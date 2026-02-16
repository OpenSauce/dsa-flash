import os
from typing import Generator

from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine

DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://user:password@db:5432/flashcards",
)

engine = create_engine(DB_URL, echo=os.getenv("DEV_MODE", "").lower() in ("1", "true"))


def init_db() -> None:
    """Create tables if they don't exist, then ensure FK cascades."""
    SQLModel.metadata.create_all(engine)

    with engine.begin() as conn:
        conn.execute(
            text(
                "ALTER TABLE userflashcard "
                "DROP CONSTRAINT IF EXISTS userflashcard_flashcard_id_fkey, "
                "ADD CONSTRAINT userflashcard_flashcard_id_fkey "
                "FOREIGN KEY (flashcard_id) REFERENCES flashcard(id) ON DELETE CASCADE;"
            )
        )


def get_session() -> Generator[Session, None, None]:
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()
