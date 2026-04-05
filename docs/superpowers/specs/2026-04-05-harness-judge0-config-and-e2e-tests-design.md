# Harness Judge0 Config + Integration Tests — Design

**Date:** 2026-04-05
**Status:** Proposed (revised)
**Author:** brainstorming session output
**Related:** `backend/app/harnesses/`, `backend/app/api/problems.py`, OpenSauce/dsa-flash#154

**Revision note:** Integration-test layer redesigned around a declarative `ProblemFixture` registry and the FastAPI `TestClient`, exercising the real `/api/problems/{id}/submit` code path through a TestContainers Postgres. Tests run from the host against Judge0 exposed on `localhost:2358`. The fixture registry makes adding new cases a one-line append. Config-fix scope is unchanged.

## Problem Statement

Generated test harnesses for JavaScript, Go, and Java fail on Judge0 with resource-starvation errors, even when the user's function body is empty. Python works. Cross-referencing the errors with the submission config at `backend/app/api/problems.py:320-323` reveals the root cause: a uniform resource budget is applied to all four language runtimes, sized for CPython.

Observed error signatures on empty functions:

| Language | Error | Diagnosis |
|---|---|---|
| Java | `Could not reserve enough space for 256000KB object heap` | The JVM's default initial heap reservation is ~256 MB. Current `memory_limit` is 128 MB. The JVM refuses to boot; `256000KB` in the error is the exact size the VM requested. |
| Go | `runtime/cgo: pthread_create failed: Resource temporarily unavailable` | The Go runtime spawns ~10 threads at startup (sysmon, GC, scheduler, cgo workers). Combined with `enable_per_process_and_thread_memory_limit=true`, the sandbox hits `RLIMIT_NPROC` (EAGAIN from pthread_create). |
| JavaScript | Time Limit Exceeded | Node cold start + V8 JIT warmup under isolate's strict cgroups is slow. With `enable_per_process_and_thread_time_limit=true` the 5 s CPU budget is split per thread; startup alone consumes most of it. |

Python works because CPython has a ~5 MB RSS at startup, is single-threaded, and has no JIT warmup. The existing 128 MB / 5 s / per-thread budget is comfortable for Python and fatal for everything else.

### Existing test coverage does not catch this

There are already 363 lines of harness tests (`backend/tests/test_harnesses_js.py`, `test_harnesses_go.py`, `test_harnesses_java.py`) plus 757 lines of type-conversion tests (`backend/tests/harnesses/test_type_conversion.py`). **All 84 tests pass.** But they are pure string-assertion tests: they check that the generated harness contains expected substrings. They never execute the generated code against a real language runtime. A harness that is syntactically valid but resource-starved at execution slips through cleanly.

The gap this spec closes is the one test layer that would have caught this: **integration tests that submit real code through the production submit endpoint to a live Judge0 and assert on the returned results.**

## Goals

1. Fix the production submit path so JavaScript, Go, and Java work for all existing problems.
2. Add an opt-in integration test layer that exercises the full submit pipeline (`/api/problems/{id}/submit` → harness generation → Judge0 → result parsing) against a running Judge0.
3. Make the new tests a regression guard: reverting any language's resource budget to a broken value must cause a test to fail with a clear diagnostic.
4. Keep the default `pytest backend/tests/` run fast and offline (no Judge0 dependency).
5. Make adding a new test case trivial — a single append to a declarative fixture list that auto-fans out across all four languages.

## Non-Goals

- Replacing the string-template harness architecture. The approach is sound; the bug is config, not design.
- Testing the frontend submission flow. That is a separate layer.
- Adding TestContainers for Judge0. Judge0 requires 4+ service containers (db, redis, server, workers), which is too heavy for per-test-session setup. Tests target the running dev stack instead.
- Phase 2 coverage (wider param-type matrix, error paths). Tracked as follow-up work in TODOS.md after Phase 1 is green.
- A CI workflow that brings up the full stack and runs the integration tests. Tracked as follow-up.

## Architecture

