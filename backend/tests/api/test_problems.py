from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import select

from app.api.problems import router as problems_router
from app.api.users import get_current_user, get_optional_user
from app.api.users import router as user_router
from app.database import get_session
from app.models import UserCodingProblem
from tests.conftest import get_test_session


@pytest.fixture(name="app")
def app_fixture(session, create_user):
    user = create_user(username="testuser", password="password123")

    class FakeUser:
        id = user.id

    fake_user = FakeUser()

    app = FastAPI()
    app.include_router(problems_router)
    app.include_router(user_router)
    app.dependency_overrides[get_session] = get_test_session(session)
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_optional_user] = lambda: fake_user
    return app


@pytest.fixture(name="client")
def client_fixture(app):
    return TestClient(app)


@pytest.fixture(name="anon_app")
def anon_app_fixture(session):
    app = FastAPI()
    app.include_router(problems_router)
    app.include_router(user_router)
    app.dependency_overrides[get_session] = get_test_session(session)
    return app


@pytest.fixture(name="anon_client")
def anon_client_fixture(anon_app):
    return TestClient(anon_app)


def test_list_problems(client, create_coding_problem):
    create_coding_problem(title="Two Sum", category="data-structures")
    create_coding_problem(title="Valid Parentheses", category="data-structures", difficulty="easy")

    resp = client.get("/problems")
    assert resp.status_code == 200
    data = resp.json()
    titles = [p["title"] for p in data]
    assert "Two Sum" in titles
    assert "Valid Parentheses" in titles


def test_list_problems_filter_category(client, create_coding_problem):
    create_coding_problem(title="Two Sum", category="data-structures")
    create_coding_problem(title="Binary Search", category="algorithms", difficulty="easy")

    resp = client.get("/problems?category=data-structures")
    assert resp.status_code == 200
    data = resp.json()
    assert all(p["category"] == "data-structures" for p in data)
    assert len(data) == 1


def test_list_problems_filter_difficulty(client, create_coding_problem):
    create_coding_problem(title="Two Sum", category="data-structures", difficulty="easy")
    create_coding_problem(title="Merge Intervals", category="algorithms", difficulty="medium")

    resp = client.get("/problems?difficulty=easy")
    assert resp.status_code == 200
    data = resp.json()
    assert all(p["difficulty"] == "easy" for p in data)
    assert len(data) == 1


def test_list_problems_filter_tag(client, create_coding_problem):
    create_coding_problem(title="Two Sum", category="data-structures", tags=["hash-map", "array"])
    create_coding_problem(title="Valid Parentheses", category="data-structures", tags=["stack"])

    resp = client.get("/problems?tag=hash-map")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "Two Sum"


def test_list_problems_due_status(client, create_coding_problem):
    create_coding_problem(title="Two Sum", category="data-structures")

    # No ucp yet → "new"
    resp = client.get("/problems")
    assert resp.status_code == 200
    data = resp.json()
    p = next(p for p in data if p["title"] == "Two Sum")
    assert p["due_status"] == "new"


