from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from ..database import get_session
from ..models import (
    Quiz,
    QuizAnswerResult,
    QuizDetailOut,
    QuizOut,
    QuizQuestion,
    QuizQuestionOut,
    QuizSubmitIn,
    QuizSubmitOut,
    User,
    UserQuizAttempt,
)
from .users import get_optional_user

router = APIRouter(prefix="/quizzes", tags=["quizzes"])


@router.get("", response_model=list[QuizOut])
def list_quizzes(
    category: Optional[str] = Query(None),
    session: Session = Depends(get_session),
):
    """List quizzes, optionally filtered by category. No auth required."""
    stmt = select(Quiz).order_by(Quiz.category, Quiz.title)
    if category:
        stmt = stmt.where(Quiz.category == category)
    quizzes = session.exec(stmt).all()

    result = []
    for quiz in quizzes:
        question_count = len(
            session.exec(
                select(QuizQuestion).where(QuizQuestion.quiz_id == quiz.id)
            ).all()
        )
        result.append(
            QuizOut(
                id=quiz.id,
                title=quiz.title,
                slug=quiz.slug,
                category=quiz.category,
                lesson_slug=quiz.lesson_slug,
                question_count=question_count,
                created_at=quiz.created_at,
                updated_at=quiz.updated_at,
            )
        )
    return result


@router.get("/{slug}", response_model=QuizDetailOut)
def get_quiz(
    slug: str,
    session: Session = Depends(get_session),
):
    """Get a single quiz with questions. No auth required."""
    quiz = session.exec(select(Quiz).where(Quiz.slug == slug)).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    questions = session.exec(
        select(QuizQuestion)
        .where(QuizQuestion.quiz_id == quiz.id)
        .order_by(QuizQuestion.order)
    ).all()

    return QuizDetailOut(
        id=quiz.id,
        title=quiz.title,
        slug=quiz.slug,
        category=quiz.category,
        lesson_slug=quiz.lesson_slug,
        questions=[
            QuizQuestionOut(
                id=q.id,
                order=q.order,
                question=q.question,
                options=q.options,
                correct_index=q.correct_index,
            )
            for q in questions
        ],
    )


@router.post("/{slug}/submit", response_model=QuizSubmitOut)
def submit_quiz(
    slug: str,
    body: QuizSubmitIn,
    session: Session = Depends(get_session),
    user: Optional[User] = Depends(get_optional_user),
):
    """Submit answers for a quiz. Anonymous users get results but no score persistence."""
    quiz = session.exec(select(Quiz).where(Quiz.slug == slug)).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    questions = session.exec(
        select(QuizQuestion)
        .where(QuizQuestion.quiz_id == quiz.id)
        .order_by(QuizQuestion.order)
    ).all()

    results = []
    score = 0
    total = len(questions)

    for q in questions:
        selected = body.answers.get(str(q.id))
        correct = selected == q.correct_index
        if correct:
            score += 1
        results.append(
            QuizAnswerResult(
                question_id=q.id,
                correct=correct,
                correct_index=q.correct_index,
                explanation=q.explanation,
            )
        )

    if user:
        _upsert_attempt(session, user.id, quiz.id, score, total)

    return QuizSubmitOut(score=score, total=total, results=results)


def _upsert_attempt(
    session: Session, user_id: int, quiz_id: int, score: int, total: int
) -> None:
    """Insert or update UserQuizAttempt, handling concurrent submission race."""
    existing = session.exec(
        select(UserQuizAttempt).where(
            UserQuizAttempt.user_id == user_id,
            UserQuizAttempt.quiz_id == quiz_id,
        )
    ).first()

    now = datetime.now(timezone.utc)
    if existing:
        existing.score = score
        existing.total = total
        existing.completed_at = now
        session.add(existing)
    else:
        attempt = UserQuizAttempt(
            user_id=user_id,
            quiz_id=quiz_id,
            score=score,
            total=total,
            completed_at=now,
        )
        session.add(attempt)
        try:
            session.flush()
        except IntegrityError:
            session.rollback()
            existing = session.exec(
                select(UserQuizAttempt).where(
                    UserQuizAttempt.user_id == user_id,
                    UserQuizAttempt.quiz_id == quiz_id,
                )
            ).first()
            if existing:
                existing.score = score
                existing.total = total
                existing.completed_at = now
                session.add(existing)
    session.commit()
