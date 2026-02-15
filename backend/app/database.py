import os
from sqlmodel import SQLModel, create_engine, Session
from typing import Generator

DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://user:password@db:5432/flashcards",
)

engine = create_engine(DB_URL, echo=True)


def init_db() -> None:
    """Create tables if they don't exist. In dev mode, drop everything first."""
    if os.getenv("DEV_MODE", "").lower() in ("1", "true"):
        SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()
