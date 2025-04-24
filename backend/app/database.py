import os
from sqlmodel import SQLModel, create_engine, Session

DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://user:password@db:5432/flashcards",
)

engine = create_engine(DB_URL, echo=False)


def init_db() -> None:
    """Drop & recreate tables — quick‑and‑dirty for dev; swap to migrations in prod."""
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)


def get_session() -> Session:  # FastAPI dependency helper
    return Session(engine)
