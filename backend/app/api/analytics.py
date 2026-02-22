import os
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy import text
from sqlmodel import Session

from ..database import get_session
from ..models import Event, EventBatchIn, EventIn, User
from .users import get_current_admin, get_optional_user

router = APIRouter(prefix="/events", tags=["events"])
summary_router = APIRouter(prefix="/analytics", tags=["analytics"])

_IS_PRODUCTION = os.getenv("DEV_MODE", "").lower() not in ("1", "true")


def _session_id_from_request(request: Request, response: Response) -> str:
    sid = request.cookies.get("session_id")
    if not sid:
        sid = str(uuid.uuid4())
        response.set_cookie(
            key="session_id",
            value=sid,
            httponly=True,
            samesite="lax",
            max_age=60 * 60 * 24 * 365,
            secure=_IS_PRODUCTION,
        )
    return sid


@router.post("", status_code=status.HTTP_201_CREATED)
def create_event(
    body: EventIn,
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
    user: Optional[User] = Depends(get_optional_user),
):
    sid = _session_id_from_request(request, response)
    event = Event(
        session_id=sid,
        user_id=user.id if user else None,
        event_type=body.event_type,
        payload=body.payload,
    )
    session.add(event)
    session.commit()
    session.refresh(event)
    return {"id": event.id}


@router.post("/batch", status_code=status.HTTP_201_CREATED)
def create_events_batch(
    body: EventBatchIn,
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
    user: Optional[User] = Depends(get_optional_user),
):
    sid = _session_id_from_request(request, response)
    user_id = user.id if user else None
    for ev in body.events:
        event = Event(
            session_id=sid,
            user_id=user_id,
            event_type=ev.event_type,
            payload=ev.payload,
        )
        session.add(event)
    session.commit()
    return {"count": len(body.events)}


@summary_router.get("/summary")
def analytics_summary(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_admin),
):
    row = session.exec(
        text("""
            SELECT
                COUNT(DISTINCT session_id)                       AS total_sessions,
                COUNT(DISTINCT session_id)
                    FILTER (WHERE has_authed_event = FALSE)      AS anonymous_sessions,
                COALESCE(
                    AVG(cards) FILTER (WHERE cards > 0), 0
                )                                                AS avg_cards_per_session,
                COALESCE(
                    (SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (
                        ORDER BY (payload->>'duration_ms')::bigint
                    )
                    FROM event
                    WHERE event_type = 'session_end'
                      AND payload->>'duration_ms' IS NOT NULL), 0
                )                                                AS median_session_duration_ms
            FROM (
                SELECT
                    session_id,
                    BOOL_OR(user_id IS NOT NULL)                 AS has_authed_event,
                    COUNT(*) FILTER (WHERE event_type = 'card_review') AS cards
                FROM event
                GROUP BY session_id
            ) sub
        """)
    ).one()

    total_sessions = row[0] or 0
    anonymous_sessions = row[1] or 0

    # Drop-off distribution: how many sessions reviewed 0, 1-3, 4-9, 10+ cards
    drop_off_rows = session.exec(
        text("""
            SELECT bucket, COUNT(*) AS cnt
            FROM (
                SELECT
                    session_id,
                    CASE
                        WHEN COUNT(*) FILTER (WHERE event_type = 'card_review') = 0 THEN '0'
                        WHEN COUNT(*) FILTER (WHERE event_type = 'card_review') BETWEEN 1 AND 3 THEN '1-3'
                        WHEN COUNT(*) FILTER (WHERE event_type = 'card_review') BETWEEN 4 AND 9 THEN '4-9'
                        ELSE '10+'
                    END AS bucket
                FROM event
                GROUP BY session_id
            ) sub
            GROUP BY bucket
        """)
    ).all()
    drop_off = {r[0]: r[1] for r in drop_off_rows}

    # Conversion rate: sessions with at least one authenticated event / total sessions
    conversion_rate = 0.0
    if total_sessions > 0:
        authed = total_sessions - anonymous_sessions
        conversion_rate = round(authed / total_sessions, 4)

    # Lesson & quiz metrics
    learning_row = session.exec(
        text("""
            SELECT
                (SELECT COUNT(*) FROM userlesson)       AS lessons_completed,
                (SELECT COUNT(DISTINCT user_id) FROM userlesson) AS users_with_lessons,
                (SELECT COUNT(*) FROM userquizattempt)   AS quizzes_taken,
                (SELECT COUNT(DISTINCT user_id) FROM userquizattempt) AS users_with_quizzes,
                COALESCE(
                    (SELECT ROUND(AVG(score::numeric / NULLIF(total, 0) * 100), 1)
                     FROM userquizattempt), 0
                )                                        AS avg_quiz_score_pct
        """)
    ).one()

    # Funnel: users who completed a lesson -> took a quiz -> reviewed a flashcard
    funnel_row = session.exec(
        text("""
            SELECT
                (SELECT COUNT(DISTINCT user_id) FROM userlesson)     AS lesson_users,
                (SELECT COUNT(DISTINCT user_id) FROM userquizattempt) AS quiz_users,
                (SELECT COUNT(DISTINCT user_id) FROM userflashcard)  AS review_users
        """)
    ).one()

    # Per-category lesson completions
    category_lessons = session.exec(
        text("""
            SELECT l.category, COUNT(*) AS completions
            FROM userlesson ul
            JOIN lesson l ON l.id = ul.lesson_id
            GROUP BY l.category
            ORDER BY completions DESC
        """)
    ).all()

    return {
        "total_sessions": total_sessions,
        "anonymous_sessions": anonymous_sessions,
        "avg_cards_per_session": round(float(row[2]), 2),
        "median_session_duration_ms": float(row[3]),
        "drop_off_distribution": drop_off,
        "conversion_rate": conversion_rate,
        "lessons_completed": learning_row[0] or 0,
        "users_with_lessons": learning_row[1] or 0,
        "quizzes_taken": learning_row[2] or 0,
        "users_with_quizzes": learning_row[3] or 0,
        "avg_quiz_score_pct": float(learning_row[4] or 0),
        "funnel": {
            "lesson_users": funnel_row[0] or 0,
            "quiz_users": funnel_row[1] or 0,
            "review_users": funnel_row[2] or 0,
        },
        "category_lesson_completions": {r[0]: r[1] for r in category_lessons},
    }
