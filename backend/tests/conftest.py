import pytest
from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine
from testcontainers.postgres import PostgresContainer

# Import all models so SQLModel.metadata knows about every table
import app.models  # noqa: F401


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
                'TRUNCATE TABLE event, userflashcard, flashcard, "user" RESTART IDENTITY CASCADE;'
            )
        )
