import os
from typing import Generator

from alembic.config import Config
from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine

from alembic import command

DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://user:password@db:5432/flashcards",
)

engine = create_engine(DB_URL, echo=os.getenv("DEV_MODE", "").lower() in ("1", "true"))


def run_migrations() -> None:
    """Run Alembic migrations to bring DB schema to head."""
    alembic_cfg = Config("alembic.ini")

    if os.getenv("RESET_DB", "").lower() == "true":
        SQLModel.metadata.drop_all(engine)
        with engine.connect() as conn:
            conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
            conn.commit()

    command.upgrade(alembic_cfg, "head")


def get_session() -> Generator[Session, None, None]:
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()
