from datetime import datetime, timezone
from math import floor
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import case, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlmodel import Session, and_, col, or_, select

from ..database import get_session
from ..models import (
    MASTERY_INTERVAL_DAYS,
    CategoryOut,
    Flashcard,
    FlashcardWithIntervals,
    Lesson,
    Quiz,
    StudySession,
    User,
    UserFlashcard,
    UserLesson,
    UserQuizAttempt,
    slug_to_display_name,
)
from ..spaced import compute_projected_intervals, sm2
from .users import get_current_user, get_optional_user

router = APIRouter(prefix="/flashcards", tags=["flashcards"])
categories_router = APIRouter(prefix="/categories", tags=["categories"])


@categories_router.get("", response_model=list[CategoryOut])
def list_categories(
    session: Session = Depends(get_session),
    user: Optional[User] = Depends(get_optional_user),
):
    totals_stmt = (
        select(Flashcard.category, func.count().label("total"))
        .where(col(Flashcard.category).is_not(None))
        .group_by(Flashcard.category)
        .order_by(Flashcard.category)
    )
    rows = session.exec(totals_stmt).all()

    lang_stmt = (
        select(Flashcard.category)
        .where(
            col(Flashcard.category).is_not(None),
            col(Flashcard.language).is_not(None),
        )
        .group_by(Flashcard.category)
    )
    lang_categories = {row for row in session.exec(lang_stmt).all()}

    lesson_count_stmt = (
        select(Lesson.category, func.count().label("count"))
        .where(col(Lesson.category).is_not(None))
        .group_by(Lesson.category)
    )
    lesson_count_map = {
        row.category: row.count for row in session.exec(lesson_count_stmt).all()
    }

    first_lesson_map: dict[str, str] = {}
    for row in session.exec(
        select(Lesson.category, Lesson.slug, Lesson.order)
        .where(col(Lesson.category).is_not(None))
        .order_by(Lesson.category, Lesson.order)
    ).all():
        if row.category not in first_lesson_map:
            first_lesson_map[row.category] = row.slug

    due_map: dict[str, int] = {}
    new_map: dict[str, int] = {}
    learned_map: dict[str, int] = {}
    mastered_map: dict[str, int] = {}
    lessons_completed_map: dict[str, int] = {}

    if user:
        now = datetime.now(timezone.utc)
        due_stmt = (
            select(Flashcard.category, func.count().label("due"))
            .join(
                UserFlashcard,
                and_(
                    col(UserFlashcard.flashcard_id) == col(Flashcard.id),
                    col(UserFlashcard.user_id) == user.id,
                ),
            )
            .where(
                col(Flashcard.category).is_not(None),
                col(UserFlashcard.next_review) <= now,
            )
            .group_by(Flashcard.category)
        )
        due_map = {row.category: row.due for row in session.exec(due_stmt).all()}

        exists_q = select(1).where(
            UserFlashcard.user_id == user.id,
            UserFlashcard.flashcard_id == Flashcard.id,
        )
        new_stmt = (
            select(Flashcard.category, func.count().label("new_count"))
            .select_from(Flashcard)
            .where(
                col(Flashcard.category).is_not(None),
                ~exists_q.exists(),
            )
            .group_by(Flashcard.category)
        )
        new_map = {row.category: row.new_count for row in session.exec(new_stmt).all()}

        progress_stmt = (
            select(
                Flashcard.category,
                func.count(UserFlashcard.flashcard_id).label("learned"),
                func.sum(
                    case((UserFlashcard.interval > MASTERY_INTERVAL_DAYS, 1), else_=0)
                ).label("mastered"),
            )
            .select_from(UserFlashcard)
            .join(Flashcard, Flashcard.id == UserFlashcard.flashcard_id)
            .where(
                UserFlashcard.user_id == user.id,
                col(Flashcard.category).is_not(None),
            )
            .group_by(Flashcard.category)
        )
        for row in session.exec(progress_stmt).all():
            learned_map[row.category] = row.learned
            mastered_map[row.category] = int(row.mastered or 0)

        # For categories with lessons: count completed lessons (quiz-based)
        # A lesson is "completed" if its quiz has been submitted (UserQuizAttempt),
        # or if no quiz exists and UserLesson exists.
        if lesson_count_map:
            # Get all lessons in categories that have lessons
            all_lessons = session.exec(
                select(Lesson).where(
                    col(Lesson.category).in_(list(lesson_count_map.keys()))
                )
            ).all()

            # Map lesson_slug -> quiz_id
            lesson_slugs = [les.slug for les in all_lessons]
            quiz_map: dict[str, int] = {}
            if lesson_slugs:
                for q in session.exec(
                    select(Quiz).where(col(Quiz.lesson_slug).in_(lesson_slugs))
                ).all():
                    if q.lesson_slug:
                        quiz_map[q.lesson_slug] = q.id

            # User's completed quiz IDs
            completed_quiz_ids: set[int] = set()
            if quiz_map:
                completed_quiz_ids = set(
                    session.exec(
                        select(UserQuizAttempt.quiz_id).where(
                            UserQuizAttempt.user_id == user.id,
                            col(UserQuizAttempt.quiz_id).in_(
                                list(quiz_map.values())
                            ),
                        )
                    ).all()
                )

            # User's completed lesson IDs (fallback for lessons without quizzes)
            completed_lesson_ids = {
                ul.lesson_id
                for ul in session.exec(
                    select(UserLesson).where(UserLesson.user_id == user.id)
                ).all()
            }

            for les in all_lessons:
                has_quiz = les.slug in quiz_map
                if has_quiz:
                    done = quiz_map[les.slug] in completed_quiz_ids
                else:
                    done = les.id in completed_lesson_ids
                if done and les.category:
                    lessons_completed_map[les.category] = (
                        lessons_completed_map.get(les.category, 0) + 1
                    )

    def _learned(cat_slug: str, total: int) -> int:
        """For categories with lessons, learned = lessons completed.
        For categories without, learned = flashcards seen (UserFlashcard count).
        """
        if cat_slug in lesson_count_map:
            return lessons_completed_map.get(cat_slug, 0)
        return learned_map.get(cat_slug, 0)

    def _learned_pct(cat_slug: str, total: int) -> int:
        """Percentage based on lesson or flashcard progress."""
        if cat_slug in lesson_count_map:
            lesson_total = lesson_count_map[cat_slug]
            if lesson_total > 0:
                return floor(
                    lessons_completed_map.get(cat_slug, 0) / lesson_total * 100
                )
            return 0
        if total > 0:
            return floor(learned_map.get(cat_slug, 0) / total * 100)
        return 0

    return [
        CategoryOut(
            slug=row.category,
            name=slug_to_display_name(row.category),
            total=row.total,
            has_language=row.category in lang_categories,
            due=due_map.get(row.category, 0) if user else None,
            new=new_map.get(row.category, 0) if user else None,
            learned=_learned(row.category, row.total) if user else None,
            mastered=mastered_map.get(row.category, 0) if user else None,
            mastery_pct=(
                floor(mastered_map.get(row.category, 0) / row.total * 100)
                if user and row.total > 0
                else None
            ),
            learned_pct=(
                _learned_pct(row.category, row.total) if user else None
            ),
            lessons_available=lesson_count_map.get(row.category, 0),
            lessons_completed=(
                lessons_completed_map.get(row.category, 0) if user else None
            ),
            first_lesson_slug=first_lesson_map.get(row.category),
        )
        for row in rows
    ]


