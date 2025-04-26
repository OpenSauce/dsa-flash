import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine, select
from testcontainers.postgres import PostgresContainer
from datetime import datetime, timedelta, timezone
from sqlalchemy import text

# Import the router and dependencies
from app.api.flashcards import router as flashcard_router
from app.api.users import router as user_router, User
from app.database import get_session
from app.api.users import get_current_user, get_password_hash
from app.models import Flashcard, UserFlashcard


@pytest.fixture(scope="session")
def postgres_container():
    """
    Start a PostgreSQL test container for the duration of the test session.
    """
    with PostgresContainer("postgres:14-alpine") as postgres:
        # Optionally set a database name, user, password:
        # postgres.with_database_name("testdb").with_username("test").with_password("test")
        yield postgres


@pytest.fixture(scope="session")
def engine(postgres_container):
    """
    Create a SQLModel Engine pointing at the testcontainer Postgres.
    Create all tables once at session start.
    """
    engine = create_engine(postgres_container.get_connection_url(), echo=True)
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture(name="session")
def session_fixture(engine):
    """
    Provide a transactional session for each test, rolling back at teardown.
    """
    with Session(engine) as session:
        yield session


@pytest.fixture(name="app")
def app_fixture(session):
    """
    Override FastAPI dependencies to use our test Session & a fake user.
    """

    def get_test_session():
        # create a fresh Session for each request
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


@pytest.fixture(autouse=True)
def clear_db(engine):
    """
    After each test, truncate all our tables and reset their SERIAL sequences.
    """
    yield
    # run after each test
    with engine.begin() as conn:
        # Truncate tables in the correct order (userflashcard references flashcard & user)
        conn.execute(
            text(
                'TRUNCATE TABLE userflashcard, flashcard, "user" RESTART IDENTITY CASCADE;'
            )
        )


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


def create_user(session, **kwargs):
    user = User(username="alice", hashed_password=get_password_hash("secret"))
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def get_token(client) -> str:
    response = client.post("/token", data={"username": "alice", "password": "secret"})
    assert response.status_code == 200
    return response.json()["access_token"]


# Tests
def test_list_cards_empty(client):
    response = client.get("/flashcards")
    assert response.status_code == 200
    assert response.json() == []


def test_list_cards_page_out_of_range(client):
    response = client.get("/flashcards?page=2")
    assert response.status_code == 404
    assert response.json()["detail"] == "Page out of range"


def test_list_cards_filters_and_pagination(client, session):
    # Add sample cards
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

    # Filter by category
    r = client.get("/flashcards?category=cat1")
    assert r.status_code == 200
    assert len(r.json()) == 5

    # Filter by language
    r = client.get("/flashcards?language=lang2")
    assert r.status_code == 200
    assert len(r.json()) == 3

    # Filter by tag
    r = client.get("/flashcards?tag=t1")
    assert r.status_code == 200
    assert len(r.json()) == 5

    # Test pagination
    r = client.get("/flashcards?page=1&page_size=2")
    assert r.status_code == 200
    assert len(r.json()) == 2
    r2 = client.get("/flashcards?page=2&page_size=2")
    assert r2.status_code == 200
    assert len(r2.json()) == 2


def test_review_card_creates_new_userflashcard(client, session):
    user = create_user(session)
    card = create_flashcard(session, front="Q", back="A")

    token = get_token(client)

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
    user = create_user(session)
    token = get_token(client)

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
    user = create_user(session)
    token = get_token(client)

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
