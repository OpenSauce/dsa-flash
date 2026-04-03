import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.api.analytics import router as events_router
from app.api.analytics import summary_router
from app.api.users import router as user_router
from app.database import get_session
from app.models import CodingProblem, Event, UserCodingProblem


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


def test_authenticated_events_include_user_id(client, session, create_user, get_token):
    user = create_user()
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


def test_summary_requires_auth(client):
    resp = client.get("/analytics/summary")
    assert resp.status_code == 401


def test_summary_requires_admin(client, session, create_user, get_token):
    create_user(is_admin=False)
    token = get_token(client, "user", "password")
    resp = client.get("/analytics/summary", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Admin access required"


def test_summary_allowed_for_admin(client, session, create_user, get_token):
    create_user(is_admin=True)
    token = get_token(client, "user", "password")
    resp = client.get("/analytics/summary", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


def test_summary_no_events(client, session, create_user, get_token):
    create_user(is_admin=True)
    token = get_token(client, "user", "password")

    resp = client.get("/analytics/summary", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_sessions"] == 0
    assert data["anonymous_sessions"] == 0
    assert data["avg_cards_per_session"] == 0
    assert data["median_session_duration_ms"] == 0
    assert data["conversion_rate"] == 0


def test_summary_with_seeded_events(client, session, create_user, get_token):
    user = create_user(is_admin=True)
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


def test_summary_with_problem_metrics(client, session, create_user, get_token):
    user = create_user(is_admin=True)
    token = get_token(client, "user", "password")

    # Create a CodingProblem so we can attach a UserCodingProblem
    problem = CodingProblem(
        title="Two Sum",
        difficulty="easy",
        category="data-structures",
        tags=["array"],
        description="Find two numbers that add to target.",
        examples=[],
        constraints=[],
        starter_code={"python": "def two_sum(nums, target): pass"},
        test_cases=[],
        solution={},
        hints=[],
    )
    session.add(problem)
    session.commit()
    session.refresh(problem)

    # Create UserCodingProblem row (simulates user having solved a problem)
    ucp = UserCodingProblem(user_id=user.id, coding_problem_id=problem.id)
    session.add(ucp)
    session.commit()

    # Seed problem_submit events (3 total: 2 passed, 1 failed)
    submit_events = [
        Event(
            session_id="s1",
            user_id=user.id,
            event_type="problem_submit",
            payload={"problem_id": problem.id, "category": "data-structures", "passed": True},
        ),
        Event(
            session_id="s1",
            user_id=user.id,
            event_type="problem_submit",
            payload={"problem_id": problem.id, "category": "data-structures", "passed": True},
        ),
        Event(
            session_id="s2",
            user_id=None,
            event_type="problem_submit",
            payload={"problem_id": problem.id, "category": "data-structures", "passed": False},
        ),
        Event(
            session_id="s1",
            user_id=user.id,
            event_type="problem_review",
            payload={"problem_id": problem.id, "quality": 5},
        ),
    ]
    for e in submit_events:
        session.add(e)
    session.commit()

    resp = client.get("/analytics/summary", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()

    pm = data["problem_metrics"]
    assert pm["total_submissions"] == 3
    assert pm["unique_submitters"] == 2
    assert pm["problem_solve_rate"] == round(2 / 3, 4)
    assert pm["problems_reviewed"] == 1
    assert pm["users_with_problem_reviews"] == 1

    assert data["funnel"]["problem_users"] == 1
    assert data["category_problem_submissions"]["data-structures"] == 3


def test_users_me_returns_is_admin_false(client, session, create_user, get_token):
    create_user(is_admin=False)
    token = get_token(client, "user", "password")
    resp = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "user"
    assert data["is_admin"] is False


def test_users_me_returns_is_admin_true(client, session, create_user, get_token):
    create_user(username="admin", is_admin=True)
    token = get_token(client, "admin", "password")
    resp = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "admin"
    assert data["is_admin"] is True
