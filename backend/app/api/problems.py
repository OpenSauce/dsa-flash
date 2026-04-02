import json
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
    StudySession,
    SubmissionOut,
    TestCaseResult,
    User,
    UserCodingProblem,
)
from ..spaced import sm2
from .users import get_current_user, get_optional_user

router = APIRouter(prefix="/problems", tags=["problems"])

JUDGE0_URL = "http://judge0-server:2358"
PYTHON_LANGUAGE_ID = 71
MAX_CODE_BYTES = 10 * 1024  # 10KB


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
    problems = session.exec(stmt).all()

    if tag:
        problems = [p for p in problems if tag in p.tags]

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
                if ucp.next_review and ucp.next_review <= now:
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


def _build_test_harness(user_code: str, test_cases: list) -> str:
    """Build a Python test harness script that exec()s user code and runs test cases."""
    harness = f"""
import json, sys, traceback

user_code = {json.dumps(user_code)}
exec(user_code, globals())

test_cases = {json.dumps(test_cases)}
results = []

for tc in test_cases:
    inp = tc.get("input", {{}})
    expected = tc.get("expected")
    try:
        # Find the function defined in user_code
        func_name = None
        for name, obj in list(globals().items()):
            if callable(obj) and not name.startswith("_") and name not in ("json", "sys", "traceback"):
                func_name = name
                break
        if func_name is None:
            raise RuntimeError("No callable function found in submitted code")
        func = globals()[func_name]
        if isinstance(inp, dict):
            actual = func(**inp)
        else:
            actual = func(inp)
        passed = actual == expected
        results.append({{
            "input": str(inp),
            "expected": str(expected),
            "actual": str(actual),
            "passed": passed,
        }})
    except Exception as e:
        results.append({{
            "input": str(inp),
            "expected": str(expected),
            "actual": f"ERROR: {{e}}",
            "passed": False,
        }})

print(json.dumps(results))
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

    harness = _build_test_harness(body.code, problem.test_cases)

    start_ms = int(time.time() * 1000)

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                f"{JUDGE0_URL}/submissions",
                params={"base64_encoded": "false", "wait": "true"},
                json={
                    "language_id": PYTHON_LANGUAGE_ID,
                    "source_code": harness,
                    "cpu_time_limit": 5,
                    "memory_limit": 128000,
                },
            )
            resp.raise_for_status()
            judge0_result = resp.json()
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Code execution service unavailable")
    except httpx.TimeoutException:
        raise HTTPException(status_code=503, detail="Code execution service unavailable")
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail="Code execution service unavailable")

    solve_time_ms = int(time.time() * 1000) - start_ms

    status_id = judge0_result.get("status", {}).get("id", 0)
    status_desc = judge0_result.get("status", {}).get("description", "Unknown")
    stdout = judge0_result.get("stdout") or ""
    stderr = judge0_result.get("stderr") or ""
    compile_output = judge0_result.get("compile_output") or ""

    test_results: list[TestCaseResult] = []
    all_passed = False

    if status_id == 3:
        # Accepted — parse JSON output from harness
        try:
            raw_results = json.loads(stdout.strip())
            test_results = [
                TestCaseResult(
                    input=r["input"],
                    expected=r["expected"],
                    actual=r["actual"],
                    passed=r["passed"],
                )
                for r in raw_results
            ]
            all_passed = all(r.passed for r in test_results)
        except (json.JSONDecodeError, KeyError):
            all_passed = False
    elif status_id == 5:
        status_desc = "Time Limit Exceeded"
    elif status_id == 6:
        status_desc = "Compilation Error"
        stderr = compile_output or stderr
    else:
        status_desc = f"Runtime Error (status {status_id})"

    # On first successful submission, create UserCodingProblem if not exists
    if status_id == 3:
        ucp = session.get(UserCodingProblem, (user.id, problem_id))
        if ucp is None:
            ucp = UserCodingProblem(user_id=user.id, coding_problem_id=problem_id)
            session.add(ucp)
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

    ucp = session.get(UserCodingProblem, (user.id, problem_id))
    if ucp is None:
        ucp = UserCodingProblem(user_id=user.id, coding_problem_id=problem_id)
        session.add(ucp)
        session.flush()

    sm2(ucp, body.quality)

    today = datetime.now(timezone.utc).date()
    stmt = pg_insert(StudySession).values(
        user_id=user.id,
        study_date=today,
        cards_reviewed=1,
    ).on_conflict_do_update(
        constraint="uq_studysession_user_date",
        set_={"cards_reviewed": StudySession.__table__.c.cards_reviewed + 1},
    )
    session.execute(stmt)

    session.commit()


@router.get("/{problem_id}/hints/{index}")
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
    return {
        "hint": problem.hints[index],
        "total": len(problem.hints),
        "index": index,
    }
