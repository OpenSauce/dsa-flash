import json
import os
import re
import time
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlmodel import Session, col, select

from ..database import get_session
from ..limiter import limiter
from ..models import (
    CodingProblem,
    CodingProblemDetailOut,
    CodingProblemOut,
    HintOut,
    StudySession,
    SubmissionOut,
    TestCaseResult,
    User,
    UserCodingProblem,
)
from ..spaced import sm2
from .users import get_current_user, get_optional_user

router = APIRouter(prefix="/problems", tags=["problems"])

JUDGE0_URL = os.getenv("JUDGE0_URL", "http://judge0-server:2358")
JUDGE0_AUTHN_TOKEN = os.getenv("JUDGE0_AUTHN_TOKEN", "")
PYTHON_LANGUAGE_ID = 71  # Judge0 CE: Python 3
MAX_CODE_BYTES = 10 * 1024  # 10KB

# Judge0 status codes
JUDGE0_ACCEPTED = 3
JUDGE0_TLE = 5
JUDGE0_COMPILE_ERROR = 6


class ProblemReviewIn(BaseModel):
    quality: int = Field(ge=0, le=5)


class SubmitIn(BaseModel):
    code: str


@router.get("", response_model=list[CodingProblemOut])
def list_problems(
    session: Session = Depends(get_session),
    user: Optional[User] = Depends(get_optional_user),
    category: Optional[str] = Query(None),
    difficulty: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
):
    stmt = select(CodingProblem)
    if category:
        stmt = stmt.where(CodingProblem.category == category)
    if difficulty:
        stmt = stmt.where(CodingProblem.difficulty == difficulty)
    if tag:
        stmt = stmt.where(col(CodingProblem.tags).contains([tag]))
    problems = session.exec(stmt).all()

    due_status_map: dict[int, str] = {}
    if user:
        now = datetime.now(timezone.utc)
        problem_ids = [p.id for p in problems if p.id is not None]
        if problem_ids:
            ucp_rows = session.exec(
                select(UserCodingProblem).where(
                    UserCodingProblem.user_id == user.id,
                    col(UserCodingProblem.coding_problem_id).in_(problem_ids),
                )
            ).all()
            for ucp in ucp_rows:
                nr = ucp.next_review
                if nr and nr.tzinfo is None:
                    nr = nr.replace(tzinfo=timezone.utc)
                if nr and nr <= now:
                    due_status_map[ucp.coding_problem_id] = "due"
                else:
                    due_status_map[ucp.coding_problem_id] = "review"

    result = []
    for p in problems:
        if user:
            status = due_status_map.get(p.id, "new") if p.id is not None else "new"
        else:
            status = None
        result.append(
            CodingProblemOut(
                id=p.id,
                title=p.title,
                difficulty=p.difficulty,
                category=p.category,
                tags=p.tags,
                due_status=status,
            )
        )
    return result


