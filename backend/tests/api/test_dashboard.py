from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dashboard import router as dashboard_router
from app.api.flashcards import router as flashcard_router
from app.api.users import router as user_router
from app.database import get_session
from app.models import StudySession, UserFlashcard


def _get_test_session(session):
    def get_test_session():
        with session.__class__(session.get_bind()) as s:
            yield s

    return get_test_session


@pytest.fixture(name="app")
def app_fixture(session):
    app = FastAPI()
    app.include_router(flashcard_router)
    app.include_router(user_router)
    app.include_router(dashboard_router)
    app.dependency_overrides[get_session] = _get_test_session(session)
    return app


@pytest.fixture(name="client")
def client_fixture(app):
    return TestClient(app)


def create_user_flashcard(
    session, user_id, flashcard_id, interval=0, easiness=2.5, created_at=None, last_reviewed=None
):
    now = datetime.now(timezone.utc)
    uf = UserFlashcard(
        user_id=user_id,
        flashcard_id=flashcard_id,
        interval=interval,
        easiness=easiness,
        created_at=created_at or now,
        last_reviewed=last_reviewed or now,
    )
    session.add(uf)
    session.commit()
    return uf


def seed_study_session(session, user_id, study_date, cards_reviewed=1):
    ss = StudySession(user_id=user_id, study_date=study_date, cards_reviewed=cards_reviewed)
    session.add(ss)
    session.commit()
    return ss


# ─── Tests ─────────────────────────────────────────────────────────────────────


def test_dashboard_unauthenticated_returns_401(client):
    r = client.get("/users/dashboard")
    assert r.status_code == 401


