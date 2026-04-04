import json
import os
import time
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlmodel import Session, col, select

from ..database import get_session
from ..harnesses import build as build_harness
from ..harnesses import extract_func_name
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
MAX_CODE_BYTES = 10 * 1024  # 10KB

LANGUAGE_CONFIG = {
    "python": {"judge0_id": 71, "monaco_mode": "python"},
    "javascript": {"judge0_id": 63, "monaco_mode": "javascript"},
    "go": {"judge0_id": 60, "monaco_mode": "go"},
    "java": {"judge0_id": 62, "monaco_mode": "java"},
}

# Judge0 status codes
JUDGE0_ACCEPTED = 3
JUDGE0_TLE = 5


class DifficultyBreakdown(BaseModel):
    easy: int = 0
    medium: int = 0
    hard: int = 0


class ProblemCategoryOut(BaseModel):
    category: str
    total: int
    solved: Optional[int] = None
    due: Optional[int] = None
    mastered: Optional[int] = None
    difficulty: DifficultyBreakdown
    languages: list[str]
JUDGE0_COMPILE_ERROR = 6


class ProblemReviewIn(BaseModel):
    quality: int = Field(ge=0, le=5)


class SubmitIn(BaseModel):
    code: str
    language: str = "python"


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


@router.get("/categories", response_model=list[ProblemCategoryOut])
def list_problem_categories(
    session: Session = Depends(get_session),
    user: Optional[User] = Depends(get_optional_user),
):
    rows = session.exec(select(CodingProblem)).all()

    # Group by category
    category_map: dict[str, dict] = {}
    for p in rows:
        cat = p.category or "unknown"
        if cat not in category_map:
            category_map[cat] = {"total": 0, "difficulty": {"easy": 0, "medium": 0, "hard": 0}, "languages": set()}
        category_map[cat]["total"] += 1
        diff = (p.difficulty or "").lower()
        if diff in category_map[cat]["difficulty"]:
            category_map[cat]["difficulty"][diff] += 1
        for lang in (p.starter_code or {}).keys():
            category_map[cat]["languages"].add(lang)

    if not category_map:
        return []

    # Build per-category user stats if authenticated
    user_stats: dict[str, dict] = {}
    if user:
        now = datetime.now(timezone.utc)
        ucp_rows = session.exec(
            select(UserCodingProblem).where(UserCodingProblem.user_id == user.id)
        ).all()
        # Join with problem to get category
        problem_ids = [ucp.coding_problem_id for ucp in ucp_rows]
        if problem_ids:
            problems_by_id: dict[int, CodingProblem] = {
                p.id: p for p in session.exec(
                    select(CodingProblem).where(col(CodingProblem.id).in_(problem_ids))
                ).all()
            }
            for ucp in ucp_rows:
                prob = problems_by_id.get(ucp.coding_problem_id)
                if not prob:
                    continue
                cat = prob.category or "unknown"
                if cat not in user_stats:
                    user_stats[cat] = {"solved": 0, "due": 0, "mastered": 0}
                user_stats[cat]["solved"] += 1
                nr = ucp.next_review
                if nr:
                    if nr.tzinfo is None:
                        nr = nr.replace(tzinfo=timezone.utc)
                    if nr <= now:
                        user_stats[cat]["due"] += 1
                if ucp.interval >= 21:
                    user_stats[cat]["mastered"] += 1

    result = []
    for cat, stats in category_map.items():
        languages = sorted(stats["languages"])
        if user:
            ust = user_stats.get(cat, {"solved": 0, "due": 0, "mastered": 0})
            result.append({
                "category": cat,
                "total": stats["total"],
                "solved": ust["solved"],
                "due": ust["due"],
                "mastered": ust["mastered"],
                "difficulty": stats["difficulty"],
                "languages": languages,
            })
        else:
            result.append({
                "category": cat,
                "total": stats["total"],
                "solved": None,
                "due": None,
                "mastered": None,
                "difficulty": stats["difficulty"],
                "languages": languages,
            })

    return result


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

    if body.language not in LANGUAGE_CONFIG:
        raise HTTPException(status_code=422, detail=f"Unsupported language: {body.language}")

    problem = session.get(CodingProblem, problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    if not problem.starter_code or body.language not in problem.starter_code:
        raise HTTPException(status_code=422, detail=f"This problem does not support {body.language} yet")

    func_name = extract_func_name(body.language, problem.starter_code)
    if not func_name:
        raise HTTPException(status_code=500, detail="Problem has no valid starter code")

    harness = build_harness(body.language, body.code, problem.test_cases, func_name)

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
                    "language_id": LANGUAGE_CONFIG[body.language]["judge0_id"],
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
            # JS/Go/Java harnesses print ===HARNESS_OUTPUT=== before the JSON
            raw_output = stdout
            marker = "===HARNESS_OUTPUT==="
            if marker in raw_output:
                raw_output = raw_output.split(marker, 1)[1].strip()
            else:
                raw_output = raw_output.strip()
            raw_results = json.loads(raw_output)
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