@router.get("/due", response_model=list[CodingProblemOut])
def due_problems(
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    now = datetime.now(timezone.utc)
    stmt = (
        select(CodingProblem)
        .join(
            UserCodingProblem,
            (UserCodingProblem.user_id == user.id)
            & (UserCodingProblem.coding_problem_id == CodingProblem.id),
        )
        .where(
            col(UserCodingProblem.next_review).is_not(None),
            col(UserCodingProblem.next_review) <= now,
        )
        .limit(limit)
    )
    problems = session.exec(stmt).all()
    return [
        CodingProblemOut(
            id=p.id,
            title=p.title,
            difficulty=p.difficulty,
            category=p.category,
            tags=p.tags,
            due_status="due",
        )
        for p in problems
    ]


@router.get("/{problem_id}", response_model=CodingProblemDetailOut)
def get_problem(
    problem_id: int,
    session: Session = Depends(get_session),
    user: Optional[User] = Depends(get_optional_user),
):
    problem = session.get(CodingProblem, problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    return CodingProblemDetailOut(
        id=problem.id,
        title=problem.title,
        difficulty=problem.difficulty,
        category=problem.category,
        tags=problem.tags,
        description=problem.description,
        examples=problem.examples,
        constraints=problem.constraints,
        starter_code=problem.starter_code,
        hints_count=len(problem.hints),
        created_at=problem.created_at,
        updated_at=problem.updated_at,
    )


def _extract_func_name(starter_code: dict) -> str | None:
    """Extract the function name from starter_code's Python def line."""
    python_code = starter_code.get("python", "")
    match = re.search(r"def\s+(\w+)\s*\(", python_code)
    return match.group(1) if match else None


def _build_test_harness(user_code: str, test_cases: list, func_name: str) -> str:
    """Build a Python test harness that runs user code at module top-level.

    User code is placed at module scope (not exec'd) so that
    `from __future__ import annotations` works correctly on Python 3.7
    (Judge0 CE). Typing imports are injected for runtime subscript compat.
    """
    harness = f"""from __future__ import annotations
from typing import List, Dict, Tuple, Set, Optional, Any, Union
import json, sys

{user_code}

try:
    _func = {func_name}
except NameError:
    print(json.dumps([{{"input": "", "expected": "", "actual": "Function '{func_name}' not found", "passed": False}}]))
    sys.exit(0)

_test_cases = {repr(test_cases)}
_results = []

for _tc in _test_cases:
    _inp = _tc.get("input", {{}})
    _expected = _tc.get("expected")
    try:
        if isinstance(_inp, dict):
            _actual = _func(**_inp)
        else:
            _actual = _func(_inp)
        _passed = _actual == _expected
        _results.append({{
            "input": str(_inp),
            "expected": str(_expected),
            "actual": str(_actual),
            "passed": _passed,
        }})
    except Exception as _e:
        _results.append({{
            "input": str(_inp),
            "expected": str(_expected),
            "actual": f"ERROR: {{_e}}",
            "passed": False,
        }})

print(json.dumps(_results))
"""
    return harness


@router.post("/{problem_id}/submit", response_model=SubmissionOut)
@limiter.limit("10/minute")
def submit_code(
    request: Request,
    problem_id: int,
    body: SubmitIn,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    if len(body.code.encode("utf-8")) > MAX_CODE_BYTES:
        raise HTTPException(status_code=422, detail="Code exceeds 10KB limit")

    problem = session.get(CodingProblem, problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    func_name = _extract_func_name(problem.starter_code)
    if not func_name:
        raise HTTPException(status_code=500, detail="Problem has no valid starter code")

    harness = _build_test_harness(body.code, problem.test_cases, func_name)

    start_ms = int(time.time() * 1000)

    try:
        headers = {}
        if JUDGE0_AUTHN_TOKEN:
            headers["X-Auth-Token"] = JUDGE0_AUTHN_TOKEN
        with httpx.Client(timeout=30.0) as http:
            resp = http.post(
                f"{JUDGE0_URL}/submissions",
                params={"base64_encoded": "false", "wait": "true"},
                headers=headers,
                json={
                    "language_id": PYTHON_LANGUAGE_ID,
                    "source_code": harness,
                    "cpu_time_limit": 5,
                    "memory_limit": 128000,
                    "enable_per_process_and_thread_time_limit": True,
                    "enable_per_process_and_thread_memory_limit": True,
                },
            )
            resp.raise_for_status()
            judge0_result = resp.json()
    except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPError):
        raise HTTPException(status_code=503, detail="Code execution service unavailable")
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=503, detail="Code execution service returned invalid response")

    solve_time_ms = int(time.time() * 1000) - start_ms

    status_id = judge0_result.get("status", {}).get("id", 0)
    status_desc = judge0_result.get("status", {}).get("description", "Unknown")
    stdout = judge0_result.get("stdout") or ""
    stderr = judge0_result.get("stderr") or ""
    compile_output = judge0_result.get("compile_output") or ""

    test_results: list[TestCaseResult] = []
    all_passed = False

    if status_id == JUDGE0_ACCEPTED:
        try:
            raw_results = json.loads(stdout.strip())
            test_results = [
                TestCaseResult(
                    input=r["input"],
                    expected=r["expected"] if r["passed"] else "[hidden]",
                    actual=r["actual"],
                    passed=r["passed"],
                )
                for r in raw_results
            ]
            all_passed = all(r.passed for r in test_results)
        except (json.JSONDecodeError, KeyError):
            all_passed = False
    elif status_id == JUDGE0_TLE:
        status_desc = "Time Limit Exceeded"
    elif status_id == JUDGE0_COMPILE_ERROR:
        status_desc = "Compilation Error"
        stderr = compile_output or stderr
    else:
        status_desc = f"Runtime Error (status {status_id})"

    # On first successful submission, create UserCodingProblem if not exists
    if status_id == JUDGE0_ACCEPTED:
        stmt = pg_insert(UserCodingProblem).values(
            user_id=user.id,
            coding_problem_id=problem_id,
        ).on_conflict_do_nothing()
        session.execute(stmt)
        session.commit()

    return SubmissionOut(
        passed=all_passed,
        test_results=test_results,
        stdout=stdout or None,
        stderr=stderr or None,
        status=status_desc,
        solve_time_ms=solve_time_ms,
    )


@router.post("/{problem_id}/review", status_code=204)
def review_problem(
    problem_id: int,
    body: ProblemReviewIn,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    problem = session.get(CodingProblem, problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    # Ensure UserCodingProblem exists (race-safe upsert)
    stmt = pg_insert(UserCodingProblem).values(
        user_id=user.id,
        coding_problem_id=problem_id,
    ).on_conflict_do_nothing()
    session.execute(stmt)
    session.flush()

    ucp = session.get(UserCodingProblem, (user.id, problem_id))
    sm2(ucp, body.quality)

    today = datetime.now(timezone.utc).date()
    stmt = pg_insert(StudySession).values(
        user_id=user.id,
        study_date=today,
        cards_reviewed=0,
        problems_reviewed=1,
    ).on_conflict_do_update(
        constraint="uq_studysession_user_date",
        set_={"problems_reviewed": StudySession.__table__.c.problems_reviewed + 1},
    )
    session.execute(stmt)

    session.commit()


@router.get("/{problem_id}/hints/{index}", response_model=HintOut)
def get_hint(
    problem_id: int,
    index: int,
    session: Session = Depends(get_session),
):
    problem = session.get(CodingProblem, problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    if index < 0 or index >= len(problem.hints):
        raise HTTPException(status_code=404, detail="Hint index out of range")
    return HintOut(hint=problem.hints[index], total=len(problem.hints), index=index)
