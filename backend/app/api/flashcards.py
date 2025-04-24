from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy import func
from sqlmodel import Session, select

from ..database import get_session
from ..models import Flashcard

router = APIRouter(prefix="/flashcards", tags=["flashcards"])


@router.get("", response_model=list[Flashcard])  # GET /flashcards
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
    if tag:
        stmt = stmt.where(Flashcard.tags.__contains__([tag]))
    if random:
        stmt = stmt.order_by(func.random())

    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)

    cards = session.exec(stmt).all()
    if not cards and page > 1:
        raise HTTPException(404, "Page out of range")
    return JSONResponse(content=jsonable_encoder(cards))
