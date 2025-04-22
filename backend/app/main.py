# app/api.py  (or wherever your router lives)
from fastapi import FastAPI, Query, HTTPException
from sqlmodel import Session, select
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from .database import engine
from .loader   import load_yaml_flashcards
from .models   import Flashcard

app = FastAPI()


# 👉 dump & reload YAML on every dev‑start.  drop_all() is fine for dev
@app.on_event("startup")
def init_db() -> None:
    from sqlmodel import SQLModel

    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    load_yaml_flashcards()


@app.get("/flashcards", response_model=list[Flashcard])
def list_cards(
    *,
    category: str | None = Query(None, description="e.g. 'data structures'"),
    language: str | None = Query(None, description="e.g. 'go'"),
    tag: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    stmt = select(Flashcard)

    if category:
        stmt = stmt.where(Flashcard.category == category)
    if language:
        stmt = stmt.where(Flashcard.language == language)
    if tag:
        stmt = stmt.where(Flashcard.tags.any(tag))

    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)

    with Session(engine) as s:
        cards = s.exec(stmt).all()
        if not cards and page > 1:
            raise HTTPException(status_code=404, detail="Page out of range")
        return JSONResponse(content=jsonable_encoder(cards))
