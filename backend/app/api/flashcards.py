from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import func
from sqlmodel import Session, and_, col, or_, select

from ..database import get_session
from ..models import Flashcard, User, UserFlashcard
from ..spaced import sm2
from .users import get_current_user, get_optional_user

router = APIRouter(prefix="/flashcards", tags=["flashcards"])


class ReviewIn(BaseModel):
    quality: int


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
