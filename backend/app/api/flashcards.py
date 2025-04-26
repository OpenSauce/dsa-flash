from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy import func
from sqlmodel import Session, select, col
from pydantic import BaseModel
from datetime import datetime, timezone

from ..models import Flashcard, UserFlashcard, User
from .users import get_current_user
from ..spaced import sm2
from ..database import get_session

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
    random: bool = Query(False, description="Shuffle the cards"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    stmt = select(Flashcard)
    if category:
        stmt = stmt.where(Flashcard.category == category)
    if language:
        stmt = stmt.where(Flashcard.language == language)
    if random:
        stmt = stmt.order_by(func.random())

    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)

    cards = session.exec(stmt).all()

    if tag is not None:
        cards = [c for c in cards if tag in c.tags]

    if not cards and page > 1:
        raise HTTPException(404, "Page out of range")
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
        raise HTTPException(404, "Card not found")
    if user.id is None:
        raise Exception(401, "User not authenticated")
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
            UserFlashcard.next_review is not None
            and UserFlashcard.next_review <= datetime.now(timezone.utc),
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
