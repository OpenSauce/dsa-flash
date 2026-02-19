from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.api.flashcards import categories_router
from app.api.flashcards import router as flashcard_router
from app.api.users import get_current_user
from app.api.users import router as user_router
from app.database import get_session
from app.models import UserFlashcard


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
    app.include_router(categories_router)
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
    app.include_router(categories_router)
    app.include_router(user_router)
    app.dependency_overrides[get_session] = _get_test_session(session)
    return app


@pytest.fixture(name="anon_client")
def anon_client_fixture(anon_app):
    return TestClient(anon_app)


# Tests
def test_list_cards_empty(client):
    response = client.get("/flashcards")
    assert response.status_code == 200
    assert response.json() == []


def test_list_cards_filters_and_pagination(client, session, create_user, create_flashcard, get_token):
    _ = create_user("user", "password")
    token = get_token(client, "user", "password")

    for i in range(5):
        create_flashcard(
            front=f"Q{i}",
            back=f"A{i}",
            category="cat1",
            language="lang1",
            tags=["t1"],
        )
    for i in range(3):
        create_flashcard(
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


def test_review_card_creates_new_userflashcard(client, session, create_user, create_flashcard, get_token):
    user = create_user("user", "password")
    card = create_flashcard(front="Q", back="A")

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


def test_due_cards(client, session, create_user, create_flashcard, get_token):
    user = create_user("user", "password")
    token = get_token(client, "user", "password")

    create_user("user2", "password")
    get_token(client, "user2", "password")
    card_past = create_flashcard(front="Past", back="A1")
    _ = create_flashcard(front="Future", back="A2")
    now = datetime.now(timezone.utc)
    uf1 = UserFlashcard(
        user_id=1, flashcard_id=card_past.id, next_review=now - timedelta(days=1)
    )
    uf2 = UserFlashcard(user_id=1, flashcard_id=card_past.id + 1, next_review=now + timedelta(days=1))
    session.add_all([uf1, uf2])
    session.commit()

    r = client.get("/flashcards/due", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["front"] == "Past"

    session.delete(user)


def test_due_cards_excludes_null_next_review(client, session, create_user, create_flashcard, get_token):
    user = create_user("user", "password")
    token = get_token(client, "user", "password")

    card_due = create_flashcard(front="Due", back="A1")
    card_null = create_flashcard(front="NullReview", back="A2")

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


def test_card_stats(client, session, create_user, create_flashcard, get_token):
    user = create_user("user", "password")
    token = get_token(client, "user", "password")

    card_due = create_flashcard(front="Due", back="A")
    _ = create_flashcard(front="New1", back="B")
    _ = create_flashcard(front="New2", back="C")

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


def test_anonymous_can_list_cards(anon_client, session, create_flashcard):
    create_flashcard(front="Q1", back="A1", category="cat1")
    create_flashcard(front="Q2", back="A2", category="cat1")

    r = anon_client.get("/flashcards?category=cat1")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_anonymous_gets_all_cards_ignoring_sm2(anon_client, session, create_user, create_flashcard):
    """Anonymous users see all cards, even ones that would be filtered by SM-2 for a logged-in user."""
    user = create_user("user", "password")
    card = create_flashcard(front="Q", back="A", category="cat1")

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


def test_anonymous_review_returns_401(anon_client, session, create_flashcard):
    card = create_flashcard(front="Q", back="A")

    r = anon_client.post(f"/flashcards/{card.id}/review", json={"quality": 3})
    assert r.status_code == 401


def test_authenticated_list_still_filters_by_sm2(anon_client, session, create_user, create_flashcard, get_token):
    """Logged-in users still get SM-2 filtered results."""
    user = create_user("user", "password")
    token = get_token(anon_client, "user", "password")

    card_due = create_flashcard(front="Due", back="A", category="cat1")
    card_future = create_flashcard(front="Future", back="B", category="cat1")

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


def test_review_quality_out_of_range_returns_422(client, session, create_flashcard):
    card = create_flashcard(front="Q", back="A")
    r = client.post(f"/flashcards/{card.id}/review", json={"quality": 6})
    assert r.status_code == 422

    r = client.post(f"/flashcards/{card.id}/review", json={"quality": -1})
    assert r.status_code == 422


# ── Categories endpoint tests ────────────────────────────────────────────


def test_categories_anonymous(anon_client, session, create_flashcard):
    create_flashcard(front="Q1", back="A1", category="cat1", language="go")
    create_flashcard(front="Q2", back="A2", category="cat1", language="go")
    create_flashcard(front="Q3", back="A3", category="cat2")

    r = anon_client.get("/categories")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2

    cat1 = next(c for c in data if c["slug"] == "cat1")
    assert cat1["total"] == 2
    assert cat1["name"] == "Cat1"
    assert cat1["due"] is None
    assert cat1["new"] is None
    assert cat1["has_language"] is True

    cat2 = next(c for c in data if c["slug"] == "cat2")
    assert cat2["total"] == 1
    assert cat2["has_language"] is False


def test_categories_authenticated(anon_client, session, create_user, create_flashcard, get_token):
    user = create_user("user", "password")
    token = get_token(anon_client, "user", "password")

    card1 = create_flashcard(front="Q1", back="A1", category="cat1")
    card2 = create_flashcard(front="Q2", back="A2", category="cat1")
    card3 = create_flashcard(front="Q3", back="A3", category="cat1")

    now = datetime.now(timezone.utc)
    uf1 = UserFlashcard(user_id=user.id, flashcard_id=card1.id, next_review=now - timedelta(hours=1))
    uf2 = UserFlashcard(user_id=user.id, flashcard_id=card2.id, next_review=now + timedelta(days=5))
    session.add_all([uf1, uf2])
    session.commit()

    _ = card3

    r = anon_client.get("/categories", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1

    cat = data[0]
    assert cat["slug"] == "cat1"
    assert cat["total"] == 3
    assert cat["due"] == 1
    assert cat["new"] == 1
    assert cat["has_language"] is False
    assert cat["mastered"] == 0
    assert cat["mastery_pct"] == 0


def test_categories_empty(anon_client):
    r = anon_client.get("/categories")
    assert r.status_code == 200
    assert r.json() == []


def test_categories_excludes_null_category(anon_client, session, create_flashcard):
    create_flashcard(front="Q1", back="A1", category="cat1")
    create_flashcard(front="Q2", back="A2", category=None)

    r = anon_client.get("/categories")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["slug"] == "cat1"
    assert data[0]["has_language"] is False


def test_categories_has_language(anon_client, session, create_flashcard):
    """has_language is True only for categories with non-null language cards."""
    create_flashcard(front="Q1", back="A1", category="data-structures", language="go")
    create_flashcard(front="Q2", back="A2", category="system-design", language=None)

    r = anon_client.get("/categories")
    assert r.status_code == 200
    data = r.json()

    ds = next(c for c in data if c["slug"] == "data-structures")
    assert ds["has_language"] is True

    sd = next(c for c in data if c["slug"] == "system-design")
    assert sd["has_language"] is False


def test_categories_authenticated_with_mastery(anon_client, session, create_user, create_flashcard, get_token):
    """3 cards: 1 mastered (interval=30), 1 reviewed-not-mastered (interval=5), 1 new."""
    user = create_user("user", "password")
    token = get_token(anon_client, "user", "password")

    card1 = create_flashcard(front="Q1", back="A1", category="cat1")
    card2 = create_flashcard(front="Q2", back="A2", category="cat1")
    card3 = create_flashcard(front="Q3", back="A3", category="cat1")

    uf1 = UserFlashcard(user_id=user.id, flashcard_id=card1.id, interval=30)
    uf2 = UserFlashcard(user_id=user.id, flashcard_id=card2.id, interval=5)
    session.add_all([uf1, uf2])
    session.commit()

    _ = card3

    r = anon_client.get("/categories", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    cat = next(c for c in data if c["slug"] == "cat1")
    assert cat["mastered"] == 1
    assert cat["learned"] == 2
    assert cat["mastery_pct"] == 33


def test_categories_anonymous_no_mastery(anon_client, session, create_flashcard):
    """Anonymous requests get null mastery fields."""
    create_flashcard(front="Q1", back="A1", category="cat1")
    create_flashcard(front="Q2", back="A2", category="cat1")

    r = anon_client.get("/categories")
    assert r.status_code == 200
    data = r.json()
    cat = next(c for c in data if c["slug"] == "cat1")
    assert cat["mastered"] is None
    assert cat["mastery_pct"] is None
    assert cat["learned"] is None


def test_categories_100_percent_mastery(anon_client, session, create_user, create_flashcard, get_token):
    """All cards mastered: mastery_pct == 100."""
    user = create_user("user", "password")
    token = get_token(anon_client, "user", "password")

    card1 = create_flashcard(front="Q1", back="A1", category="cat1")
    card2 = create_flashcard(front="Q2", back="A2", category="cat1")

    uf1 = UserFlashcard(user_id=user.id, flashcard_id=card1.id, interval=30)
    uf2 = UserFlashcard(user_id=user.id, flashcard_id=card2.id, interval=25)
    session.add_all([uf1, uf2])
    session.commit()

    r = anon_client.get("/categories", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    cat = next(c for c in data if c["slug"] == "cat1")
    assert cat["mastery_pct"] == 100
    assert cat["mastered"] == 2


def test_categories_zero_mastery(anon_client, session, create_user, create_flashcard, get_token):
    """Cards reviewed but interval <= 21: mastered == 0, mastery_pct == 0."""
    user = create_user("user", "password")
    token = get_token(anon_client, "user", "password")

    card1 = create_flashcard(front="Q1", back="A1", category="cat1")
    card2 = create_flashcard(front="Q2", back="A2", category="cat1")

    uf1 = UserFlashcard(user_id=user.id, flashcard_id=card1.id, interval=10)
    uf2 = UserFlashcard(user_id=user.id, flashcard_id=card2.id, interval=21)
    session.add_all([uf1, uf2])
    session.commit()

    r = anon_client.get("/categories", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    cat = next(c for c in data if c["slug"] == "cat1")
    assert cat["mastered"] == 0
    assert cat["mastery_pct"] == 0


def test_categories_learned_pct_partial(anon_client, session, create_user, create_flashcard, get_token):
    """learned_pct is floor(learned / total * 100)."""
    user = create_user("user", "password")
    token = get_token(anon_client, "user", "password")

    # 3 cards total, 1 reviewed
    card1 = create_flashcard(front="Q1", back="A1", category="cat1")
    _card2 = create_flashcard(front="Q2", back="A2", category="cat1")
    _card3 = create_flashcard(front="Q3", back="A3", category="cat1")

    uf1 = UserFlashcard(user_id=user.id, flashcard_id=card1.id, interval=5)
    session.add(uf1)
    session.commit()

    r = anon_client.get("/categories", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    cat = next(c for c in data if c["slug"] == "cat1")
    # floor(1/3 * 100) == 33
    assert cat["learned_pct"] == 33
    assert cat["mastery_pct"] == 0


def test_categories_learned_pct_null_for_anonymous(anon_client, session, create_flashcard):
    """Anonymous users get learned_pct == null."""
    create_flashcard(front="Q1", back="A1", category="cat1")
    create_flashcard(front="Q2", back="A2", category="cat1")

    r = anon_client.get("/categories")
    assert r.status_code == 200
    data = r.json()
    cat = next(c for c in data if c["slug"] == "cat1")
    assert cat["learned_pct"] is None


def test_categories_learned_pct_100_when_all_reviewed(anon_client, session, create_user, create_flashcard, get_token):
    """learned_pct == 100 when all cards reviewed."""
    user = create_user("user", "password")
    token = get_token(anon_client, "user", "password")

    card1 = create_flashcard(front="Q1", back="A1", category="cat1")
    card2 = create_flashcard(front="Q2", back="A2", category="cat1")

    uf1 = UserFlashcard(user_id=user.id, flashcard_id=card1.id, interval=5)
    uf2 = UserFlashcard(user_id=user.id, flashcard_id=card2.id, interval=5)
    session.add_all([uf1, uf2])
    session.commit()

    r = anon_client.get("/categories", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    cat = next(c for c in data if c["slug"] == "cat1")
    assert cat["learned_pct"] == 100
    assert cat["mastery_pct"] == 0


def test_categories_learned_pct_zero_when_nothing_reviewed(
    anon_client, session, create_user, create_flashcard, get_token,
):
    """learned_pct == 0 when no cards reviewed."""
    create_user("user", "password")
    token = get_token(anon_client, "user", "password")

    _card1 = create_flashcard(front="Q1", back="A1", category="cat1")
    _card2 = create_flashcard(front="Q2", back="A2", category="cat1")

    r = anon_client.get("/categories", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    cat = next(c for c in data if c["slug"] == "cat1")
    assert cat["learned_pct"] == 0


# ── Mode parameter tests ─────────────────────────────────────────────────


def test_list_cards_mode_due(anon_client, session, create_user, create_flashcard, get_token):
    """mode=due returns only cards with next_review <= now."""
    user = create_user("user", "password")
    token = get_token(anon_client, "user", "password")

    card_due = create_flashcard(front="Due", back="A1", category="cat1")
    card_future = create_flashcard(front="Future", back="A2", category="cat1")
    _card_new = create_flashcard(front="New", back="A3", category="cat1")

    now = datetime.now(timezone.utc)
    uf_due = UserFlashcard(user_id=user.id, flashcard_id=card_due.id, next_review=now - timedelta(hours=1))
    uf_future = UserFlashcard(user_id=user.id, flashcard_id=card_future.id, next_review=now + timedelta(days=5))
    session.add_all([uf_due, uf_future])
    session.commit()

    r = anon_client.get("/flashcards?mode=due", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["front"] == "Due"


def test_list_cards_mode_new(anon_client, session, create_user, create_flashcard, get_token):
    """mode=new returns only cards with no UserFlashcard row for this user."""
    user = create_user("user", "password")
    token = get_token(anon_client, "user", "password")

    card_reviewed = create_flashcard(front="Reviewed", back="A1", category="cat1")
    _card_new1 = create_flashcard(front="New1", back="A2", category="cat1")
    _card_new2 = create_flashcard(front="New2", back="A3", category="cat1")

    now = datetime.now(timezone.utc)
    uf = UserFlashcard(user_id=user.id, flashcard_id=card_reviewed.id, next_review=now + timedelta(days=1))
    session.add(uf)
    session.commit()

    r = anon_client.get("/flashcards?mode=new", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    fronts = {c["front"] for c in data}
    assert "Reviewed" not in fronts
    assert "New1" in fronts
    assert "New2" in fronts


def test_list_cards_mode_new_default_limit(anon_client, session, create_user, create_flashcard, get_token):
    """mode=new without explicit limit defaults to 10 cards."""
    create_user("user", "password")
    token = get_token(anon_client, "user", "password")

    for i in range(15):
        create_flashcard(front=f"Card{i}", back="A", category="cat1")

    r = anon_client.get("/flashcards?mode=new", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert len(r.json()) == 10


def test_list_cards_mode_new_custom_limit(anon_client, session, create_user, create_flashcard, get_token):
    """mode=new with explicit limit respects that limit."""
    create_user("user", "password")
    token = get_token(anon_client, "user", "password")

    for i in range(15):
        create_flashcard(front=f"Card{i}", back="A", category="cat1")

    r = anon_client.get("/flashcards?mode=new&limit=5", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert len(r.json()) == 5


def test_list_cards_mode_due_no_limit(anon_client, session, create_user, create_flashcard, get_token):
    """mode=due without explicit limit returns all due cards."""
    user = create_user("user", "password")
    token = get_token(anon_client, "user", "password")

    now = datetime.now(timezone.utc)
    for i in range(15):
        card = create_flashcard(front=f"Due{i}", back="A", category="cat1")
        uf = UserFlashcard(user_id=user.id, flashcard_id=card.id, next_review=now - timedelta(hours=1))
        session.add(uf)
    session.commit()

    r = anon_client.get("/flashcards?mode=due", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert len(r.json()) == 15


def test_list_cards_mode_all(anon_client, session, create_user, create_flashcard, get_token):
    """mode=all returns the same as default (due + new)."""
    user = create_user("user", "password")
    token = get_token(anon_client, "user", "password")

    card_due = create_flashcard(front="Due", back="A1", category="cat1")
    _card_new = create_flashcard(front="New", back="A2", category="cat1")

    now = datetime.now(timezone.utc)
    uf = UserFlashcard(user_id=user.id, flashcard_id=card_due.id, next_review=now - timedelta(hours=1))
    session.add(uf)
    session.commit()

    r_default = anon_client.get("/flashcards?category=cat1", headers={"Authorization": f"Bearer {token}"})
    r_all = anon_client.get("/flashcards?category=cat1&mode=all", headers={"Authorization": f"Bearer {token}"})

    assert r_default.status_code == 200
    assert r_all.status_code == 200
    assert len(r_all.json()) == len(r_default.json())


def test_list_cards_mode_invalid_returns_422(anon_client, session, create_user, create_flashcard, get_token):
    """Invalid mode value returns 422."""
    create_user("user", "password")
    token = get_token(anon_client, "user", "password")

    r = anon_client.get("/flashcards?mode=invalid", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 422


def test_list_cards_mode_ignored_for_anonymous(anon_client, session, create_user, create_flashcard):
    """Anonymous users with mode=new still get all cards."""
    user = create_user("user", "password")
    card1 = create_flashcard(front="Q1", back="A1", category="cat1")
    _card2 = create_flashcard(front="Q2", back="A2", category="cat1")

    now = datetime.now(timezone.utc)
    uf = UserFlashcard(user_id=user.id, flashcard_id=card1.id, next_review=now + timedelta(days=5))
    session.add(uf)
    session.commit()

    r = anon_client.get("/flashcards?category=cat1&mode=new")
    assert r.status_code == 200
    # Anonymous: all 2 cards returned regardless of mode
    assert len(r.json()) == 2


def test_anonymous_invalid_mode_returns_200(anon_client, session, create_flashcard):
    """Anonymous users with an invalid mode value still get 200 (mode is ignored)."""
    create_flashcard(front="Q1", back="A1", category="cat1")

    r = anon_client.get("/flashcards?category=cat1&mode=invalid")
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_list_cards_mode_with_category_filter(anon_client, session, create_user, create_flashcard, get_token):
    """mode=due combined with category filter works correctly."""
    user = create_user("user", "password")
    token = get_token(anon_client, "user", "password")

    card_due_cat1 = create_flashcard(front="Due-Cat1", back="A1", category="cat1")
    card_due_cat2 = create_flashcard(front="Due-Cat2", back="A2", category="cat2")
    _card_new = create_flashcard(front="New-Cat1", back="A3", category="cat1")

    now = datetime.now(timezone.utc)
    uf1 = UserFlashcard(user_id=user.id, flashcard_id=card_due_cat1.id, next_review=now - timedelta(hours=1))
    uf2 = UserFlashcard(user_id=user.id, flashcard_id=card_due_cat2.id, next_review=now - timedelta(hours=1))
    session.add_all([uf1, uf2])
    session.commit()

    r = anon_client.get("/flashcards?mode=due&category=cat1", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["front"] == "Due-Cat1"
