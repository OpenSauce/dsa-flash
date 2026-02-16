from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel
from sqlalchemy import JSON, Column, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlmodel import Field, SQLModel


class Flashcard(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    front: str
    back: str
    title: str
    difficulty: Optional[str] = None
    tags: List[str] = Field(
        default_factory=list, sa_column=Column(ARRAY(String), nullable=False)
    )
    category: Optional[str] = None
    language: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    hashed_password: str
    is_admin: bool = Field(default=False)


class UserCreate(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserFlashcard(SQLModel, table=True):
    """
    Link-table that stores the user's personal learning state for one card.

    Implements the SuperMemo-2 algorithm (interval, easiness, repetitions).
    The composite PK prevents duplicates.
    """

    user_id: Optional[int] = Field(foreign_key="user.id", primary_key=True)
    flashcard_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("flashcard.id", ondelete="CASCADE"),
            primary_key=True,
        )
    )

    repetitions: int = 0  # number of successful reviews so far
    interval: int = 0  # days until next review
    easiness: float = 2.5  # SM-2 easiness factor
    next_review: Optional[datetime] = None  # when it becomes "due"
    last_reviewed: Optional[datetime] = None  # most-recent review
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)


class Event(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(index=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", nullable=True)
    event_type: str = Field(index=True)
    payload: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False, server_default="{}"))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False, index=True)


class EventIn(BaseModel):
    event_type: str
    payload: dict = {}


class EventBatchIn(BaseModel):
    events: list[EventIn]
