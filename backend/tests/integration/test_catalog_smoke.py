"""Catalog smoke tests.

Loads real CodingProblem rows by reading YAML files directly from the
dsa-flash-cards submodule, then submits canonical solutions in all four
languages. Complements the synthetic fixture matrix by validating that
real catalog content still flows through the harness + Judge0 pipeline.
"""
from pathlib import Path

import pytest
import yaml

from app.models import CodingProblem

pytestmark = pytest.mark.integration

from .catalog_solutions import CATALOG_SOLUTIONS

LANGUAGES = ["python", "javascript", "go", "java"]

# Repo layout: backend/tests/integration/test_catalog_smoke.py
#   -> backend/ -> repo root -> dsa-flash-cards/
REPO_ROOT = Path(__file__).resolve().parents[3]
CARDS_ROOT = REPO_ROOT / "dsa-flash-cards"


def _find_yaml_by_title(title: str) -> Path:
    """Locate the YAML file in dsa-flash-cards/ whose title: matches."""
    for path in CARDS_ROOT.rglob("problems/*.yaml"):
        try:
            data = yaml.safe_load(path.read_text()) or {}
        except Exception:
            continue
        if isinstance(data, dict) and data.get("title") == title:
            return path
    raise FileNotFoundError(
        f"Catalog smoke title {title!r} not found under {CARDS_ROOT}. "
        f"Either the catalog drifted or the smoke title needs updating."
    )


def _load_catalog_problem(session, title: str) -> CodingProblem:
    """Read the real YAML and insert a CodingProblem row into the test session."""
    path = _find_yaml_by_title(title)
    data = yaml.safe_load(path.read_text())

    # Derive category from path: dsa-flash-cards/{category}/problems/{slug}.yaml
    rel = path.relative_to(CARDS_ROOT)
    category = rel.parts[0].replace(" ", "-")

    problem = CodingProblem(
        title=data["title"],
        difficulty=data.get("difficulty", "medium"),
        category=category,
        tags=data.get("tags") or [],
        description=data.get("description", ""),
        examples=data.get("examples") or [],
        constraints=data.get("constraints") or [],
        starter_code=data.get("starter_code") or {},
        test_cases=data.get("test_cases") or [],
        solution=data.get("solution") or {},
        hints=data.get("hints") or [],
    )
    session.add(problem)
    session.commit()
    session.refresh(problem)
    return problem


@pytest.mark.parametrize("language", LANGUAGES)
@pytest.mark.parametrize("title", list(CATALOG_SOLUTIONS.keys()))
def test_catalog_smoke(client, session, title: str, language: str):
    problem = _load_catalog_problem(session, title)
    solution = CATALOG_SOLUTIONS[title][language]

    resp = client.post(
        f"/problems/{problem.id}/submit",
        json={"language": language, "code": solution},
    )

    assert resp.status_code == 200, f"HTTP {resp.status_code}: {resp.text}"
    body = resp.json()

    assert body["status"] == "Accepted", (
        f"{title} [{language}] -> status={body['status']!r}\n"
        f"stderr: {body.get('stderr') or ''}\n"
        f"stdout: {body.get('stdout') or ''}"
    )
    assert body["passed"] is True, (
        f"{title} [{language}] -> not all test cases passed\n"
        f"test_results: {body.get('test_results')}"
    )
