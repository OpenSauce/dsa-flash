import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.api.analytics import router as events_router
from app.api.analytics import summary_router
from app.api.users import get_password_hash
from app.api.users import router as user_router
from app.database import get_session
from app.models import Event, User


def create_user(session, username="user", password="password"):
    user = User(username=username, hashed_password=get_password_hash(password))
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def get_token(client, username, password) -> str:
    resp = client.post("/token", data={"username": username, "password": password})
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest.fixture(name="app")
def app_fixture(session):
    def get_test_session():
        with Session(session.get_bind()) as s:
            yield s

    app = FastAPI()
    app.include_router(events_router)
    app.include_router(summary_router)
    app.include_router(user_router)
    app.dependency_overrides[get_session] = get_test_session
    return app


@pytest.fixture(name="client")
def client_fixture(app):
    return TestClient(app)


def test_anonymous_event_creation(client):
    resp = client.post("/events", json={"event_type": "page_view", "payload": {"page": "/"}})
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert data["id"] >= 1
    # session_id cookie should be set
    assert "session_id" in resp.cookies


def test_session_id_persistence(client):
    resp1 = client.post("/events", json={"event_type": "page_view", "payload": {}})
    sid1 = resp1.cookies["session_id"]

    # Second request with the cookie should reuse the same session_id
    resp2 = client.post(
        "/events",
        json={"event_type": "card_flip", "payload": {}},
        cookies={"session_id": sid1},
    )
    assert resp2.status_code == 201
    # Should NOT set a new cookie since one was already present
    assert "session_id" not in resp2.cookies


def test_batch_event_ingestion(client):
    events = [
        {"event_type": "page_view", "payload": {"page": "/"}},
        {"event_type": "card_flip", "payload": {"card_id": 1}},
        {"event_type": "card_review", "payload": {"card_id": 1, "quality": 3}},
    ]
    resp = client.post("/events/batch", json={"events": events})
    assert resp.status_code == 201
    assert resp.json()["count"] == 3


def test_authenticated_events_include_user_id(client, session):
    user = create_user(session)
    token = get_token(client, "user", "password")

    resp = client.post(
        "/events",
        json={"event_type": "page_view", "payload": {}},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    event_id = resp.json()["id"]

    event = session.get(Event, event_id)
    assert event is not None
    assert event.user_id == user.id


def test_anonymous_events_have_null_user_id(client, session):
    resp = client.post("/events", json={"event_type": "page_view", "payload": {}})
    event_id = resp.json()["id"]

    event = session.get(Event, event_id)
    assert event is not None
    assert event.user_id is None


def test_summary_no_events(client, session):
    create_user(session)
    token = get_token(client, "user", "password")

    resp = client.get("/analytics/summary", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_sessions"] == 0
    assert data["anonymous_sessions"] == 0
    assert data["avg_cards_per_session"] == 0
    assert data["median_session_duration_ms"] == 0
    assert data["conversion_rate"] == 0


def test_summary_with_seeded_events(client, session):
    user = create_user(session)
    token = get_token(client, "user", "password")

    # Seed events: 2 sessions - one anonymous, one authenticated
    # Anonymous session with 2 card reviews
    anon_events = [
        Event(session_id="anon-1", user_id=None, event_type="page_view", payload={"page": "/"}),
        Event(session_id="anon-1", user_id=None, event_type="card_review", payload={"card_id": 1}),
        Event(session_id="anon-1", user_id=None, event_type="card_review", payload={"card_id": 2}),
        Event(session_id="anon-1", user_id=None, event_type="session_end", payload={"duration_ms": 30000}),
    ]
    # Authenticated session with 1 card review
    auth_events = [
        Event(session_id="auth-1", user_id=user.id, event_type="page_view", payload={"page": "/"}),
        Event(session_id="auth-1", user_id=user.id, event_type="card_review", payload={"card_id": 3}),
        Event(session_id="auth-1", user_id=user.id, event_type="session_end", payload={"duration_ms": 15000}),
    ]
    for e in anon_events + auth_events:
        session.add(e)
    session.commit()

    resp = client.get("/analytics/summary", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_sessions"] == 2
    assert data["anonymous_sessions"] == 1
    # avg cards: (2 + 1) / 2 = 1.5
    assert data["avg_cards_per_session"] == 1.5
    # median of [15000, 30000] = 22500
    assert data["median_session_duration_ms"] == 22500.0
    # conversion: 1 authed / 2 total = 0.5
    assert data["conversion_rate"] == 0.5
    # drop-off: anon-1 has 2 reviews (bucket "1-3"), auth-1 has 1 review (bucket "1-3")
    assert data["drop_off_distribution"]["1-3"] == 2
