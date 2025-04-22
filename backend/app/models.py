from datetime import datetime
from typing import List, Optional
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy import Column
from sqlmodel import SQLModel, Field, String


class Flashcard(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    front: str
    back: str
    title: str
    difficulty: Optional[str] = None

    tags: Optional[List[str]] = Field(
        default=None, sa_column=Column(ARRAY(String))
    )

    category: Optional[str] = None
    language: Optional[str] = None

    created_at: datetime = Field(
        default_factory=datetime.utcnow, nullable=False
    )
