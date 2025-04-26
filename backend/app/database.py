import os
from sqlmodel import SQLModel, create_engine, Session
from typing import Generator

DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://user:password@db:5432/flashcards",
)

engine = create_engine(DB_URL, echo=True)


def init_db() -> None:
    """Drop & recreate tables — quick‑and‑dirty for dev; swap to migrations in prod."""
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:  # FastAPI dependency helper
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()
