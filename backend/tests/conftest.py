import os

os.environ.setdefault("SECRET_KEY", "test-secret")

import pytest
from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine
from testcontainers.postgres import PostgresContainer

# Import all models so SQLModel.metadata knows about every table
import app.models  # noqa: F401
from app.api.users import User, get_password_hash
from app.models import Flashcard


@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:14-alpine") as postgres:
        yield postgres


@pytest.fixture(scope="session")
def engine(postgres_container):
    engine = create_engine(postgres_container.get_connection_url(), echo=True)
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture(name="session")
def session_fixture(engine):
    with Session(engine) as session:
        yield session


@pytest.fixture(autouse=True)
def clear_db(engine):
    yield
    with engine.begin() as conn:
        conn.execute(
            text(
                'TRUNCATE TABLE studysession, event, userflashcard, flashcard, "user" RESTART IDENTITY CASCADE;'
            )
        )


@pytest.fixture
def create_user(session):
    def _create(username="user", password="password", is_admin=False):
        user = User(username=username, hashed_password=get_password_hash(password), is_admin=is_admin)
        session.add(user)
        session.commit()
        session.refresh(user)
        return user

    return _create


@pytest.fixture
def create_flashcard(session):
    def _create(**kwargs):
        kwargs.setdefault("back", "Answer")
        if "title" not in kwargs:
            kwargs["title"] = kwargs.get("front") or "Untitled"
        if "front" not in kwargs:
            kwargs["front"] = kwargs["title"]
        card = Flashcard(**kwargs)
        session.add(card)
        session.commit()
        session.refresh(card)
        return card

    return _create


@pytest.fixture
def get_token():
    def _get_token(client, username, password) -> str:
        response = client.post("/token", data={"username": username, "password": password})
        assert response.status_code == 200
        return response.json()["access_token"]

    return _get_token