class ReviewIn(BaseModel):
    quality: int = Field(ge=0, le=5)


class StatsOut(BaseModel):
    due: int
    new: int


@router.get("", response_model=list[FlashcardWithIntervals])
def list_cards(
    session: Session = Depends(get_session),
    category: Optional[str] = Query(None),
    language: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    user: Optional[User] = Depends(get_optional_user),
    random: bool = Query(False, description="Shuffle the cards"),
    mode: Optional[str] = Query(None),
    limit: Optional[int] = Query(None, ge=1, le=100),
):
    now = datetime.now(timezone.utc)
    if user:
        if mode not in (None, "due", "new", "all"):
            raise HTTPException(status_code=422, detail="Invalid mode parameter")
        if mode == "due":
            stmt = (
                select(Flashcard)
                .join(
                    UserFlashcard,
                    and_(
                        col(UserFlashcard.flashcard_id) == col(Flashcard.id),
                        col(UserFlashcard.user_id) == user.id,
                    ),
                )
                .where(
                    col(UserFlashcard.next_review).is_not(None),
                    col(UserFlashcard.next_review) <= now,
                )
            )
        elif mode == "new":
            exists_q = select(1).where(
                UserFlashcard.user_id == user.id,
                UserFlashcard.flashcard_id == Flashcard.id,
            )
            stmt = select(Flashcard).where(~exists_q.exists())
        else:
            # mode=all or mode=None: default SM-2 behavior (due + new)
            stmt = (
                select(Flashcard)
                .join(
                    UserFlashcard,
                    and_(
                        col(UserFlashcard.flashcard_id) == col(Flashcard.id),
                        col(UserFlashcard.user_id) == user.id,
                    ),
                    isouter=True,
                )
                .where(
                    or_(
                        col(UserFlashcard.user_id).is_(None),
                        col(UserFlashcard.next_review) <= now,
                    )
                )
            )
    else:
        # Anonymous: all cards, no SM-2 filtering, mode ignored
        stmt = select(Flashcard)

    if category:
        stmt = stmt.where(Flashcard.category == category)
    if language:
        stmt = stmt.where(Flashcard.language == language)
    if random:
        stmt = stmt.order_by(func.random())
    if tag:
        stmt = stmt.where(col(Flashcard.tags).contains([tag]))

    # Apply limit: explicit limit takes priority; mode=new defaults to 10
    effective_limit = limit
    if effective_limit is None and mode == "new" and user:
        effective_limit = 10
    if effective_limit is not None:
        stmt = stmt.limit(effective_limit)

    cards = session.exec(stmt).all()

    if user:
        card_ids = [c.id for c in cards]
        if card_ids:
            uf_stmt = select(UserFlashcard).where(
                UserFlashcard.user_id == user.id,
                col(UserFlashcard.flashcard_id).in_(card_ids),
            )
            uf_rows = session.exec(uf_stmt).all()
            uf_map = {uf.flashcard_id: uf for uf in uf_rows}
        else:
            uf_map = {}

        result = []
        for card in cards:
            uf = uf_map.get(card.id)
            if uf:
                intervals = compute_projected_intervals(uf.repetitions, uf.interval, uf.easiness)
            else:
                intervals = compute_projected_intervals()
            result.append(FlashcardWithIntervals(
                id=card.id,
                front=card.front,
                back=card.back,
                title=card.title,
                difficulty=card.difficulty,
                tags=card.tags,
                category=card.category,
                language=card.language,
                created_at=card.created_at,
                projected_intervals=intervals,
            ))
        return result

    return [
        FlashcardWithIntervals(
            id=card.id,
            front=card.front,
            back=card.back,
            title=card.title,
            difficulty=card.difficulty,
            tags=card.tags,
            category=card.category,
            language=card.language,
            created_at=card.created_at,
            projected_intervals=None,
        )
        for card in cards
    ]


