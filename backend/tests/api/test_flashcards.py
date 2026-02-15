import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from datetime import datetime, timedelta, timezone

from app.api.flashcards import router as flashcard_router, err_no_cards_found
from app.api.users import router as user_router, User
from app.database import get_session
from app.api.users import get_current_user, get_password_hash
from app.models import Flashcard, UserFlashcard


@pytest.fixture(name="app")
def app_fixture(session):
    def get_test_session():
        with Session(session.get_bind()) as s:
            yield s

    class FakeUser:
        id = 1

    app = FastAPI()
    app.include_router(flashcard_router)
    app.include_router(user_router)
    app.dependency_overrides[get_session] = get_test_session
    app.dependency_overrides[get_current_user] = lambda: FakeUser()
    return app


@pytest.fixture(name="client")
def client_fixture(app):
    return TestClient(app)


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

    user2 = create_user(session, "user2", "password")
    token2 = get_token(client, "user2", "password")
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
