import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import select

from app.api.lessons import router as lessons_router
from app.api.users import get_current_user, get_optional_user
from app.api.users import router as user_router
from app.database import get_session
from app.models import UserLesson
from tests.conftest import get_test_session


class FakeUser:
    id = 1


@pytest.fixture(name="app")
def app_fixture(session):
    app = FastAPI()
    app.include_router(lessons_router)
    app.include_router(user_router)
    app.dependency_overrides[get_session] = get_test_session(session)
    app.dependency_overrides[get_current_user] = lambda: FakeUser()
    app.dependency_overrides[get_optional_user] = lambda: FakeUser()
    return app


@pytest.fixture(name="client")
def client_fixture(app):
    return TestClient(app)


@pytest.fixture(name="anon_app")
def anon_app_fixture(session):
    """App without get_current_user override -- uses real auth."""
    app = FastAPI()
    app.include_router(lessons_router)
    app.include_router(user_router)
    app.dependency_overrides[get_session] = get_test_session(session)
    return app


@pytest.fixture(name="anon_client")
def anon_client_fixture(anon_app):
    return TestClient(anon_app)


def test_list_lessons_empty(client):
    response = client.get("/lessons")
    assert response.status_code == 200
    assert response.json() == []


def test_list_lessons_returns_lessons(client, create_lesson):
    l1 = create_lesson(slug="lesson-one", title="Lesson One", category="cat-a", order=1)
    l2 = create_lesson(slug="lesson-two", title="Lesson Two", category="cat-b", order=1)

    response = client.get("/lessons")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

    slugs = {item["slug"] for item in data}
    assert slugs == {"lesson-one", "lesson-two"}

    # content field must NOT be present in list response
    for item in data:
        assert "content" not in item

    _ = l1, l2  # referenced to satisfy linter


def test_list_lessons_filter_by_category(client, create_lesson):
    create_lesson(slug="cat-a-lesson", category="cat-a")
    create_lesson(slug="cat-b-lesson", category="cat-b")

    response = client.get("/lessons?category=cat-a")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["slug"] == "cat-a-lesson"


def test_list_lessons_ordered_by_category_and_order(client, create_lesson):
    create_lesson(slug="b-second", category="cat-b", order=2)
    create_lesson(slug="a-first", category="cat-a", order=1)
    create_lesson(slug="b-first", category="cat-b", order=1)

    response = client.get("/lessons")
    assert response.status_code == 200
    data = response.json()
    slugs = [item["slug"] for item in data]
    assert slugs == ["a-first", "b-first", "b-second"]


def test_get_lesson_by_slug(client, create_lesson):
    lesson = create_lesson(
        slug="my-lesson",
        title="My Lesson",
        content="# Heading\n\nBody content here.",
    )

    response = client.get("/lessons/my-lesson")
    assert response.status_code == 200
    data = response.json()
    assert data["slug"] == "my-lesson"
    assert data["title"] == "My Lesson"
    assert "content" in data
    assert data["content"] == lesson.content


def test_get_lesson_not_found(client):
    response = client.get("/lessons/nonexistent-slug")
    assert response.status_code == 404


def test_complete_lesson(client, session, create_user, create_lesson):
    create_user(username="user", password="password")
    lesson = create_lesson(slug="complete-me")

    response = client.post("/lessons/complete-me/complete")
    assert response.status_code == 204

    rows = session.exec(
        select(UserLesson).where(
            UserLesson.user_id == FakeUser.id,
            UserLesson.lesson_id == lesson.id,
        )
    ).all()
    assert len(rows) == 1


def test_complete_lesson_idempotent(client, session, create_user, create_lesson):
    create_user(username="user", password="password")
    lesson = create_lesson(slug="complete-idempotent")

    # Complete twice
    r1 = client.post("/lessons/complete-idempotent/complete")
    r2 = client.post("/lessons/complete-idempotent/complete")

    assert r1.status_code == 204
    assert r2.status_code == 204

    # Only one UserLesson row
    rows = session.exec(
        select(UserLesson).where(
            UserLesson.user_id == FakeUser.id,
            UserLesson.lesson_id == lesson.id,
        )
    ).all()
    assert len(rows) == 1


def test_complete_lesson_not_found(client):
    response = client.post("/lessons/no-such-lesson/complete")
    assert response.status_code == 404


def test_complete_lesson_requires_auth(anon_client, create_lesson):
    create_lesson(slug="auth-required")

    response = anon_client.post("/lessons/auth-required/complete")
    assert response.status_code == 401


def test_lessons_for_category_with_completion(client, session, create_user, create_lesson):
    create_user(username="user", password="password")
    l1 = create_lesson(slug="done-lesson", category="test-cat", order=1)
    create_lesson(slug="not-done-lesson", category="test-cat", order=2)

    # Mark l1 as completed for FakeUser (id=1)
    ul = UserLesson(user_id=FakeUser.id, lesson_id=l1.id)
    session.add(ul)
    session.commit()

    response = client.get("/lessons/by-category/test-cat")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

    by_slug = {item["slug"]: item for item in data}
    assert by_slug["done-lesson"]["completed"] is True
    assert by_slug["not-done-lesson"]["completed"] is False


def test_lessons_for_category_anon(anon_client, create_lesson):
    create_lesson(slug="anon-lesson-1", category="anon-cat", order=1)
    create_lesson(slug="anon-lesson-2", category="anon-cat", order=2)

    response = anon_client.get("/lessons/by-category/anon-cat")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    for item in data:
        assert item["completed"] is False