```
docker-compose.yml
    judge0-server now publishes 2358:2358 to host
           │
           ▼
LANGUAGE_CONFIG  (backend/app/api/problems.py)
    extended with per-language resource budget
           │
           │ same dict, new "judge0_limits" field per entry
           ▼
submit_code endpoint
    reads LANGUAGE_CONFIG[language]["judge0_limits"]
    instead of hardcoded uniform limits
           │
           ▼
Judge0 POST /submissions
    same call shape, now with per-language budget
           │
           ▼
Harness executes successfully under language-appropriate limits

           ▲  (SAME PATH, exercised end-to-end by tests)
           │
backend/tests/integration/
    marker: @pytest.mark.integration   (opt-in, skipped by default)
    conftest: TestContainers Postgres + FastAPI TestClient +
              Judge0 reachability check (skips module if unreachable)
    fixtures.py:          ProblemFixture dataclass registry
    catalog_solutions.py: {slug: {lang: source}} for catalog smoke
    test_harness_matrix.py: parametrized over FIXTURES × 4 languages
    test_catalog_smoke.py:  parametrized over 2 real catalog slugs × 4 languages
```

Tests import the FastAPI app and `LANGUAGE_CONFIG` from the production modules, then POST to `/api/problems/{id}/submit` via `TestClient`. The submit endpoint hits the real (host-reachable) Judge0. Every test therefore exercises the exact resource budget production uses, plus the real harness builder and the real endpoint code. Revert the budget in production, tests fail. That is the regression-guard property.

## Scope

### In scope

1. Per-language Judge0 resource config, stored as a `judge0_limits` dict inside each `LANGUAGE_CONFIG` entry.
2. Submit endpoint change at `backend/app/api/problems.py:317-324` to read limits from `LANGUAGE_CONFIG` instead of hardcoding.
3. Publish `judge0-server` port 2358 to host in `docker-compose.yml` so host-run pytest can reach it.
4. New test directory `backend/tests/integration/` with:
   - `conftest.py` — TestContainers Postgres fixture, FastAPI `TestClient` with dependency overrides, Judge0 reachability check, `seed_fixture` helper.
   - `fixtures.py` — `ProblemFixture` dataclass and the `FIXTURES` registry.
   - `catalog_solutions.py` — `{slug: {lang: source}}` map for catalog smoke tests.
   - `test_harness_matrix.py` — parametrized over `FIXTURES × languages`.
   - `test_catalog_smoke.py` — parametrized over two real catalog slugs × languages.
5. New pytest marker `integration` registered in `backend/pytest.ini` with `-m "not integration"` as the default.
6. New Makefile target `test-integration` that runs the integration tests from the host.
7. Phase 1 test matrix:
   - Six `ProblemFixture` entries (primitives, arrays, strings, ListNode, TreeNode, Graph) × 4 languages = 24 harness-matrix tests.
   - Two catalog smoke slugs × 4 languages = 8 catalog smoke tests.
   - Total: 32 tests.

### Out of scope (Phase 2, tracked in TODOS.md)

- Wider param-type coverage (additional shapes, nested types)
- Error paths: function missing, runtime exception inside user code, wrong return type, malformed source × 4 languages
- CI workflow that brings up the dev stack and runs `pytest -m integration` on PRs touching harness or submit code
- Performance assertions / watchdog for test wall-clock times

## Component Details

### Component 1: Per-language `LANGUAGE_CONFIG`

**File:** `backend/app/api/problems.py`

**Current shape** (line 37):
```python
LANGUAGE_CONFIG = {
    "python":     {"judge0_id": 71, "monaco_mode": "python"},
    "javascript": {"judge0_id": 63, "monaco_mode": "javascript"},
    "go":         {"judge0_id": 60, "monaco_mode": "go"},
    "java":       {"judge0_id": 62, "monaco_mode": "java"},
}
```

