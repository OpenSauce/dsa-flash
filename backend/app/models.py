from datetime import date, datetime, timezone
from typing import List, Optional

from pydantic import BaseModel
from pydantic import Field as PydanticField
from sqlalchemy import JSON, Column, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY
from sqlmodel import Field, SQLModel

MASTERY_INTERVAL_DAYS = 21

DISPLAY_NAMES: dict[str, str] = {
    "aws": "AWS",
    "data-structures": "Data Structures",
    "algorithms": "Algorithms",
    "advanced-data-structures": "Advanced Data Structures",
    "big-o-notation": "Big O Notation",
    "system-design": "System Design",
    "kubernetes": "Kubernetes",
    "docker": "Docker",
    "linux": "Linux",
    "networking": "Networking",
}


def slug_to_display_name(slug: str) -> str:
    if slug in DISPLAY_NAMES:
        return DISPLAY_NAMES[slug]
    return slug.replace("-", " ").title()


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
    username: str = PydanticField(min_length=3, pattern=r'^[a-zA-Z0-9_]+$')
    password: str = PydanticField(min_length=8)


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


class StudySession(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint("user_id", "study_date", name="uq_studysession_user_date"),
    )
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    study_date: date
    cards_reviewed: int = Field(default=0)


class StreakOut(BaseModel):
    current_streak: int
    longest_streak: int
    today_reviewed: int


class FlashcardWithIntervals(BaseModel):
    id: Optional[int]
    front: str
    back: str
    title: str
    difficulty: Optional[str] = None
    tags: List[str] = []
    category: Optional[str] = None
    language: Optional[str] = None
    created_at: datetime
    projected_intervals: Optional[dict[str, str]] = None


class EventIn(BaseModel):
    event_type: str
    payload: dict = {}


class EventBatchIn(BaseModel):
    events: list[EventIn]


class CategoryOut(BaseModel):
    slug: str
    name: str
    total: int
    has_language: bool
    due: Optional[int] = None
    new: Optional[int] = None
    learned: Optional[int] = None
    mastered: Optional[int] = None
    mastery_pct: Optional[int] = None
    learned_pct: Optional[int] = None


class DashboardKnowledgeSummary(BaseModel):
    total_concepts_learned: int
    concepts_mastered: int
    domains_explored: int


class DashboardDomain(BaseModel):
    name: str
    slug: str
    total: int
    learned: int
    mastered: int
    mastery_pct: int
    learned_pct: int


class DashboardStreak(BaseModel):
    current: int
    longest: int
    today_reviewed: int


class DashboardWeek(BaseModel):
    concepts_learned: int
    domains_studied: list[str]
    study_days: int


class DashboardWeakCard(BaseModel):
    id: int
    title: str
    category: str
    easiness: float


class DashboardOut(BaseModel):
    knowledge_summary: DashboardKnowledgeSummary
    domains: list[DashboardDomain]
    streak: DashboardStreak
    this_week: DashboardWeek
    weakest_cards: list[DashboardWeakCard]
    study_calendar: list[str]
