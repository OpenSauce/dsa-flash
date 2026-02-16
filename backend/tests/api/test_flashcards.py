from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.api.flashcards import err_no_cards_found
from app.api.flashcards import router as flashcard_router
from app.api.users import User, get_current_user, get_password_hash
from app.api.users import router as user_router
from app.database import get_session
from app.models import Flashcard, UserFlashcard


def _get_test_session(session):
    def get_test_session():
        with Session(session.get_bind()) as s:
            yield s

    return get_test_session


@pytest.fixture(name="app")
def app_fixture(session):
    class FakeUser:
        id = 1

    app = FastAPI()
    app.include_router(flashcard_router)
    app.include_router(user_router)
    app.dependency_overrides[get_session] = _get_test_session(session)
    app.dependency_overrides[get_current_user] = lambda: FakeUser()
    return app


@pytest.fixture(name="client")
def client_fixture(app):
    return TestClient(app)


@pytest.fixture(name="anon_app")
def anon_app_fixture(session):
    """App without get_current_user override — uses real auth."""
    app = FastAPI()
    app.include_router(flashcard_router)
    app.include_router(user_router)
    app.dependency_overrides[get_session] = _get_test_session(session)
    return app


@pytest.fixture(name="anon_client")
def anon_client_fixture(anon_app):
    return TestClient(anon_app)


# Helpers
def create_flashcard(session, **kwargs):
    kwargs.setdefault("title", kwargs.get("front") or "Untitled")
    card = Flashcard(**kwargs)
    session.add(card)
    session.commit()
    session.refresh(card)
    return card