**New shape:**
```python
LANGUAGE_CONFIG = {
    "python": {
        "judge0_id": 71,
        "monaco_mode": "python",
        "judge0_limits": {
            "cpu_time_limit": 5,
            "memory_limit": 128000,         # 128 MB — comfortable for CPython
            "enable_per_process_and_thread_time_limit": True,
            "enable_per_process_and_thread_memory_limit": True,
        },
    },
    "javascript": {
        "judge0_id": 63,
        "monaco_mode": "javascript",
        "judge0_limits": {
            "cpu_time_limit": 10,           # Node + V8 JIT warmup
            "memory_limit": 256000,         # 256 MB for V8 heap
            "enable_per_process_and_thread_time_limit": False,
            "enable_per_process_and_thread_memory_limit": False,
        },
    },
    "go": {
        "judge0_id": 60,
        "monaco_mode": "go",
        "judge0_limits": {
            "cpu_time_limit": 10,
            "memory_limit": 256000,
            "max_processes_and_or_threads": 60,  # Go runtime spawns ~10+
            "enable_per_process_and_thread_time_limit": False,
            "enable_per_process_and_thread_memory_limit": False,
        },
    },
    "java": {
        "judge0_id": 62,
        "monaco_mode": "java",
        "judge0_limits": {
            "cpu_time_limit": 10,
            "memory_limit": 512000,         # JVM default heap + overhead
            "max_processes_and_or_threads": 60,  # JVM is multi-threaded
            "enable_per_process_and_thread_time_limit": False,
            "enable_per_process_and_thread_memory_limit": False,
        },
    },
}
```

**Submit endpoint change** at `backend/app/api/problems.py:317-324`:

Before:
```python
json={
    "language_id": LANGUAGE_CONFIG[body.language]["judge0_id"],
    "source_code": harness,
    "cpu_time_limit": 5,
    "memory_limit": 128000,
    "enable_per_process_and_thread_time_limit": True,
    "enable_per_process_and_thread_memory_limit": True,
},
```

After:
```python
cfg = LANGUAGE_CONFIG[body.language]
json={
    "language_id": cfg["judge0_id"],
    "source_code": harness,
    **cfg["judge0_limits"],
},
```

### Component 2: Judge0 port publish

**File:** `docker-compose.yml`

The `judge0-server` service currently does not publish port 2358. Tests run from the host need to reach it. Add:

```yaml
  judge0-server:
    profiles: ["prod", "dev"]
    image: judge0/judge0:1.13.1
    ports:
      - "2358:2358"
    ...
```

**Security note.** Judge0 has `AUTHN_TOKEN` support via the `JUDGE0_AUTHN_TOKEN` env var, already threaded through `backend/app/api/problems.py:310-311`. If the project runs with `JUDGE0_AUTHN_TOKEN` unset (as the default compose env suggests), exposing 2358 on localhost allows any local process to submit code. This is acceptable for a dev workstation — Judge0 is already sandboxed via isolate — but flagged for awareness. If the user wants authn enforced, set `JUDGE0_AUTHN_TOKEN` in `.env` and the tests will inherit it.

### Component 3: Test infrastructure

**New directory:** `backend/tests/integration/`

**Marker registration.** Extend `backend/pytest.ini`:
```ini
[pytest]
markers =
    integration: integration tests that submit via real Judge0 (opt-in; requires make dev)
addopts = -m "not integration"
```

The `addopts` default ensures `pytest backend/tests/` skips the integration directory. Explicit invocation via `pytest -m integration` or pointing pytest at `backend/tests/integration/` overrides.

**`backend/tests/integration/conftest.py`:**

```python
"""Integration tests for the /submit pipeline.

Exercises the full code path: FastAPI endpoint → harness builder →
real Judge0 → result parsing. Requires `make dev` running so that
judge0-server is reachable at localhost:2358.

Adding new test cases: append a ProblemFixture to fixtures.FIXTURES
(for harness matrix) or an entry to catalog_solutions.CATALOG_SOLUTIONS
(for catalog smoke). Each entry auto-fans out across all four languages.
"""
import os
import httpx
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.main import app
from app.database import get_session
from app.api.users import get_current_user
from app.models import User, CodingProblem

# Reuse the TestContainers Postgres session fixture from backend/conftest.py.
# That fixture is already the pattern used by tests/api/.

pytestmark = pytest.mark.integration

JUDGE0_URL = os.getenv("JUDGE0_URL", "http://localhost:2358")


@pytest.fixture(scope="session", autouse=True)
def judge0_available():
    """Skip the whole integration suite if Judge0 isn't reachable."""
    try:
        r = httpx.get(f"{JUDGE0_URL}/about", timeout=2.0)
        r.raise_for_status()
    except Exception as e:
        pytest.skip(
            f"Judge0 not reachable at {JUDGE0_URL} — run `make dev` in another "
            f"terminal, or set JUDGE0_URL. ({e})"
        )


@pytest.fixture
def test_user(session: Session) -> User:
    user = User(username="integration-tester", hashed_password="unused")
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def client(session: Session, test_user: User) -> TestClient:
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_current_user] = lambda: test_user
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def seed_fixture(session: Session):
    """Insert a ProblemFixture into the DB and return the CodingProblem."""
    created: list[int] = []

    def _seed(fixture) -> CodingProblem:
        problem = CodingProblem(
            title=fixture.slug,
            slug=fixture.slug,
            difficulty="easy",
            category="integration-test",
            description=fixture.description,
            starter_code=fixture.starter_code,
            test_cases=fixture.test_cases,
            # ... other required fields with sensible defaults
        )
        session.add(problem)
        session.commit()
        session.refresh(problem)
        created.append(problem.id)
        return problem

    yield _seed

    # Cleanup — tests run against TestContainers, teardown is implicit,
    # but we clear between tests for safety.
    for pid in created:
        obj = session.get(CodingProblem, pid)
        if obj:
            session.delete(obj)
    session.commit()
```