@router.post("/{card_id}/review", status_code=204)
def review_card(
    card_id: int,
    body: ReviewIn,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    card = session.get(Flashcard, card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    uf = session.get(UserFlashcard, (user.id, card_id))
    if uf is None:
        uf = UserFlashcard(user_id=user.id, flashcard_id=card_id)
        session.add(uf)
    sm2(uf, body.quality)

    today = datetime.now(timezone.utc).date()
    stmt = pg_insert(StudySession).values(
        user_id=user.id,
        study_date=today,
        cards_reviewed=1,
    ).on_conflict_do_update(
        constraint="uq_studysession_user_date",
        set_={"cards_reviewed": StudySession.__table__.c.cards_reviewed + 1},
    )
    session.execute(stmt)

    session.commit()


@router.get("/due", response_model=list[Flashcard])
def due_cards(
    limit: int = Query(20, ge=1, le=100),
    user=Depends(get_current_user),
    session: Session = Depends(get_session),
):
    stmt = (
        select(Flashcard)
        .join(
            UserFlashcard,
            (UserFlashcard.user_id == user.id)
            & (UserFlashcard.flashcard_id == Flashcard.id),
        )
        .where(
            col(UserFlashcard.next_review).is_not(None),
            col(UserFlashcard.next_review) <= datetime.now(timezone.utc),
        )
        .limit(limit)
    )
    return session.exec(stmt).all()


@router.get("/stats", response_model=StatsOut)
def card_stats(
    category: Optional[str] = Query(None),
    language: Optional[str] = Query(None),
    user=Depends(get_current_user),
    session: Session = Depends(get_session),
):
    now = datetime.now(timezone.utc)

    fc_filters = []
    if category:
        fc_filters.append(Flashcard.category == category)
    if language:
        fc_filters.append(Flashcard.language == language)

    due_q = (
        select(func.count())
        .select_from(UserFlashcard, Flashcard)
        .where(
            Flashcard.id == UserFlashcard.flashcard_id,
            UserFlashcard.user_id == user.id,
            col(UserFlashcard.next_review) <= now,
            *fc_filters,
        )
    )
    due = session.exec(due_q).one()

    exists_q = (
        select(1)
        .select_from(UserFlashcard)
        .where(
            UserFlashcard.user_id == user.id, UserFlashcard.flashcard_id == Flashcard.id
        )
    )
    new_q = (
        select(func.count())
        .select_from(Flashcard)
        .where(~exists_q.exists(), *fc_filters)
    )
    new = session.exec(new_q).one()

    return {"due": due, "new": new}
