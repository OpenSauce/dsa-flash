"""Harness matrix integration tests.

For each ProblemFixture in fixtures.FIXTURES, submit its known-good
solution in each of the four supported languages and assert the
Judge0 result is "Accepted" with all test cases passing.

This is the regression guard for:
  1. Per-language Judge0 resource limits (memory, CPU time, thread caps)
  2. Harness generation correctness across param-type shapes
"""
import pytest

from app.models import CodingProblem

from .fixtures import FIXTURES, ProblemFixture

pytestmark = pytest.mark.integration

LANGUAGES = ["python", "javascript", "go", "java"]


def _seed_problem(session, fixture: ProblemFixture) -> CodingProblem:
    """Insert a ProblemFixture into the DB as a CodingProblem row."""
    problem = CodingProblem(
        title=fixture.slug,
        difficulty="easy",
        category="integration-test",
        tags=[],
        description=fixture.description,
        examples=[],
        constraints=[],
        starter_code=fixture.starter_code,
        test_cases=fixture.test_cases,
        solution=fixture.solutions,
        hints=[],
    )
    session.add(problem)
    session.commit()
    session.refresh(problem)
    return problem


@pytest.mark.parametrize("language", LANGUAGES)
@pytest.mark.parametrize("fixture", FIXTURES, ids=lambda f: f.slug)
def test_fixture_accepted(client, session, fixture: ProblemFixture, language: str):
    problem = _seed_problem(session, fixture)

    resp = client.post(
        f"/problems/{problem.id}/submit",
        json={"language": language, "code": fixture.solutions[language]},
    )

    assert resp.status_code == 200, f"HTTP {resp.status_code}: {resp.text}"
    body = resp.json()

    assert body["status"] == "Accepted", (
        f"{fixture.slug} [{language}] -> status={body['status']!r}\n"
        f"stderr: {body.get('stderr') or ''}\n"
        f"stdout: {body.get('stdout') or ''}"
    )

    assert body["passed"] is True, (
        f"{fixture.slug} [{language}] -> not all test cases passed\n"
        f"test_results: {body.get('test_results')}"
    )