**`backend/tests/integration/fixtures.py`:**

```python
from dataclasses import dataclass


@dataclass
class ProblemFixture:
    slug: str                        # unique id, e.g. "add-two-ints"
    description: str                 # one-liner for test IDs and errors
    starter_code: dict[str, str]     # {lang: starter source} — drives func_name + param_types
    test_cases: list[dict]           # [{"input": {...}, "output": ...}, ...]
    solutions: dict[str, str]        # {lang: known-good solution source}
    expected_status: str = "accepted"


FIXTURES: list[ProblemFixture] = [
    ProblemFixture(
        slug="add-two-ints",
        description="primitives in / primitive out",
        starter_code={
            "python":     "def add(a: int, b: int) -> int:\n    pass",
            "javascript": "function add(a, b) {}",
            "go":         "func add(a int, b int) int { return 0 }",
            "java":       "class Solution { public int add(int a, int b) { return 0; } }",
        },
        test_cases=[
            {"input": {"a": 1,    "b": 2},    "output": 3},
            {"input": {"a": -5,   "b": 5},    "output": 0},
            {"input": {"a": 1000, "b": 2000}, "output": 3000},
        ],
        solutions={
            "python":     "def add(a, b): return a + b",
            "javascript": "function add(a, b) { return a + b; }",
            "go":         "func add(a int, b int) int { return a + b }",
            "java":       "public int add(int a, int b) { return a + b; }",
        },
    ),
    # Additional fixtures: reverse_array (arrays), is_palindrome (strings),
    # linked_list_length (ListNode), max_depth (TreeNode), node_count (Graph).
    # Full source omitted from spec — one entry per param-type shape, same schema.
]
```

**`backend/tests/integration/test_harness_matrix.py`:**

```python
import pytest
from .fixtures import FIXTURES

LANGUAGES = ["python", "javascript", "go", "java"]


@pytest.mark.parametrize("language", LANGUAGES)
@pytest.mark.parametrize("fixture", FIXTURES, ids=lambda f: f.slug)
def test_fixture_accepted(client, seed_fixture, fixture, language):
    problem = seed_fixture(fixture)
    resp = client.post(
        f"/api/problems/{problem.id}/submit",
        json={"language": language, "code": fixture.solutions[language]},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == fixture.expected_status, (
        f"{fixture.slug} [{language}] → {body['status']}\n"
        f"stderr: {body.get('stderr') or ''}\n"
        f"compile_output: {body.get('compile_output') or ''}"
    )
```

The assertion message is the key debug affordance: on any failure, the Judge0 `stderr` and `compile_output` are printed directly, so the Java heap error, Go pthread abort, or compilation error is visible without rerunning with extra logging.

### Component 4: Catalog smoke tests

**`backend/tests/integration/catalog_solutions.py`:**

```python
# {slug: {language: known-good solution source}}
CATALOG_SOLUTIONS: dict[str, dict[str, str]] = {
    "two-sum": {
        "python":     "...",
        "javascript": "...",
        "go":         "...",
        "java":       "...",
    },
    "maximum-depth-of-binary-tree": {
        "python":     "...",
        "javascript": "...",
        "go":         "...",
        "java":       "...",
    },
}
```

**`backend/tests/integration/test_catalog_smoke.py`:**

Loads real `CodingProblem` rows from the `dsa-flash-cards/` submodule via the YAML loader (session-scoped, called once), looks up each slug, and submits its canonical solution in each language.