def test_get_problem_detail(client, create_coding_problem):
    problem = create_coding_problem(
        title="Two Sum",
        category="data-structures",
        hints=["Hint 1", "Hint 2"],
    )

    resp = client.get(f"/problems/{problem.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Two Sum"
    assert data["category"] == "data-structures"
    assert "description" in data
    assert "examples" in data
    assert "constraints" in data
    assert "starter_code" in data
    assert data["hints_count"] == 2
    # solution must NOT be in detail response
    assert "solution" not in data
    # test_cases must NOT be in detail response
    assert "test_cases" not in data


def test_get_problem_not_found(client):
    resp = client.get("/problems/99999")
    assert resp.status_code == 404


def test_submit_requires_auth(anon_client, create_coding_problem):
    problem = create_coding_problem()
    resp = anon_client.post(f"/problems/{problem.id}/submit", json={"code": "def two_sum(nums, target): pass"})
    assert resp.status_code == 401


def test_submit_code(client, session, create_coding_problem, create_user):
    problem = create_coding_problem(
        title="Two Sum",
        test_cases=[
            {"input": {"nums": [2, 7, 11, 15], "target": 9}, "expected": [0, 1]},
        ],
    )

    harness_output = (
        '[{"input": "{\\"nums\\": [2, 7, 11, 15], \\"target\\": 9}",'
        ' "expected": "[0, 1]", "actual": "[0, 1]", "passed": true}]'
    )
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "status": {"id": 3, "description": "Accepted"},
        "stdout": harness_output,
        "stderr": None,
        "compile_output": None,
    }
    mock_response.raise_for_status = MagicMock()

    with patch("app.api.problems.httpx.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        resp = client.post(f"/problems/{problem.id}/submit", json={"code": "def two_sum(nums, target): return [0, 1]"})

    assert resp.status_code == 200
    data = resp.json()
    assert "passed" in data
    assert "test_results" in data
    assert "status" in data
    assert "solve_time_ms" in data


def test_submit_code_too_large(client, create_coding_problem):
    problem = create_coding_problem()
    large_code = "x = 1\n" * 2000  # well over 10KB
    resp = client.post(f"/problems/{problem.id}/submit", json={"code": large_code})
    assert resp.status_code == 422


def test_submit_judge0_unavailable(client, create_coding_problem):
    problem = create_coding_problem()

    with patch("app.api.problems.httpx.Client") as mock_client_class:
        import httpx as httpx_module
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.side_effect = httpx_module.ConnectError("Connection refused")
        mock_client_class.return_value = mock_client

        resp = client.post(f"/problems/{problem.id}/submit", json={"code": "def two_sum(nums, target): pass"})

    assert resp.status_code == 503
    assert "unavailable" in resp.json()["detail"].lower()


def test_review_problem(client, session, create_coding_problem, create_user):
    problem = create_coding_problem()

    resp = client.post(f"/problems/{problem.id}/review", json={"quality": 3})
    assert resp.status_code == 204

    # Verify UserCodingProblem was created with SM-2 data
    user = session.exec(select(__import__("app.models", fromlist=["User"]).User)).first()
    ucp = session.get(UserCodingProblem, (user.id, problem.id))
    assert ucp is not None
    assert ucp.repetitions == 1
    assert ucp.next_review is not None


def test_review_requires_auth(anon_client, create_coding_problem):
    problem = create_coding_problem()
    resp = anon_client.post(f"/problems/{problem.id}/review", json={"quality": 3})
    assert resp.status_code == 401


def test_hints_progressive(client, create_coding_problem):
    problem = create_coding_problem(hints=["First hint", "Second hint", "Third hint"])

    resp = client.get(f"/problems/{problem.id}/hints/0")
    assert resp.status_code == 200
    data = resp.json()
    assert data["hint"] == "First hint"
    assert data["index"] == 0
    assert data["total"] == 3

    resp = client.get(f"/problems/{problem.id}/hints/1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["hint"] == "Second hint"
    assert data["index"] == 1

    resp = client.get(f"/problems/{problem.id}/hints/2")
    assert resp.status_code == 200
    data = resp.json()
    assert data["hint"] == "Third hint"
    assert data["index"] == 2


def test_hints_out_of_range(client, create_coding_problem):
    problem = create_coding_problem(hints=["Only hint"])
    resp = client.get(f"/problems/{problem.id}/hints/5")
    assert resp.status_code == 404


def test_hints_problem_not_found(client):
    resp = client.get("/problems/99999/hints/0")
    assert resp.status_code == 404


def test_due_problems(client, session, create_coding_problem, create_user):
    problem = create_coding_problem()
    user = session.exec(select(__import__("app.models", fromlist=["User"]).User)).first()

    # Create a UserCodingProblem that is due
    past = datetime.now(timezone.utc) - timedelta(days=1)
    ucp = UserCodingProblem(
        user_id=user.id,
        coding_problem_id=problem.id,
        next_review=past,
    )
    session.add(ucp)
    session.commit()

    resp = client.get("/problems/due")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert any(p["id"] == problem.id for p in data)
    assert all(p["due_status"] == "due" for p in data)


def test_due_problems_requires_auth(anon_client):
    resp = anon_client.get("/problems/due")
    assert resp.status_code == 401