def test_dashboard_new_user_returns_zeros(client, session, create_user, create_flashcard, get_token):
    create_user("dashuser", "password")
    token = get_token(client, "dashuser", "password")

    # Create some flashcards so domains list is populated
    create_flashcard(category="system-design", title="Card 1")
    create_flashcard(category="aws", title="Card 2")

    r = client.get("/users/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()

    ks = data["knowledge_summary"]
    assert ks["total_concepts_learned"] == 0
    assert ks["concepts_mastered"] == 0
    assert ks["domains_explored"] == 0

    assert data["streak"]["current"] == 0
    assert data["streak"]["longest"] == 0
    assert data["streak"]["today_reviewed"] == 0

    tw = data["this_week"]
    assert tw["concepts_learned"] == 0
    assert tw["domains_studied"] == []
    assert tw["study_days"] == 0

    assert data["weakest_cards"] == []
    assert data["study_calendar"] == []

    # Domains list includes all categories with 0 progress
    domain_slugs = {d["slug"] for d in data["domains"]}
    assert "system-design" in domain_slugs
    assert "aws" in domain_slugs
    for d in data["domains"]:
        assert d["learned"] == 0
        assert d["mastered"] == 0
        assert d["mastery_pct"] == 0


def test_dashboard_with_review_data(client, session, create_user, create_flashcard, get_token):
    user = create_user("dashuser", "password")
    token = get_token(client, "dashuser", "password")

    # Create cards in 2 categories
    card1 = create_flashcard(category="system-design", title="Load Balancing")
    card2 = create_flashcard(category="system-design", title="Caching")
    card3 = create_flashcard(category="aws", title="EC2 vs Lambda")

    # Review all 3; card1 is mastered (interval > 21), card2 and card3 are not
    create_user_flashcard(session, user.id, card1.id, interval=30)
    create_user_flashcard(session, user.id, card2.id, interval=5)
    create_user_flashcard(session, user.id, card3.id, interval=10)

    r = client.get("/users/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()

    ks = data["knowledge_summary"]
    assert ks["total_concepts_learned"] == 3
    assert ks["concepts_mastered"] == 1
    assert ks["domains_explored"] == 2

    domains_by_slug = {d["slug"]: d for d in data["domains"]}
    sd = domains_by_slug["system-design"]
    assert sd["total"] == 2
    assert sd["learned"] == 2
    assert sd["mastered"] == 1
    assert sd["mastery_pct"] == 50

    aws = domains_by_slug["aws"]
    assert aws["total"] == 1
    assert aws["learned"] == 1
    assert aws["mastered"] == 0
    assert aws["mastery_pct"] == 0


def test_dashboard_mastery_threshold(client, session, create_user, create_flashcard, get_token):
    user = create_user("dashuser", "password")
    token = get_token(client, "dashuser", "password")

    card_not_mastered = create_flashcard(category="system-design", title="Not mastered")
    card_mastered = create_flashcard(category="system-design", title="Mastered")
    card_boundary = create_flashcard(category="system-design", title="Boundary")

    # interval <= 21 should NOT be mastered
    create_user_flashcard(session, user.id, card_not_mastered.id, interval=21)
    # interval > 21 SHOULD be mastered
    create_user_flashcard(session, user.id, card_mastered.id, interval=22)
    # interval = 0
    create_user_flashcard(session, user.id, card_boundary.id, interval=0)

    r = client.get("/users/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()

    assert data["knowledge_summary"]["concepts_mastered"] == 1


def test_dashboard_weakest_cards_capped_at_5(client, session, create_user, create_flashcard, get_token):
    user = create_user("dashuser", "password")
    token = get_token(client, "dashuser", "password")

    # Create 7 cards with low easiness
    for i in range(7):
        card = create_flashcard(category="system-design", title=f"Weak card {i}")
        create_user_flashcard(session, user.id, card.id, easiness=1.3 + i * 0.05)

    r = client.get("/users/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()

    assert len(data["weakest_cards"]) == 5


def test_dashboard_weakest_cards_threshold(client, session, create_user, create_flashcard, get_token):
    user = create_user("dashuser", "password")
    token = get_token(client, "dashuser", "password")

    card_ok = create_flashcard(category="system-design", title="OK card")
    card_weak = create_flashcard(category="system-design", title="Weak card")
    card_boundary = create_flashcard(category="system-design", title="Boundary card")

    # easiness >= 2.0 should NOT appear
    create_user_flashcard(session, user.id, card_ok.id, easiness=2.5)
    create_user_flashcard(session, user.id, card_boundary.id, easiness=2.0)
    # easiness < 2.0 SHOULD appear
    create_user_flashcard(session, user.id, card_weak.id, easiness=1.9)

    r = client.get("/users/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()

    assert len(data["weakest_cards"]) == 1
    assert data["weakest_cards"][0]["easiness"] == 1.9


def test_dashboard_weakest_cards_sorted_ascending(client, session, create_user, create_flashcard, get_token):
    user = create_user("dashuser", "password")
    token = get_token(client, "dashuser", "password")

    for easiness in [1.8, 1.4, 1.6]:
        card = create_flashcard(category="system-design", title=f"Card {easiness}")
        create_user_flashcard(session, user.id, card.id, easiness=easiness)

    r = client.get("/users/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()

    easiness_values = [c["easiness"] for c in data["weakest_cards"]]
    assert easiness_values == sorted(easiness_values)
    assert easiness_values[0] == pytest.approx(1.4)


def test_dashboard_this_week_boundary(client, session, create_user, create_flashcard, get_token):
    user = create_user("dashuser", "password")
    token = get_token(client, "dashuser", "password")

    today = datetime.now(timezone.utc).date()
    week_start_date = today - timedelta(days=today.weekday())
    week_start_dt = datetime(week_start_date.year, week_start_date.month, week_start_date.day, tzinfo=timezone.utc)

    card_this_week = create_flashcard(category="system-design", title="This week")
    card_last_week = create_flashcard(category="system-design", title="Last week")

    # This week: created_at inside current week
    create_user_flashcard(
        session, user.id, card_this_week.id,
        created_at=week_start_dt + timedelta(hours=1),
        last_reviewed=week_start_dt + timedelta(hours=1),
    )
    # Last week: created_at before current week
    create_user_flashcard(
        session, user.id, card_last_week.id,
        created_at=week_start_dt - timedelta(days=1),
        last_reviewed=week_start_dt - timedelta(days=1),
    )

    r = client.get("/users/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()

    assert data["this_week"]["concepts_learned"] == 1
    assert len(data["this_week"]["domains_studied"]) == 1


def test_dashboard_study_calendar_current_month(client, session, create_user, get_token):
    user = create_user("dashuser", "password")
    token = get_token(client, "dashuser", "password")

    today = datetime.now(timezone.utc).date()
    first_of_month = today.replace(day=1)

    # Seed sessions in current month
    if first_of_month <= today:
        seed_study_session(session, user.id, first_of_month)
    if today.day > 2:
        seed_study_session(session, user.id, today)

    # Seed a session from last month (should not appear)
    last_month = first_of_month - timedelta(days=1)
    seed_study_session(session, user.id, last_month)

    r = client.get("/users/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()

    calendar = data["study_calendar"]
    # All dates in calendar must be in current month
    for date_str in calendar:
        from datetime import date

        d = date.fromisoformat(date_str)
        assert d.year == today.year
        assert d.month == today.month

    # Last month's date should not be in calendar
    assert last_month.isoformat() not in calendar


def test_dashboard_streak_data(client, session, create_user, get_token):
    user = create_user("dashuser", "password")
    token = get_token(client, "dashuser", "password")

    today = datetime.now(timezone.utc).date()
    seed_study_session(session, user.id, today, cards_reviewed=3)
    seed_study_session(session, user.id, today - timedelta(days=1))

    r = client.get("/users/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()

    assert data["streak"]["current"] == 2
    assert data["streak"]["today_reviewed"] == 3


def test_dashboard_domain_names_human_readable(client, session, create_user, create_flashcard, get_token):
    create_user("dashuser", "password")
    token = get_token(client, "dashuser", "password")

    create_flashcard(category="system-design", title="Card 1")
    create_flashcard(category="big-o-notation", title="Card 2")

    r = client.get("/users/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()

    domains_by_slug = {d["slug"]: d for d in data["domains"]}
    assert domains_by_slug["system-design"]["name"] == "System Design"
    assert domains_by_slug["big-o-notation"]["name"] == "Big O Notation"