```python
import pytest
from sqlmodel import select
from app.models import CodingProblem
from app.loader import load_yaml_flashcards  # or the problem-loading equivalent
from .catalog_solutions import CATALOG_SOLUTIONS

LANGUAGES = ["python", "javascript", "go", "java"]


@pytest.fixture(scope="module", autouse=True)
def load_catalog(session):
    load_yaml_flashcards(session)  # or the coding-problem loader


@pytest.mark.parametrize("language", LANGUAGES)
@pytest.mark.parametrize("slug", list(CATALOG_SOLUTIONS.keys()))
def test_catalog_smoke(client, session, slug, language):
    problem = session.exec(
        select(CodingProblem).where(CodingProblem.slug == slug)
    ).first()
    assert problem is not None, (
        f"Catalog slug '{slug}' missing — either the catalog drifted or "
        f"this smoke test needs updating."
    )
    resp = client.post(
        f"/api/problems/{problem.id}/submit",
        json={"language": language, "code": CATALOG_SOLUTIONS[slug][language]},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "accepted", (
        f"{slug} [{language}] → {body['status']}\n"
        f"stderr: {body.get('stderr') or ''}\n"
        f"compile_output: {body.get('compile_output') or ''}"
    )
```

**Why only two smoke slugs?** The harness-matrix fixture suite already covers every param-type shape. Catalog smoke answers one additional question: "is the real YAML pipeline + loader + real problem records wired up correctly?" Two slugs is enough to answer that. More is redundant coverage. If a specific catalog problem breaks, promote it to its own smoke entry.

### Component 5: Execution

**New Makefile target:**
```makefile
test-integration:
	cd backend && pytest tests/integration/ -m integration -v
```

**Running:**

| Command | What happens |
|---|---|
| `pytest backend/tests/` | Default dev loop. `addopts = -m "not integration"` skips the integration directory. ~10 s, offline. |
| `make dev` (one terminal) + `make test-integration` (another) | Full integration run from the host. Judge0 reachable at `localhost:2358` thanks to the new port publish. ~60-90 s. |
| `JUDGE0_URL=http://other-host:2358 make test-integration` | Escape hatch for remote Judge0. |

**Default behavior guarantee:** `pytest backend/tests/` must continue to run in ~10 s with no Judge0 dependency. The `integration` marker + `addopts` is the opt-in gate.

## Data Flow (single test, happy path)

1. Pytest collector runs with default `-m "not integration"` and skips `tests/integration/` entirely. On explicit `pytest tests/integration/`, the directory is collected.
2. Session-scoped `judge0_available` fixture pings `GET {JUDGE0_URL}/about`. If unreachable, the whole suite skips with a clear message pointing at `make dev`.
3. For each parametrized test:
   - `seed_fixture` inserts the fixture's `CodingProblem` into the TestContainers Postgres (or `load_catalog` has seeded real rows).
   - `client.post("/api/problems/{id}/submit", ...)` hits the real FastAPI endpoint.
   - The endpoint calls `build_harness(...)`, then POSTs to Judge0 at `JUDGE0_URL` with the per-language `judge0_limits`.
   - Judge0 returns synchronously (`wait=true`).
   - The endpoint parses Judge0's result and returns the `SubmissionOut` shape.
4. Test assertions:
   - `resp.status_code == 200` (catches endpoint bugs)
   - `body["status"] == expected_status` (catches resource starvation, compile errors, wrong results)
5. On failure, the assertion message includes language, fixture slug, Judge0 status, `stderr`, and `compile_output`.

## Error Handling

Three distinct failure modes the tests are designed to surface cleanly:

| Failure shape | Means | Action |
|---|---|---|
| `body["status"] != "accepted"` with Java heap / Go pthread / TLE signature | Config is still wrong for this language | Adjust that language's `judge0_limits`, re-run |
| `body["status"] == "accepted"` but `passed` flags are false | Harness generated bad code or type conversion is broken | Read `expected` vs `actual` in the per-case result to diagnose |
| `body["status"] == "compile_error"` | Harness generator produced bad source | `compile_output` in the assertion names the line |
| `pytest.skip` from `judge0_available` fixture | Judge0 not running | Run `make dev` in another terminal |

