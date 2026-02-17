import os
from pathlib import Path
from typing import Generator

from alembic.config import Config
from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine

from alembic import command

DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://user:password@db:5432/flashcards",
)

_dev_mode = os.getenv("DEV_MODE", "").lower() in ("1", "true")
engine = create_engine(DB_URL, echo=_dev_mode)

_BASE_DIR = Path(__file__).resolve().parent.parent
_ALEMBIC_INI = str(_BASE_DIR / "alembic.ini")


def run_migrations() -> None:
    """Run Alembic migrations to bring DB schema to head."""
    alembic_cfg = Config(_ALEMBIC_INI)

    if _dev_mode and os.getenv("RESET_DB", "").lower() == "true":
        SQLModel.metadata.drop_all(engine)
        with engine.begin() as conn:
            conn.execute(text("DROP TABLE IF EXISTS alembic_version"))

    command.upgrade(alembic_cfg, "head")


def get_session() -> Generator[Session, None, None]:
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()
