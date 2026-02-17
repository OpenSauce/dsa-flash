from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlmodel import Session, and_, col, or_, select

from ..database import get_session
from ..models import CategoryOut, Flashcard, StudySession, User, UserFlashcard
from ..spaced import sm2
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

    due_map: dict[str, int] = {}
    new_map: dict[str, int] = {}

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

    return [
        CategoryOut(
            slug=row.category,
            name=row.category.replace("-", " ").title(),
            total=row.total,
            due=due_map.get(row.category, 0) if user else None,
            new=new_map.get(row.category, 0) if user else None,
        )
        for row in rows
    ]


class ReviewIn(BaseModel):
    quality: int = Field(ge=0, le=5)


class StatsOut(BaseModel):
    due: int
    new: int


@router.get("", response_model=list[Flashcard])
def list_cards(
    session: Session = Depends(get_session),
    category: Optional[str] = Query(None),
    language: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    user: Optional[User] = Depends(get_optional_user),
    random: bool = Query(False, description="Shuffle the cards"),
):
    if user:
        # Authenticated: SM-2 filtered (due or new cards only)
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
                    col(UserFlashcard.next_review) <= datetime.now(timezone.utc),
                )
            )
        )
    else:
        # Anonymous: all cards, no SM-2 filtering
        stmt = select(Flashcard)

    if category:
        stmt = stmt.where(Flashcard.category == category)
    if language:
        stmt = stmt.where(Flashcard.language == language)
    if random:
        stmt = stmt.order_by(func.random())
    if tag:
        stmt = stmt.where(col(Flashcard.tags).contains([tag]))
    cards = session.exec(stmt).all()

    return JSONResponse(content=jsonable_encoder(cards))


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
