import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import select

from app.api.quizzes import router as quizzes_router
from app.api.users import get_current_user, get_optional_user
from app.api.users import router as user_router
from app.database import get_session
from app.models import UserQuizAttempt
from tests.conftest import get_test_session


class FakeUser:
    id = 1


@pytest.fixture(name="app")
def app_fixture(session):
    app = FastAPI()
    app.include_router(quizzes_router)
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
    app = FastAPI()
    app.include_router(quizzes_router)
    app.include_router(user_router)
    app.dependency_overrides[get_session] = get_test_session(session)
    app.dependency_overrides[get_optional_user] = lambda: None
    return app


@pytest.fixture(name="anon_client")
def anon_client_fixture(anon_app):
    return TestClient(anon_app)


def test_list_quizzes_empty(client):
    response = client.get("/quizzes")
    assert response.status_code == 200
    assert response.json() == []


def test_list_quizzes_returns_quizzes(client, create_quiz, create_quiz_question):
    q1 = create_quiz(slug="quiz-one", title="Quiz One", category="cat-a")
    q2 = create_quiz(slug="quiz-two", title="Quiz Two", category="cat-b")
    create_quiz_question(quiz_id=q1.id, order=0)
    create_quiz_question(quiz_id=q1.id, order=1)

    response = client.get("/quizzes")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

    slugs = {item["slug"] for item in data}
    assert slugs == {"quiz-one", "quiz-two"}

    # questions field must NOT be present in list response
    for item in data:
        assert "questions" not in item

    by_slug = {item["slug"]: item for item in data}
    assert by_slug["quiz-one"]["question_count"] == 2
    assert by_slug["quiz-two"]["question_count"] == 0

    _ = q2


def test_list_quizzes_filter_by_category(client, create_quiz):
    create_quiz(slug="cat-a-quiz", category="cat-a")
    create_quiz(slug="cat-b-quiz", category="cat-b")

    response = client.get("/quizzes?category=cat-a")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["slug"] == "cat-a-quiz"


def test_get_quiz_by_slug(client, create_quiz, create_quiz_question):
    quiz = create_quiz(slug="my-quiz", title="My Quiz", lesson_slug="my-lesson")
    create_quiz_question(quiz_id=quiz.id, question="Q1?", options=["a", "b", "c", "d"], correct_index=0)

    response = client.get("/quizzes/my-quiz")
    assert response.status_code == 200
    data = response.json()
    assert data["slug"] == "my-quiz"
    assert data["title"] == "My Quiz"
    assert data["lesson_slug"] == "my-lesson"
    assert len(data["questions"]) == 1

    q = data["questions"][0]
    assert q["question"] == "Q1?"
    assert q["options"] == ["a", "b", "c", "d"]
    assert q["correct_index"] == 0


def test_get_quiz_not_found(client):
    response = client.get("/quizzes/nonexistent-quiz")
    assert response.status_code == 404


def test_get_quiz_questions_ordered(client, create_quiz, create_quiz_question):
    quiz = create_quiz(slug="ordered-quiz")
    create_quiz_question(quiz_id=quiz.id, question="Third", order=2)
    create_quiz_question(quiz_id=quiz.id, question="First", order=0)
    create_quiz_question(quiz_id=quiz.id, question="Second", order=1)

    response = client.get("/quizzes/ordered-quiz")
    assert response.status_code == 200
    data = response.json()
    questions = data["questions"]
    assert len(questions) == 3
    assert [q["question"] for q in questions] == ["First", "Second", "Third"]


def test_submit_quiz_anonymous(anon_client, session, create_quiz, create_quiz_question):
    quiz = create_quiz(slug="anon-quiz")
    q1 = create_quiz_question(quiz_id=quiz.id, correct_index=1, order=0)
    q2 = create_quiz_question(quiz_id=quiz.id, correct_index=0, order=1)

    response = anon_client.post(
        "/quizzes/anon-quiz/submit",
        json={"answers": {str(q1.id): 1, str(q2.id): 2}},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["score"] == 1
    assert data["total"] == 2

    # No attempt should be saved for anonymous user
    attempts = session.exec(select(UserQuizAttempt)).all()
    assert len(attempts) == 0


def test_submit_quiz_authenticated(client, session, create_user, create_quiz, create_quiz_question):
    create_user(username="user", password="password")
    quiz = create_quiz(slug="auth-quiz")
    q1 = create_quiz_question(quiz_id=quiz.id, correct_index=2, order=0)
    q2 = create_quiz_question(quiz_id=quiz.id, correct_index=0, order=1)

    response = client.post(
        "/quizzes/auth-quiz/submit",
        json={"answers": {str(q1.id): 2, str(q2.id): 0}},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["score"] == 2
    assert data["total"] == 2

    attempts = session.exec(
        select(UserQuizAttempt).where(
            UserQuizAttempt.user_id == FakeUser.id,
            UserQuizAttempt.quiz_id == quiz.id,
        )
    ).all()
    assert len(attempts) == 1
    assert attempts[0].score == 2
    assert attempts[0].total == 2


def test_submit_quiz_replaces_previous_attempt(client, session, create_user, create_quiz, create_quiz_question):
    create_user(username="user", password="password")
    quiz = create_quiz(slug="retry-quiz")
    q1 = create_quiz_question(quiz_id=quiz.id, correct_index=1, order=0)

    # First submission (wrong)
    r1 = client.post(
        "/quizzes/retry-quiz/submit",
        json={"answers": {str(q1.id): 0}},
    )
    assert r1.status_code == 200
    assert r1.json()["score"] == 0

    # Second submission (correct)
    r2 = client.post(
        "/quizzes/retry-quiz/submit",
        json={"answers": {str(q1.id): 1}},
    )
    assert r2.status_code == 200
    assert r2.json()["score"] == 1

    # Only one attempt row should exist
    attempts = session.exec(
        select(UserQuizAttempt).where(
            UserQuizAttempt.user_id == FakeUser.id,
            UserQuizAttempt.quiz_id == quiz.id,
        )
    ).all()
    assert len(attempts) == 1
    assert attempts[0].score == 1


def test_submit_quiz_not_found(client):
    response = client.post(
        "/quizzes/no-such-quiz/submit",
        json={"answers": {}},
    )
    assert response.status_code == 404


def test_submit_quiz_perfect_score(client, create_quiz, create_quiz_question):
    quiz = create_quiz(slug="perfect-quiz")
    q1 = create_quiz_question(quiz_id=quiz.id, correct_index=0, order=0)
    q2 = create_quiz_question(quiz_id=quiz.id, correct_index=1, order=1)
    q3 = create_quiz_question(quiz_id=quiz.id, correct_index=2, order=2)

    response = client.post(
        "/quizzes/perfect-quiz/submit",
        json={"answers": {str(q1.id): 0, str(q2.id): 1, str(q3.id): 2}},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["score"] == 3
    assert data["total"] == 3
    assert all(r["correct"] for r in data["results"])


def test_submit_quiz_zero_score(client, create_quiz, create_quiz_question):
    quiz = create_quiz(slug="zero-quiz")
    q1 = create_quiz_question(quiz_id=quiz.id, correct_index=0, order=0)
    q2 = create_quiz_question(quiz_id=quiz.id, correct_index=1, order=1)

    response = client.post(
        "/quizzes/zero-quiz/submit",
        json={"answers": {str(q1.id): 3, str(q2.id): 3}},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["score"] == 0
    assert data["total"] == 2
    assert not any(r["correct"] for r in data["results"])

    # correct_index and explanation should be present in results
    for r in data["results"]:
        assert "correct_index" in r
        assert "explanation" in r
