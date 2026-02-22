from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, col, select

from ..database import get_session
from ..models import (
    CategoryLessonInfo,
    Flashcard,
    Lesson,
    LessonDetailOut,
    LessonOut,
    Quiz,
    User,
    UserFlashcard,
    UserLesson,
    UserQuizAttempt,
)
from .users import get_current_user, get_optional_user

router = APIRouter(prefix="/lessons", tags=["lessons"])


@router.get("", response_model=list[LessonOut])
def list_lessons(
    category: Optional[str] = Query(None),
    session: Session = Depends(get_session),
):
    """List lessons, optionally filtered by category. No auth required."""
    stmt = select(Lesson).order_by(Lesson.category, Lesson.order)
    if category:
        stmt = stmt.where(Lesson.category == category)
    return session.exec(stmt).all()


@router.get("/by-category/{category}", response_model=list[CategoryLessonInfo])
def lessons_for_category(
    category: str,
    session: Session = Depends(get_session),
    user: Optional[User] = Depends(get_optional_user),
):
    """Get lesson list for a category with completion status.

    Completion is quiz-based: if a lesson has a quiz, completed = quiz submitted.
    If no quiz exists, completed = lesson marked complete (UserLesson).
    """
    lessons = session.exec(
        select(Lesson).where(Lesson.category == category).order_by(Lesson.order)
    ).all()

    lesson_slugs = [l.slug for l in lessons]

    # Map lesson_slug -> quiz_id for lessons that have quizzes
    quiz_map: dict[str, int] = {}
    if lesson_slugs:
        for q in session.exec(
            select(Quiz).where(col(Quiz.lesson_slug).in_(lesson_slugs))
        ).all():
            if q.lesson_slug:
                quiz_map[q.lesson_slug] = q.id

    if not user:
        return [
            CategoryLessonInfo(
                slug=lesson.slug, title=lesson.title, completed=False,
                has_quiz=lesson.slug in quiz_map,
            )
            for lesson in lessons
        ]

    # Lessons marked complete (fallback for lessons without quizzes)
    completed_ids = {
        ul.lesson_id
        for ul in session.exec(
            select(UserLesson).where(UserLesson.user_id == user.id)
        ).all()
    }

    # Quiz attempts for this user
    completed_quiz_ids: set[int] = set()
    if quiz_map:
        completed_quiz_ids = set(
            session.exec(
                select(UserQuizAttempt.quiz_id).where(
                    UserQuizAttempt.user_id == user.id,
                    col(UserQuizAttempt.quiz_id).in_(list(quiz_map.values())),
                )
            ).all()
        )

    result = []
    for lesson in lessons:
        has_quiz = lesson.slug in quiz_map
        if has_quiz:
            completed = quiz_map[lesson.slug] in completed_quiz_ids
        else:
            completed = lesson.id in completed_ids
        result.append(
            CategoryLessonInfo(
                slug=lesson.slug, title=lesson.title,
                completed=completed, has_quiz=has_quiz,
            )
        )
    return result


@router.get("/{slug}", response_model=LessonDetailOut)
def get_lesson(
    slug: str,
    session: Session = Depends(get_session),
):
    """Get a single lesson with full markdown content. No auth required."""
    lesson = session.exec(
        select(Lesson).where(Lesson.slug == slug)
    ).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return lesson


@router.post("/{slug}/complete", status_code=204)
def complete_lesson(
    slug: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Mark a lesson as read. Auth required. Idempotent.

    If the lesson has a quiz, flashcards are NOT seeded here — the quiz
    submission handles that. If no quiz exists, flashcards are seeded
    immediately.
    """
    lesson = session.exec(
        select(Lesson).where(Lesson.slug == slug)
    ).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    existing = session.exec(
        select(UserLesson).where(
            UserLesson.user_id == user.id,
            UserLesson.lesson_id == lesson.id,
        )
    ).first()
    if existing:
        return  # already completed, idempotent

    user_lesson = UserLesson(user_id=user.id, lesson_id=lesson.id)
    session.add(user_lesson)

    # If a quiz exists for this lesson, let quiz submission seed flashcards
    has_quiz = session.exec(
        select(Quiz).where(Quiz.lesson_slug == slug)
    ).first()
    if has_quiz:
        session.commit()
        return

    linked_cards = session.exec(
        select(Flashcard).where(Flashcard.lesson_slug == slug)
    ).all()

    card_ids = [card.id for card in linked_cards]
    existing_ids: set[int] = set()
    if card_ids:
        existing_ids = set(
            session.exec(
                select(UserFlashcard.flashcard_id).where(
                    UserFlashcard.user_id == user.id,
                    UserFlashcard.flashcard_id.in_(card_ids),
                )
            ).all()
        )

    now = datetime.now(timezone.utc)
    for card in linked_cards:
        if card.id in existing_ids:
            continue
        uf = UserFlashcard(
            user_id=user.id,
            flashcard_id=card.id,
            repetitions=0,
            interval=1,
            easiness=2.5,
            next_review=now + timedelta(days=1),
            last_reviewed=None,
            created_at=now,
        )
        session.add(uf)

    session.commit()