**No retries.** Judge0 under isolate is deterministic; flakes here are signal, not noise. If a test is flaky, that is a real bug and should be investigated, not papered over.

## Success Criteria

1. `make dev` + `make test-integration` prints **32 passed** (24 harness-matrix + 8 catalog smoke) on the current dev stack.
2. Reverting `LANGUAGE_CONFIG["java"]["judge0_limits"]["memory_limit"]` back to `128000` causes every Java fixture test to fail with an assertion whose message contains "Could not reserve enough space". (Regression-guard property.)
3. `pytest backend/tests/` without the marker still completes in the current ~10 s window. All previously passing tests still pass.
4. Adding a seventh `ProblemFixture` to `FIXTURES` is a single append; no other code changes required, and the four new parametrized cases appear automatically.
5. A Phase 2 entry is added to `TODOS.md` (wider param-type matrix, error paths, CI workflow).

## Risks and Open Questions

1. **`max_processes_and_or_threads` may not be respected at the submission level.** Some Judge0 deployments require raising this at the service level (isolate's `-p` flag, or the Judge0 Rails app's own config). If the Go smoke test still fails with `pthread_create` after the config change, we need to touch Judge0's service config. Mitigation: if Go still fails, inspect `judge0-server` container logs and `docker exec` into it to check `isolate --version` and config.

2. **Port 2358 exposure on localhost.** Publishing Judge0 adds a local attack surface if `JUDGE0_AUTHN_TOKEN` is unset. For a dev workstation this is acceptable — Judge0's isolate sandbox is the real containment boundary — but worth noting. If the project wants authn enforced, set the token in `.env` and tests will inherit it via the existing header plumbing.

3. **TestContainers + real Judge0 mixes two worlds.** The test DB is ephemeral (TestContainers), but Judge0 is shared with the dev stack. This is fine because Judge0 is stateless per submission — no cross-contamination between test runs or between tests and the live dev environment.

4. **Raising resource limits expands the sandbox attack surface.** 512 MB for Java and 256 MB for JS/Go is more than 128 MB for Python, giving malicious code more room to operate. Mitigations already in place: Judge0's isolate sandbox, CPU time limit, no network, short-lived container. Not in scope to tighten further in this work, but worth noting that the budget increase trades security headroom for language viability.

5. **Judge0 `wait=true` may not guarantee immediate stdout.** If we observe empty `stdout` on submissions that Judge0 reports as Accepted, we may need to fall back to polling `GET /submissions/{token}` with retries. Not expected from the existing production submit code path which uses the same `wait=true` pattern, but flagged as a possibility.

6. **CI does not currently run the integration layer.** Until the Phase 2 CI workflow exists, these tests only run locally. A broken harness config could merge to main if no one runs `make test-integration` before pushing. Accepted risk for Phase 1; prioritize the CI follow-up accordingly.

7. **`load_yaml_flashcards` may not be the right loader for coding problems.** The current loader name suggests flashcards, and the catalog smoke path needs the real coding-problem loader. Verify during implementation and use the correct entry point; if a separate problem loader exists, use it.

## Phase 2 Follow-ups (for TODOS.md)

- Additional `ProblemFixture` entries: nested types, 2D arrays, map/dict return types
- Error path fixtures: function name missing, runtime exception in user code, wrong return type, malformed source × 4 languages
- CI workflow: GitHub Actions job that brings up the dev stack and runs `pytest -m integration` on PRs touching `backend/app/harnesses/` or `backend/app/api/problems.py`
- Watchdog: if any Phase 1 test takes > 15 s wall clock, flag as potential Judge0 regression

## Plan Handoff

After this spec is approved, implementation is handed to `superpowers:writing-plans` to produce a step-by-step implementation plan covering:
- `LANGUAGE_CONFIG` extension and `problems.py` submit endpoint change
- `docker-compose.yml` port publish for `judge0-server`
- New `backend/tests/integration/` directory with conftest, fixtures, catalog solutions, and two test files
- `backend/pytest.ini` marker + `addopts` change
- Makefile `test-integration` target
- Phase 1 fixture set (primitives, arrays, strings, ListNode, TreeNode, Graph) × 4 languages
- Two catalog smoke slugs × 4 languages
- TODOS.md Phase 2 entry
- Local verification via `make dev` + `make test-integration`
