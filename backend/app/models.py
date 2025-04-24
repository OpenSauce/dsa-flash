from datetime import datetime
from typing import List, Optional
from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlmodel import SQLModel, Field
from pydantic import BaseModel


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
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    hashed_password: str


class UserCreate(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