def create_user(session, username: str, password: str):
    user = User(username=username, hashed_password=get_password_hash(password))
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def get_token(client, username, password) -> str:
    response = client.post("/token", data={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


# Tests
def test_list_cards_empty(client):
    response = client.get("/flashcards")
    assert response.status_code == 404
    assert response.json()["detail"] == err_no_cards_found


def test_list_cards_filters_and_pagination(client, session):
    _ = create_user(session, "user", "password")
    token = get_token(client, "user", "password")

    for i in range(5):
        create_flashcard(
            session,
            front=f"Q{i}",
            back=f"A{i}",
            category="cat1",
            language="lang1",
            tags=["t1"],
        )
    for i in range(3):
        create_flashcard(
            session,
            front=f"Qx{i}",
            back=f"Ax{i}",
            category="cat2",
            language="lang2",
            tags=["t2"],
        )

    r = client.get(
        "/flashcards?category=cat1", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200
    assert len(r.json()) == 5

    r = client.get(
        "/flashcards?language=lang2", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200
    assert len(r.json()) == 3

    # Filter by tag
    r = client.get("/flashcards?tag=t1", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert len(r.json()) == 5


def test_review_card_creates_new_userflashcard(client, session):
    user = create_user(session, "user", "password")
    card = create_flashcard(session, front="Q", back="A")

    token = get_token(client, "user", "password")

    review_resp = client.post(
        f"/flashcards/{card.id}/review",
        headers={"Authorization": f"Bearer {token}"},
        json={"quality": 3},
    )
    assert review_resp.status_code == 204

    uf = session.exec(
        select(UserFlashcard).where(
            UserFlashcard.user_id == user.id, UserFlashcard.flashcard_id == card.id
        )
    ).one()
    assert uf.repetitions == 1


def test_review_card_not_found(client):
    response = client.post("/flashcards/999/review", json={"quality": 2})
    assert response.status_code == 404


def test_due_cards(client, session):
    user = create_user(session, "user", "password")
    token = get_token(client, "user", "password")

    create_user(session, "user2", "password")
    get_token(client, "user2", "password")
    _ = create_flashcard(session, id=999, front="Past", back="A1")
    _ = create_flashcard(session, front="Future", back="A2")
    now = datetime.now(timezone.utc)
    uf1 = UserFlashcard(
        user_id=1, flashcard_id=999, next_review=now - timedelta(days=1)
    )
    uf2 = UserFlashcard(user_id=1, flashcard_id=1, next_review=now + timedelta(days=1))
    session.add_all([uf1, uf2])
    session.commit()

    r = client.get("/flashcards/due", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["front"] == "Past"

    session.delete(user)


def test_due_cards_excludes_null_next_review(client, session):
    user = create_user(session, "user", "password")
    token = get_token(client, "user", "password")

    card_due = create_flashcard(session, front="Due", back="A1")
    card_null = create_flashcard(session, front="NullReview", back="A2")

    now = datetime.now(timezone.utc)
    uf_due = UserFlashcard(
        user_id=user.id, flashcard_id=card_due.id, next_review=now - timedelta(days=1)
    )
    uf_null = UserFlashcard(
        user_id=user.id, flashcard_id=card_null.id, next_review=None
    )
    session.add_all([uf_due, uf_null])
    session.commit()

    r = client.get("/flashcards/due", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["front"] == "Due"

    session.delete(user)


def test_card_stats(client, session):
    user = create_user(session, "user", "password")
    token = get_token(client, "user", "password")

    card_due = create_flashcard(session, front="Due", back="A")
    _ = create_flashcard(session, front="New1", back="B")
    _ = create_flashcard(session, front="New2", back="C")

    now = datetime.now(timezone.utc)
    assert card_due.id is not None
    assert user.id is not None

    uf_due = UserFlashcard(
        user_id=user.id, flashcard_id=card_due.id, next_review=now - timedelta(hours=1)
    )
    session.add(uf_due)
    session.commit()

    r = client.get("/flashcards/stats", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    stats = r.json()
    assert stats["due"] == 1
    assert stats["new"] == 2


# ── Anonymous access tests ──────────────────────────────────────────────


def test_anonymous_can_list_cards(anon_client, session):
    create_flashcard(session, front="Q1", back="A1", category="cat1")
    create_flashcard(session, front="Q2", back="A2", category="cat1")

    r = anon_client.get("/flashcards?category=cat1")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_anonymous_gets_all_cards_ignoring_sm2(anon_client, session):
    """Anonymous users see all cards, even ones that would be filtered by SM-2 for a logged-in user."""
    user = create_user(session, "user", "password")
    card = create_flashcard(session, front="Q", back="A", category="cat1")

    # Create a UserFlashcard with next_review far in the future
    # (a logged-in user would NOT see this card, but anonymous should)
    uf = UserFlashcard(
        user_id=user.id,
        flashcard_id=card.id,
        next_review=datetime.now(timezone.utc) + timedelta(days=30),
    )
    session.add(uf)
    session.commit()

    r = anon_client.get("/flashcards?category=cat1")
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_anonymous_review_returns_401(anon_client, session):
    card = create_flashcard(session, front="Q", back="A")

    r = anon_client.post(f"/flashcards/{card.id}/review", json={"quality": 3})
    assert r.status_code == 401


def test_authenticated_list_still_filters_by_sm2(anon_client, session):
    """Logged-in users still get SM-2 filtered results."""
    user = create_user(session, "user", "password")
    token = get_token(anon_client, "user", "password")

    card_due = create_flashcard(session, front="Due", back="A", category="cat1")
    card_future = create_flashcard(session, front="Future", back="B", category="cat1")

    now = datetime.now(timezone.utc)
    session.add(
        UserFlashcard(
            user_id=user.id,
            flashcard_id=card_due.id,
            next_review=now - timedelta(hours=1),
        )
    )
    session.add(
        UserFlashcard(
            user_id=user.id,
            flashcard_id=card_future.id,
            next_review=now + timedelta(days=30),
        )
    )
    session.commit()

    r = anon_client.get(
        "/flashcards?category=cat1",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    # Only the due card should appear (future card filtered out by SM-2)
    assert len(data) == 1
    assert data[0]["front"] == "Due"
