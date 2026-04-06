"""Integration tests for the full /problems/{id}/submit pipeline.

Exercises: FastAPI endpoint -> harness builder -> real Judge0 -> result parsing.
Requires `make dev` running so judge0-server is reachable at localhost:2358.

Adding new test cases: append a ProblemFixture to fixtures.FIXTURES
(for harness matrix) or an entry to catalog_solutions.CATALOG_SOLUTIONS
(for catalog smoke). Each entry auto-fans out across all four languages.
"""
import os

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.api.problems as problems_mod
from app.api.problems import router as problems_router
from app.api.users import get_current_user, get_optional_user
from app.api.users import router as users_router
from app.database import get_session
from tests.conftest import get_test_session

# All tests in this directory are integration tests.
pytestmark = pytest.mark.integration

JUDGE0_URL = os.getenv("JUDGE0_URL", "http://localhost:2358")


@pytest.fixture(scope="session", autouse=True)
def judge0_available():
    """Skip the integration suite cleanly if Judge0 is unreachable."""
    try:
        r = httpx.get(f"{JUDGE0_URL}/about", timeout=2.0)
        r.raise_for_status()
    except Exception as e:
        pytest.skip(
            f"Judge0 not reachable at {JUDGE0_URL} - run `make dev` in "
            f"another terminal, or set JUDGE0_URL. ({e})"
        )


@pytest.fixture(name="app")
def app_fixture(session, create_user):
    """Minimal FastAPI app with just the routers we need, auth overridden."""
    user = create_user(username="integration-tester", password="password123")

    class FakeUser:
        id = user.id

    fake_user = FakeUser()

    # Patch JUDGE0_URL so the submit endpoint reaches localhost (host)
    # instead of judge0-server (Docker DNS, unreachable from host).
    # tests/conftest.py imports app.api.users which triggers app/api/__init__.py
    # importing problems.py before our conftest loads, so env-var-based
    # approaches don't work — we must patch the already-loaded module.
    original_url = problems_mod.JUDGE0_URL
    problems_mod.JUDGE0_URL = JUDGE0_URL

    app = FastAPI()
    app.include_router(problems_router)
    app.include_router(users_router)
    app.dependency_overrides[get_session] = get_test_session(session)
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_optional_user] = lambda: fake_user

    yield app

    problems_mod.JUDGE0_URL = original_url


@pytest.fixture(name="client")
def client_fixture(app):
    return TestClient(app)
