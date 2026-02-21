from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from ..database import get_session
from ..models import (
    CategoryLessonInfo,
    Lesson,
    LessonDetailOut,
    LessonOut,
    User,
    UserLesson,
)
from .users import get_current_user, get_optional_user

router = APIRouter(prefix="/lessons", tags=["lessons"])


@router.get("", response_model=list[LessonOut])
def list_lessons(
    category: Optional[str] = Query(None),
    session: Session = Depends(get_session),
):
    """List lessons, optionally filtered by category. No auth required."""
    stmt = select(Lesson).order_by(Lesson.category, Lesson.order)
    if category:
        stmt = stmt.where(Lesson.category == category)
    return session.exec(stmt).all()


@router.get("/by-category/{category}", response_model=list[CategoryLessonInfo])
def lessons_for_category(
    category: str,
    session: Session = Depends(get_session),
    user: Optional[User] = Depends(get_optional_user),
):
    """Get lesson list for a category with completion status."""
    lessons = session.exec(
        select(Lesson).where(Lesson.category == category).order_by(Lesson.order)
    ).all()

    if not user:
        return [
            CategoryLessonInfo(slug=lesson.slug, title=lesson.title, completed=False)
            for lesson in lessons
        ]

    completed_ids = {
        ul.lesson_id
        for ul in session.exec(
            select(UserLesson).where(UserLesson.user_id == user.id)
        ).all()
    }
    return [
        CategoryLessonInfo(
            slug=lesson.slug, title=lesson.title, completed=lesson.id in completed_ids
        )
        for lesson in lessons
    ]


@router.get("/{slug}", response_model=LessonDetailOut)
def get_lesson(
    slug: str,
    session: Session = Depends(get_session),
):
    """Get a single lesson with full markdown content. No auth required."""
    lesson = session.exec(
        select(Lesson).where(Lesson.slug == slug)
    ).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return lesson


@router.post("/{slug}/complete", status_code=204)
def complete_lesson(
    slug: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Mark a lesson as completed. Auth required. Idempotent."""
    lesson = session.exec(
        select(Lesson).where(Lesson.slug == slug)
    ).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    existing = session.exec(
        select(UserLesson).where(
            UserLesson.user_id == user.id,
            UserLesson.lesson_id == lesson.id,
        )
    ).first()
    if existing:
        return  # already completed, idempotent

    user_lesson = UserLesson(user_id=user.id, lesson_id=lesson.id)
    session.add(user_lesson)
    session.commit()
