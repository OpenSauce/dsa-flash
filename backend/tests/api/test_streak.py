from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.api.flashcards import router as flashcard_router
from app.api.users import User, get_password_hash
from app.api.users import router as user_router
from app.database import get_session
from app.models import Flashcard, StudySession


def _get_test_session(session):
    def get_test_session():
        with Session(session.get_bind()) as s:
            yield s

    return get_test_session


@pytest.fixture(name="app")
def app_fixture(session):
    app = FastAPI()
    app.include_router(flashcard_router)
    app.include_router(user_router)
    app.dependency_overrides[get_session] = _get_test_session(session)
    return app


@pytest.fixture(name="client")
def client_fixture(app):
    return TestClient(app)


def create_user(session, username="streakuser", password="password"):
    user = User(username=username, hashed_password=get_password_hash(password))
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def get_token(client, username, password) -> str:
    response = client.post("/token", data={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def seed_study_session(session, user_id, study_date, cards_reviewed=1):
    ss = StudySession(
        user_id=user_id,
        study_date=study_date,
        cards_reviewed=cards_reviewed,
    )
    session.add(ss)
    session.commit()
    return ss


def create_flashcard(session, **kwargs):
    kwargs.setdefault("title", kwargs.get("front") or "Untitled")
    card = Flashcard(**kwargs)
    session.add(card)
    session.commit()
    session.refresh(card)
    return card


def test_streak_unauthenticated_returns_401(client):
    r = client.get("/users/streak")
    assert r.status_code == 401


def test_streak_new_user_returns_zeros(client, session):
    create_user(session)
    token = get_token(client, "streakuser", "password")

    r = client.get("/users/streak", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert data["current_streak"] == 0
    assert data["longest_streak"] == 0
    assert data["today_reviewed"] == 0


def test_streak_after_one_review_today(client, session):
    create_user(session)
    token = get_token(client, "streakuser", "password")
    card = create_flashcard(session, front="Q", back="A")

    client.post(
        f"/flashcards/{card.id}/review",
        headers={"Authorization": f"Bearer {token}"},
        json={"quality": 3},
    )

    r = client.get("/users/streak", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert data["current_streak"] == 1
    assert data["today_reviewed"] == 1


def test_streak_consecutive_days(client, session):
    user = create_user(session)
    token = get_token(client, "streakuser", "password")
    today = datetime.now(timezone.utc).date()

    seed_study_session(session, user.id, today)
    seed_study_session(session, user.id, today - timedelta(days=1))
    seed_study_session(session, user.id, today - timedelta(days=2))

    r = client.get("/users/streak", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert data["current_streak"] == 3


def test_streak_resets_after_missed_day(client, session):
    user = create_user(session)
    token = get_token(client, "streakuser", "password")
    today = datetime.now(timezone.utc).date()

    seed_study_session(session, user.id, today)
    seed_study_session(session, user.id, today - timedelta(days=3))

    r = client.get("/users/streak", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert data["current_streak"] == 1


def test_streak_longest_preserved(client, session):
    user = create_user(session)
    token = get_token(client, "streakuser", "password")
    today = datetime.now(timezone.utc).date()

    seed_study_session(session, user.id, today)
    seed_study_session(session, user.id, today - timedelta(days=1))

    for i in range(5):
        seed_study_session(session, user.id, today - timedelta(days=10 + i))

    r = client.get("/users/streak", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert data["current_streak"] == 2
    assert data["longest_streak"] == 5


def test_review_creates_study_session(client, session):
    user = create_user(session)
    token = get_token(client, "streakuser", "password")
    card = create_flashcard(session, front="Q", back="A")

    client.post(
        f"/flashcards/{card.id}/review",
        headers={"Authorization": f"Bearer {token}"},
        json={"quality": 3},
    )

    today = datetime.now(timezone.utc).date()
    ss = session.exec(
        select(StudySession).where(
            StudySession.user_id == user.id,
            StudySession.study_date == today,
        )
    ).first()
    assert ss is not None
    assert ss.cards_reviewed == 1


def test_review_increments_study_session(client, session):
    user = create_user(session)
    token = get_token(client, "streakuser", "password")
    card1 = create_flashcard(session, front="Q1", back="A1")
    card2 = create_flashcard(session, front="Q2", back="A2")

    client.post(
        f"/flashcards/{card1.id}/review",
        headers={"Authorization": f"Bearer {token}"},
        json={"quality": 3},
    )
    client.post(
        f"/flashcards/{card2.id}/review",
        headers={"Authorization": f"Bearer {token}"},
        json={"quality": 5},
    )

    today = datetime.now(timezone.utc).date()
    ss = session.exec(
        select(StudySession).where(
            StudySession.user_id == user.id,
            StudySession.study_date == today,
        )
    ).first()
    assert ss is not None
    assert ss.cards_reviewed == 2


def test_streak_not_studied_today_but_yesterday(client, session):
    user = create_user(session)
    token = get_token(client, "streakuser", "password")
    today = datetime.now(timezone.utc).date()

    seed_study_session(session, user.id, today - timedelta(days=1))

    r = client.get("/users/streak", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert data["current_streak"] == 1
    assert data["today_reviewed"] == 0


def test_streak_not_studied_today_multi_day(client, session):
    user = create_user(session)
    token = get_token(client, "streakuser", "password")
    today = datetime.now(timezone.utc).date()

    seed_study_session(session, user.id, today - timedelta(days=1))
    seed_study_session(session, user.id, today - timedelta(days=2))
    seed_study_session(session, user.id, today - timedelta(days=3))

    r = client.get("/users/streak", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert data["current_streak"] == 3
    assert data["today_reviewed"] == 0


def test_streak_missed_yesterday_and_today(client, session):
    user = create_user(session)
    token = get_token(client, "streakuser", "password")
    today = datetime.now(timezone.utc).date()

    seed_study_session(session, user.id, today - timedelta(days=2))

    r = client.get("/users/streak", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert data["current_streak"] == 0
    assert data["longest_streak"] == 1
