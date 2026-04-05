# Harness Judge0 Config + Integration Tests — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix per-language Judge0 resource limits so JavaScript, Go, and Java submissions succeed, and add an opt-in integration test suite that exercises the real `/problems/{id}/submit` → harness → Judge0 pipeline as a regression guard.

**Architecture:** Per-language `judge0_limits` dict inside `LANGUAGE_CONFIG`, splatted into the Judge0 submission payload. New `backend/tests/integration/` directory with a declarative `ProblemFixture` dataclass registry that auto-fans out across all four languages via pytest parametrization. Tests use FastAPI `TestClient` against a minimal in-process app + TestContainers Postgres (same pattern as `tests/api/`) and hit a host-reachable Judge0 via a new `ports: ["2358:2358"]` publish on `judge0-server`. Marker `integration` is excluded from default pytest runs.

**Tech Stack:** FastAPI, SQLModel, Pytest, TestContainers (Postgres), httpx, Judge0, Docker Compose.

**Spec:** `docs/superpowers/specs/2026-04-05-harness-judge0-config-and-e2e-tests-design.md`

---

## Pre-flight

- [ ] **Step 0.1: Confirm `make dev` is running** so Judge0 is up. The integration tests will be run against this stack.

  Run: `docker compose ps judge0-server`
  Expected: `judge0-server` row with `State: running`. If not, start it in another terminal:
  ```
  make dev
  ```

- [ ] **Step 0.2: Sanity-check existing backend test infrastructure still passes** before we change anything.

  Run: `cd backend && .venv/bin/python -m pytest tests/ -q`
  Expected: all tests pass (currently ~84+ tests). If this baseline fails, **stop** — something is already broken and this plan's changes will be impossible to validate.

---

## Task 1: Publish Judge0 port to the host

**Why:** `TestClient` runs the FastAPI app in-process on the host, so when `submit_code` internally calls `httpx.post(f"{JUDGE0_URL}/submissions", ...)`, the call originates from the host. The host can't resolve `judge0-server` (a docker DNS name) unless we publish the port.

**Files:**
- Modify: `docker-compose.yml` (the `judge0-server` service block, ~line 145)

- [ ] **Step 1.1: Add `ports` to `judge0-server`**

  Open `docker-compose.yml` and locate the `judge0-server:` service (around line 145). Add a `ports` key so the service looks like:

  ```yaml
    judge0-server:
      profiles: ["prod", "dev"]
      image: judge0/judge0:1.13.1
      ports:
        - "2358:2358"
      depends_on:
        judge0-db:
          condition: service_healthy
        judge0-redis:
          condition: service_started
      environment:
        <<: *judge0-env
      restart: unless-stopped
      privileged: true
      volumes:
        - /sys/fs/cgroup:/sys/fs/cgroup:rw
  ```

- [ ] **Step 1.2: Restart the dev stack to pick up the port publish**

  Run:
  ```
  make down && make dev
  ```
  (Run `make dev` in a separate terminal since it's foreground.)

- [ ] **Step 1.3: Verify Judge0 is reachable from the host**

  Run:
  ```
  curl -sf http://localhost:2358/about | head -c 200
  ```
  Expected: a JSON blob starting with `{"version":...}`. If `curl` returns "connection refused", the port publish didn't take — re-run `make down && make dev`.

- [ ] **Step 1.4: Commit**

  ```
  git add docker-compose.yml
  git commit -m "chore(judge0): publish port 2358 to host for integration tests"
  ```

---

## Task 2: Register `integration` pytest marker and exclude by default

**Why:** The default `pytest backend/tests/` run must stay fast and offline. We add the marker and an `addopts` default so integration tests only run when explicitly invoked.

**Files:**
- Modify: `backend/pytest.ini`

- [ ] **Step 2.1: Replace `backend/pytest.ini` contents**

  The current file is:
  ```ini
  # pytest.ini
  [pytest]
  # make sure the project root (.) is on PYTHONPATH
  python_paths = .
  ```

  Replace it with:
  ```ini
  # pytest.ini
  [pytest]
  # make sure the project root (.) is on PYTHONPATH
  python_paths = .
  markers =
      integration: integration tests that hit a real Judge0 at JUDGE0_URL (opt-in; requires `make dev`)
  addopts = -m "not integration"
  ```

- [ ] **Step 2.2: Verify the marker is registered and the default run still works**

  Run: `cd backend && .venv/bin/python -m pytest tests/ -q`
  Expected: same ~84+ tests pass, no "unknown marker" warnings. If you see `PytestUnknownMarkWarning`, the `markers =` line isn't being read — check indentation under `[pytest]`.

- [ ] **Step 2.3: Commit**

  ```
  git add backend/pytest.ini
  git commit -m "test: register integration marker and exclude from default run"
  ```

---

## Task 3: Add `test-integration` Makefile target

**Files:**
- Modify: `Makefile`

- [ ] **Step 3.1: Add target and update `.PHONY`**

  At the top of `Makefile`, change:
  ```makefile
  .PHONY: dev prod down logs validate-problems
  ```
  to:
  ```makefile
  .PHONY: dev prod down logs validate-problems test-integration
  ```

  Append to the bottom of `Makefile`:
  ```makefile

  # Run the integration test suite. Requires `make dev` running in another
  # terminal so judge0-server is reachable at localhost:2358. Tests use a
  # TestContainers Postgres so they do not touch the dev database.
  test-integration:
  	@if [ ! -x backend/.venv/bin/python ]; then \
  		echo "error: backend/.venv not found. Create it with:"; \
  		echo "  cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt -r requirements-test.txt"; \
  		exit 1; \
  	fi
  	cd backend && .venv/bin/python -m pytest tests/integration/ -m integration -v
  ```

  Note: the leading whitespace on recipe lines MUST be a tab, not spaces — Make is strict about this. After pasting, verify with `cat -A Makefile | tail -15` (look for `^I` at the start of recipe lines).

- [ ] **Step 3.2: Verify the target exists (does not run yet — tests don't exist)**

  Run: `make -n test-integration`
  Expected: prints the `cd backend && .venv/bin/python -m pytest ...` command. No error.

- [ ] **Step 3.3: Commit**

  ```
  git add Makefile
  git commit -m "test: add test-integration Makefile target"
  ```

---

## Task 4: Create integration conftest with Judge0 reachability check and TestClient fixtures

**Why:** We need module-local `app`, `client`, and `judge0_available` fixtures. The pattern mirrors `backend/tests/api/test_problems.py:17-37` (minimal FastAPI app with only the `problems_router` and `users_router`, `get_current_user` dependency override). The `judge0_available` fixture gracefully skips the suite if `make dev` isn't running.

**Files:**
- Create: `backend/tests/integration/__init__.py` (empty)
- Create: `backend/tests/integration/conftest.py`

- [ ] **Step 4.1: Create `backend/tests/integration/__init__.py`**

  Create an empty file:
  ```
  touch backend/tests/integration/__init__.py
  ```

- [ ] **Step 4.2: Create `backend/tests/integration/conftest.py`**

  Write the following exact content to `backend/tests/integration/conftest.py`:

  ```python
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
              f"Judge0 not reachable at {JUDGE0_URL} — run `make dev` in "
              f"another terminal, or set JUDGE0_URL. ({e})"
          )


  @pytest.fixture(name="app")
  def app_fixture(session, create_user):
      """Minimal FastAPI app with just the routers we need, auth overridden."""
      user = create_user(username="integration-tester", password="password123")

      class FakeUser:
          id = user.id

      fake_user = FakeUser()

      app = FastAPI()
      app.include_router(problems_router)
      app.include_router(users_router)
      app.dependency_overrides[get_session] = get_test_session(session)
      app.dependency_overrides[get_current_user] = lambda: fake_user
      app.dependency_overrides[get_optional_user] = lambda: fake_user
      return app


  @pytest.fixture(name="client")
  def client_fixture(app):
      return TestClient(app)
  ```

  **Notes on this file:**
  - `session`, `create_user`, and the autouse `clear_db` + `reset_rate_limiter` fixtures are inherited from `backend/tests/conftest.py` automatically.
  - `pytestmark = pytest.mark.integration` marks every test in this directory with the `integration` marker — no need to decorate individual tests.
  - The `judge0_available` fixture is `autouse=True` and session-scoped, so if Judge0 is down the whole suite short-circuits with one clear message.
  - `get_test_session` is imported from the top-level test conftest; same pattern as `tests/api/test_problems.py:14`.

- [ ] **Step 4.3: Verify pytest can collect an empty suite without errors**

  Run: `cd backend && .venv/bin/python -m pytest tests/integration/ -m integration --collect-only`
  Expected: `collected 0 items`, no import errors. If you see `ModuleNotFoundError: No module named 'tests.conftest'`, the path insertion in `backend/conftest.py` isn't reaching this subdirectory — verify `backend/conftest.py` still contains the `sys.path.insert` line.

- [ ] **Step 4.4: Commit**

  ```
  git add backend/tests/integration/__init__.py backend/tests/integration/conftest.py
  git commit -m "test: add integration conftest with Judge0 reachability check"
  ```

---

## Task 5: Create `ProblemFixture` dataclass and first fixture (`add-two-ints`)

**Why:** We add the declarative registry and the simplest possible fixture (primitive ints) so the first `test_harness_matrix.py` run surfaces the Python-passes / JS-Go-Java-fails baseline before we touch the config.

**Files:**
- Create: `backend/tests/integration/fixtures.py`

- [ ] **Step 5.1: Write `backend/tests/integration/fixtures.py`**

  ```python
  """Declarative registry of test fixtures for the integration harness matrix.

  Adding a new case: append a ProblemFixture to FIXTURES. Each entry
  auto-fans out across all four languages via the parametrized test in
  test_harness_matrix.py. Solution sources must be known-good — the test
  asserts status == "Accepted" and all test cases pass.
  """
  from dataclasses import dataclass


  @dataclass
  class ProblemFixture:
      slug: str                        # unique id, used for test IDs (not DB)
      description: str                 # one-liner for assertion messages
      starter_code: dict[str, str]     # {lang: starter source} — drives func_name + param_types
      test_cases: list[dict]           # [{"input": {...}, "expected": ...}, ...]
      solutions: dict[str, str]        # {lang: known-good solution source}


  # ---------- Fixture: primitives (int, int) -> int ----------

  ADD_TWO_INTS = ProblemFixture(
      slug="add-two-ints",
      description="primitives in, primitive out",
      starter_code={
          "python": (
              "def add(a: int, b: int) -> int:\n"
              "    pass\n"
          ),
          "javascript": (
              "function add(a, b) {\n"
              "}\n"
          ),
          "go": (
              "func add(a int, b int) int {\n"
              "    return 0\n"
              "}\n"
          ),
          "java": (
              "public int add(int a, int b) {\n"
              "    return 0;\n"
              "}\n"
          ),
      },
      test_cases=[
          {"input": {"a": 1, "b": 2}, "expected": 3},
          {"input": {"a": -5, "b": 5}, "expected": 0},
          {"input": {"a": 1000, "b": 2000}, "expected": 3000},
      ],
      solutions={
          "python": (
              "def add(a, b):\n"
              "    return a + b\n"
          ),
          "javascript": (
              "function add(a, b) {\n"
              "    return a + b;\n"
              "}\n"
          ),
          "go": (
              "func add(a int, b int) int {\n"
              "    return a + b\n"
              "}\n"
          ),
          "java": (
              "public int add(int a, int b) {\n"
              "    return a + b;\n"
              "}\n"
          ),
      },
  )


  FIXTURES: list[ProblemFixture] = [
      ADD_TWO_INTS,
  ]
  ```

- [ ] **Step 5.2: Verify import works**

  Run: `cd backend && .venv/bin/python -c "from tests.integration.fixtures import FIXTURES; print(len(FIXTURES))"`
  Expected: `1`

- [ ] **Step 5.3: Commit**

  ```
  git add backend/tests/integration/fixtures.py
  git commit -m "test: add ProblemFixture dataclass and add-two-ints fixture"
  ```

---

## Task 6: Write the parametrized harness-matrix test

**Why:** This is where TDD kicks in. We write the test first, run it, and expect Python to pass and JS/Go/Java to fail with config-related errors. The failures validate the spec's problem statement.

**Files:**
- Create: `backend/tests/integration/test_harness_matrix.py`

- [ ] **Step 6.1: Write `backend/tests/integration/test_harness_matrix.py`**

  ```python
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

      # The `status` field is the Judge0 status description
      # (e.g. "Accepted", "Time Limit Exceeded", "Compilation Error").
      assert body["status"] == "Accepted", (
          f"{fixture.slug} [{language}] -> status={body['status']!r}\n"
          f"stderr: {body.get('stderr') or ''}\n"
          f"stdout: {body.get('stdout') or ''}"
      )

      # All test cases must pass (top-level `passed` is the aggregate).
      assert body["passed"] is True, (
          f"{fixture.slug} [{language}] -> not all test cases passed\n"
          f"test_results: {body.get('test_results')}"
      )
  ```

- [ ] **Step 6.2: Run the new tests to see the baseline failure mode**

  Run: `cd backend && .venv/bin/python -m pytest tests/integration/test_harness_matrix.py -m integration -v`

  Expected (BEFORE the config fix in Task 7):
  - `test_fixture_accepted[add-two-ints-python]` — **PASS**
  - `test_fixture_accepted[add-two-ints-javascript]` — **FAIL** with "Time Limit Exceeded" OR the Java-style heap error depending on the isolate config
  - `test_fixture_accepted[add-two-ints-go]` — **FAIL** with `pthread_create` stderr
  - `test_fixture_accepted[add-two-ints-java]` — **FAIL** with `Could not reserve enough space for 256000KB object heap`

  **This is the validation of the spec's problem statement.** Capture the failure output — it should match the error signatures in the spec's Problem Statement section. If the failures look *different* from the spec (e.g. Java passes unexpectedly), pause and reconcile: the spec may be stale, or the dev stack's Judge0 version may differ.

  **Do not commit yet.** The test file will be committed together with the config fix in Task 7 (so the repository never has a state where the new test is present but failing).

---

## Task 7: Per-language `LANGUAGE_CONFIG` with `judge0_limits` + submit endpoint change

**Files:**
- Modify: `backend/app/api/problems.py` (lines 37-43 and 317-324)

- [ ] **Step 7.1: Replace `LANGUAGE_CONFIG` (around line 37)**

  Find this block:
  ```python
  LANGUAGE_CONFIG = {
      "python": {"judge0_id": 71, "monaco_mode": "python"},
      "javascript": {"judge0_id": 63, "monaco_mode": "javascript"},
      "go": {"judge0_id": 60, "monaco_mode": "go"},
      "java": {"judge0_id": 62, "monaco_mode": "java"},
  }
  ```

  Replace with:
  ```python
  LANGUAGE_CONFIG = {
      "python": {
          "judge0_id": 71,
          "monaco_mode": "python",
          "judge0_limits": {
              "cpu_time_limit": 5,
              "memory_limit": 128000,  # 128 MB — comfortable for CPython
              "enable_per_process_and_thread_time_limit": True,
              "enable_per_process_and_thread_memory_limit": True,
          },
      },
      "javascript": {
          "judge0_id": 63,
          "monaco_mode": "javascript",
          "judge0_limits": {
              "cpu_time_limit": 10,  # Node + V8 JIT warmup
              "memory_limit": 256000,  # 256 MB for V8 heap
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
              "memory_limit": 512000,  # JVM default heap + overhead
              "max_processes_and_or_threads": 60,  # JVM is multi-threaded
              "enable_per_process_and_thread_time_limit": False,
              "enable_per_process_and_thread_memory_limit": False,
          },
      },
  }
  ```

- [ ] **Step 7.2: Update the submit payload (around line 317)**

  Find this block in `submit_code`:
  ```python
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
  ```

  Replace with:
  ```python
          cfg = LANGUAGE_CONFIG[body.language]
          with httpx.Client(timeout=30.0) as http:
              resp = http.post(
                  f"{JUDGE0_URL}/submissions",
                  params={"base64_encoded": "false", "wait": "true"},
                  headers=headers,
                  json={
                      "language_id": cfg["judge0_id"],
                      "source_code": harness,
                      **cfg["judge0_limits"],
                  },
              )
  ```

- [ ] **Step 7.3: Re-run the existing mocked tests to confirm no regressions**

  Run: `cd backend && .venv/bin/python -m pytest tests/api/test_problems.py -q`
  Expected: all previously-passing tests still pass. The mocked tests don't inspect the Judge0 payload fields we changed, so they should be unaffected. If any fail, read the failure — it's likely asserting on the shape of the httpx mock call and needs updating.

- [ ] **Step 7.4: Re-run the integration matrix test**

  Run: `cd backend && .venv/bin/python -m pytest tests/integration/test_harness_matrix.py -m integration -v`
  Expected: **4 passed** (add-two-ints × 4 languages).

  If Java still fails with "Could not reserve enough space", the 512 MB limit may still be too low for this specific JVM image — try bumping to `768000` and re-run. Document any such adjustment in the commit message.

  If Go still fails with `pthread_create`, `max_processes_and_or_threads` may not be honored by the local Judge0 build. Spec Risk #1 flags this: inspect `docker logs judge0-server` and consult isolate's `--help` for the process-count flag. Escalate rather than papering over.

- [ ] **Step 7.5: Commit test file + config fix together**

  ```
  git add backend/app/api/problems.py backend/tests/integration/test_harness_matrix.py
  git commit -m "fix(submit): per-language Judge0 resource limits + harness matrix test

  Uniform resource budget sized for CPython was starving JVM, Go runtime,
  and V8 at startup. Move limits into LANGUAGE_CONFIG per language and
  splat into the submission payload.

  Add the first integration test (add-two-ints x 4 languages) that would
  have caught this regression."
  ```

---

## Task 8: Add array fixture (`reverse-array`)

**Files:**
- Modify: `backend/tests/integration/fixtures.py`

- [ ] **Step 8.1: Append `REVERSE_ARRAY` fixture**

  Before the `FIXTURES = [...]` line, insert:

  ```python
  # ---------- Fixture: list[int] -> list[int] ----------

  REVERSE_ARRAY = ProblemFixture(
      slug="reverse-array",
      description="list of ints in, list of ints out",
      starter_code={
          "python": (
              "def reverse_list(nums: list[int]) -> list[int]:\n"
              "    pass\n"
          ),
          "javascript": (
              "function reverse_list(nums) {\n"
              "}\n"
          ),
          "go": (
              "func reverse_list(nums []int) []int {\n"
              "    return nil\n"
              "}\n"
          ),
          "java": (
              "public int[] reverse_list(int[] nums) {\n"
              "    return new int[0];\n"
              "}\n"
          ),
      },
      test_cases=[
          {"input": {"nums": [1, 2, 3, 4, 5]}, "expected": [5, 4, 3, 2, 1]},
          {"input": {"nums": []}, "expected": []},
          {"input": {"nums": [42]}, "expected": [42]},
      ],
      solutions={
          "python": (
              "def reverse_list(nums):\n"
              "    return list(reversed(nums))\n"
          ),
          "javascript": (
              "function reverse_list(nums) {\n"
              "    return nums.slice().reverse();\n"
              "}\n"
          ),
          "go": (
              "func reverse_list(nums []int) []int {\n"
              "    out := make([]int, len(nums))\n"
              "    for i, v := range nums {\n"
              "        out[len(nums)-1-i] = v\n"
              "    }\n"
              "    return out\n"
              "}\n"
          ),
          "java": (
              "public int[] reverse_list(int[] nums) {\n"
              "    int[] out = new int[nums.length];\n"
              "    for (int i = 0; i < nums.length; i++) {\n"
              "        out[nums.length - 1 - i] = nums[i];\n"
              "    }\n"
              "    return out;\n"
              "}\n"
          ),
      },
  )
  ```

  Then update `FIXTURES`:
  ```python
  FIXTURES: list[ProblemFixture] = [
      ADD_TWO_INTS,
      REVERSE_ARRAY,
  ]
  ```

- [ ] **Step 8.2: Run the matrix for this fixture**

  Run: `cd backend && .venv/bin/python -m pytest tests/integration/test_harness_matrix.py -m integration -v -k reverse-array`
  Expected: **4 passed**.

  If a specific language fails with a compile error or `passed=false`, the solution source or function-name style for that language is wrong for the harness builder — read `compile_output` or `test_results` to diagnose. Common causes:
  - Python function name must match the Python starter's function name (harness uses Python's signature to derive `func_name`).
  - Go function names must be snake_case to match Python's (the harness renames based on the Python def).
  - Java `class Solution` wrapping is automatic per `backend/app/harnesses/java.py:417-422` — do not wrap the user's method in `class Solution { ... }` yourself.

- [ ] **Step 8.3: Commit**

  ```
  git add backend/tests/integration/fixtures.py
  git commit -m "test(integration): add reverse-array fixture"
  ```

---

## Task 9: Add string fixture (`is-palindrome`)

**Files:**
- Modify: `backend/tests/integration/fixtures.py`

- [ ] **Step 9.1: Append `IS_PALINDROME` fixture**

  Before the `FIXTURES = [...]` line, insert:

  ```python
  # ---------- Fixture: str -> bool ----------

  IS_PALINDROME = ProblemFixture(
      slug="is-palindrome",
      description="string in, bool out",
      starter_code={
          "python": (
              "def is_palindrome(s: str) -> bool:\n"
              "    pass\n"
          ),
          "javascript": (
              "function is_palindrome(s) {\n"
              "}\n"
          ),
          "go": (
              "func is_palindrome(s string) bool {\n"
              "    return false\n"
              "}\n"
          ),
          "java": (
              "public boolean is_palindrome(String s) {\n"
              "    return false;\n"
              "}\n"
          ),
      },
      test_cases=[
          {"input": {"s": "racecar"}, "expected": True},
          {"input": {"s": "hello"}, "expected": False},
          {"input": {"s": ""}, "expected": True},
          {"input": {"s": "a"}, "expected": True},
      ],
      solutions={
          "python": (
              "def is_palindrome(s):\n"
              "    return s == s[::-1]\n"
          ),
          "javascript": (
              "function is_palindrome(s) {\n"
              "    return s === s.split('').reverse().join('');\n"
              "}\n"
          ),
          "go": (
              "func is_palindrome(s string) bool {\n"
              "    n := len(s)\n"
              "    for i := 0; i < n/2; i++ {\n"
              "        if s[i] != s[n-1-i] {\n"
              "            return false\n"
              "        }\n"
              "    }\n"
              "    return true\n"
              "}\n"
          ),
          "java": (
              "public boolean is_palindrome(String s) {\n"
              "    int n = s.length();\n"
              "    for (int i = 0; i < n / 2; i++) {\n"
              "        if (s.charAt(i) != s.charAt(n - 1 - i)) return false;\n"
              "    }\n"
              "    return true;\n"
              "}\n"
          ),
      },
  )
  ```

  Update `FIXTURES`:
  ```python
  FIXTURES: list[ProblemFixture] = [
      ADD_TWO_INTS,
      REVERSE_ARRAY,
      IS_PALINDROME,
  ]
  ```

- [ ] **Step 9.2: Run the matrix for this fixture**

  Run: `cd backend && .venv/bin/python -m pytest tests/integration/test_harness_matrix.py -m integration -v -k is-palindrome`
  Expected: **4 passed**.

- [ ] **Step 9.3: Commit**

  ```
  git add backend/tests/integration/fixtures.py
  git commit -m "test(integration): add is-palindrome fixture"
  ```

---

## Task 10: Add ListNode fixture (`reverse-linked-list`)

**Why:** First custom-type fixture. Validates `param_types` parsing for `Optional[ListNode]` returns, and that the harness injects the ListNode class, converts `[1,2,3]` test input into a linked list at runtime, and serializes the returned ListNode back to an array.

**Starter code must match the catalog pattern** — Python starter includes `from typing import Optional` and the `class ListNode` definition, which `parse_python_param_types` uses to extract `{"head": "ListNode", "__return__": "ListNode"}`.

**Files:**
- Modify: `backend/tests/integration/fixtures.py`

- [ ] **Step 10.1: Append `REVERSE_LINKED_LIST` fixture**

  Before the `FIXTURES = [...]` line, insert:

  ```python
  # ---------- Fixture: ListNode -> ListNode ----------

  REVERSE_LINKED_LIST = ProblemFixture(
      slug="reverse-linked-list",
      description="ListNode in, ListNode out",
      starter_code={
          "python": (
              "from typing import Optional\n"
              "\n"
              "class ListNode:\n"
              "    def __init__(self, val=0, next=None):\n"
              "        self.val = val\n"
              "        self.next = next\n"
              "\n"
              "def reverse_list(head: Optional[ListNode]) -> Optional[ListNode]:\n"
              "    pass\n"
          ),
          "javascript": (
              "class ListNode {\n"
              "    constructor(val = 0, next = null) {\n"
              "        this.val = val;\n"
              "        this.next = next;\n"
              "    }\n"
              "}\n"
              "\n"
              "function reverse_list(head) {\n"
              "}\n"
          ),
          "go": (
              "type ListNode struct {\n"
              "    Val  int\n"
              "    Next *ListNode\n"
              "}\n"
              "\n"
              "func reverse_list(head *ListNode) *ListNode {\n"
              "    return nil\n"
              "}\n"
          ),
          "java": (
              "public ListNode reverse_list(ListNode head) {\n"
              "    return null;\n"
              "}\n"
          ),
      },
      test_cases=[
          {"input": {"head": [1, 2, 3, 4, 5]}, "expected": [5, 4, 3, 2, 1]},
          {"input": {"head": [1, 2]}, "expected": [2, 1]},
          {"input": {"head": []}, "expected": []},
          {"input": {"head": [42]}, "expected": [42]},
      ],
      solutions={
          "python": (
              "def reverse_list(head):\n"
              "    prev = None\n"
              "    while head:\n"
              "        nxt = head.next\n"
              "        head.next = prev\n"
              "        prev = head\n"
              "        head = nxt\n"
              "    return prev\n"
          ),
          "javascript": (
              "function reverse_list(head) {\n"
              "    let prev = null;\n"
              "    while (head) {\n"
              "        const nxt = head.next;\n"
              "        head.next = prev;\n"
              "        prev = head;\n"
              "        head = nxt;\n"
              "    }\n"
              "    return prev;\n"
              "}\n"
          ),
          "go": (
              "func reverse_list(head *ListNode) *ListNode {\n"
              "    var prev *ListNode\n"
              "    for head != nil {\n"
              "        next := head.Next\n"
              "        head.Next = prev\n"
              "        prev = head\n"
              "        head = next\n"
              "    }\n"
              "    return prev\n"
              "}\n"
          ),
          "java": (
              "public ListNode reverse_list(ListNode head) {\n"
              "    ListNode prev = null;\n"
              "    while (head != null) {\n"
              "        ListNode next = head.next;\n"
              "        head.next = prev;\n"
              "        prev = head;\n"
              "        head = next;\n"
              "    }\n"
              "    return prev;\n"
              "}\n"
          ),
      },
  )
  ```

  Update `FIXTURES`:
  ```python
  FIXTURES: list[ProblemFixture] = [
      ADD_TWO_INTS,
      REVERSE_ARRAY,
      IS_PALINDROME,
      REVERSE_LINKED_LIST,
  ]
  ```

- [ ] **Step 10.2: Run the matrix for this fixture**

  Run: `cd backend && .venv/bin/python -m pytest tests/integration/test_harness_matrix.py -m integration -v -k reverse-linked-list`
  Expected: **4 passed**.

  Common failure modes:
  - Go fails with `undefined: ListNode` → the Python starter doesn't have a valid `class ListNode` definition, so the param-type parser didn't set `{"head": "ListNode"}`, so the Go harness didn't inject the type. Verify the Python starter matches the catalog pattern exactly.
  - Java compile error: the user code must NOT include a `ListNode` class definition (the harness injects one as a sibling). Keep the Java solution to just the method.

- [ ] **Step 10.3: Commit**

  ```
  git add backend/tests/integration/fixtures.py
  git commit -m "test(integration): add reverse-linked-list fixture (ListNode round-trip)"
  ```

---

## Task 11: Add TreeNode fixture (`max-tree-depth`)

**Files:**
- Modify: `backend/tests/integration/fixtures.py`

- [ ] **Step 11.1: Append `MAX_TREE_DEPTH` fixture**

  ```python
  # ---------- Fixture: TreeNode -> int ----------

  MAX_TREE_DEPTH = ProblemFixture(
      slug="max-tree-depth",
      description="TreeNode in, int out",
      starter_code={
          "python": (
              "from typing import Optional\n"
              "\n"
              "class TreeNode:\n"
              "    def __init__(self, val=0, left=None, right=None):\n"
              "        self.val = val\n"
              "        self.left = left\n"
              "        self.right = right\n"
              "\n"
              "def max_depth(root: Optional[TreeNode]) -> int:\n"
              "    pass\n"
          ),
          "javascript": (
              "class TreeNode {\n"
              "    constructor(val = 0, left = null, right = null) {\n"
              "        this.val = val;\n"
              "        this.left = left;\n"
              "        this.right = right;\n"
              "    }\n"
              "}\n"
              "\n"
              "function max_depth(root) {\n"
              "}\n"
          ),
          "go": (
              "type TreeNode struct {\n"
              "    Val   int\n"
              "    Left  *TreeNode\n"
              "    Right *TreeNode\n"
              "}\n"
              "\n"
              "func max_depth(root *TreeNode) int {\n"
              "    return 0\n"
              "}\n"
          ),
          "java": (
              "public int max_depth(TreeNode root) {\n"
              "    return 0;\n"
              "}\n"
          ),
      },
      # Serialized tree format matches the catalog: level-order with `null`
      # for missing nodes. Example [3, 9, 20, null, null, 15, 7] is:
      #        3
      #       / \
      #      9   20
      #         /  \
      #        15   7
      test_cases=[
          {"input": {"root": [3, 9, 20, None, None, 15, 7]}, "expected": 3},
          {"input": {"root": [1, None, 2]}, "expected": 2},
          {"input": {"root": []}, "expected": 0},
          {"input": {"root": [1]}, "expected": 1},
      ],
      solutions={
          "python": (
              "def max_depth(root):\n"
              "    if root is None:\n"
              "        return 0\n"
              "    return 1 + max(max_depth(root.left), max_depth(root.right))\n"
          ),
          "javascript": (
              "function max_depth(root) {\n"
              "    if (root === null) return 0;\n"
              "    return 1 + Math.max(max_depth(root.left), max_depth(root.right));\n"
              "}\n"
          ),
          "go": (
              "func max_depth(root *TreeNode) int {\n"
              "    if root == nil {\n"
              "        return 0\n"
              "    }\n"
              "    l := max_depth(root.Left)\n"
              "    r := max_depth(root.Right)\n"
              "    if l > r {\n"
              "        return l + 1\n"
              "    }\n"
              "    return r + 1\n"
              "}\n"
          ),
          "java": (
              "public int max_depth(TreeNode root) {\n"
              "    if (root == null) return 0;\n"
              "    return 1 + Math.max(max_depth(root.left), max_depth(root.right));\n"
              "}\n"
          ),
      },
  )
  ```

  Update `FIXTURES`:
  ```python
  FIXTURES: list[ProblemFixture] = [
      ADD_TWO_INTS,
      REVERSE_ARRAY,
      IS_PALINDROME,
      REVERSE_LINKED_LIST,
      MAX_TREE_DEPTH,
  ]
  ```

- [ ] **Step 11.2: Run the matrix for this fixture**

  Run: `cd backend && .venv/bin/python -m pytest tests/integration/test_harness_matrix.py -m integration -v -k max-tree-depth`
  Expected: **4 passed**.

- [ ] **Step 11.3: Commit**

  ```
  git add backend/tests/integration/fixtures.py
  git commit -m "test(integration): add max-tree-depth fixture (TreeNode round-trip)"
  ```

---

## Task 12: Add GraphNode fixture (`graph-node-count`)

**Why:** Validates GraphNode handling — the third custom type. Uses node count (the simplest graph-traversal problem) to avoid the complexity of graph-identity/clone assertions.

**Files:**
- Modify: `backend/tests/integration/fixtures.py`

- [ ] **Step 12.0: Verify how the catalog serializes graphs**

  Before writing this fixture, check the existing catalog for a GraphNode problem to mirror the serialization:
  ```
  grep -rln "GraphNode" backend/app/harnesses/python.py | head -3
  cat backend/app/harnesses/python.py | sed -n '80,110p'
  ```
  Expected: the Python harness `GraphNode` serializer builds nodes from an adjacency list `adj`, where `adj[i]` is the list of neighbor-indices for node `i+1`. Test cases pass `{"node": adj}` and the harness builds a graph, feeds it in, and serializes the returned graph back.

  Cross-check by finding any catalog `.yaml` that uses GraphNode (there may or may not be one):
  ```
  grep -rln "GraphNode" "dsa-flash-cards/" || echo "(no catalog problem uses GraphNode yet)"
  ```

  If no catalog problem exists, proceed with Step 12.2 using the adjacency-list format described above. If a catalog problem exists, open it and mirror its test_cases shape exactly.

- [ ] **Step 12.1: Append `GRAPH_NODE_COUNT` fixture**

  ```python
  # ---------- Fixture: GraphNode -> int ----------

  GRAPH_NODE_COUNT = ProblemFixture(
      slug="graph-node-count",
      description="GraphNode in, int out (count reachable nodes)",
      starter_code={
          "python": (
              "from typing import Optional\n"
              "\n"
              "class GraphNode:\n"
              "    def __init__(self, val=0, neighbors=None):\n"
              "        self.val = val\n"
              "        self.neighbors = neighbors if neighbors is not None else []\n"
              "\n"
              "def count_nodes(node: Optional[GraphNode]) -> int:\n"
              "    pass\n"
          ),
          "javascript": (
              "class GraphNode {\n"
              "    constructor(val = 0, neighbors = null) {\n"
              "        this.val = val;\n"
              "        this.neighbors = neighbors === null ? [] : neighbors;\n"
              "    }\n"
              "}\n"
              "\n"
              "function count_nodes(node) {\n"
              "}\n"
          ),
          "go": (
              "type GraphNode struct {\n"
              "    Val       int\n"
              "    Neighbors []*GraphNode\n"
              "}\n"
              "\n"
              "func count_nodes(node *GraphNode) int {\n"
              "    return 0\n"
              "}\n"
          ),
          "java": (
              "public int count_nodes(GraphNode node) {\n"
              "    return 0;\n"
              "}\n"
          ),
      },
      # Adjacency-list format: adj[i] = 1-indexed neighbors of node (i+1).
      # Example [[2,4],[1,3],[2,4],[1,3]] is K4-style:
      #   1 -- 2
      #   |    |
      #   4 -- 3
      test_cases=[
          {"input": {"node": [[2, 4], [1, 3], [2, 4], [1, 3]]}, "expected": 4},
          {"input": {"node": [[2], [1]]}, "expected": 2},
          {"input": {"node": [[]]}, "expected": 1},
          {"input": {"node": []}, "expected": 0},
      ],
      solutions={
          "python": (
              "def count_nodes(node):\n"
              "    if node is None:\n"
              "        return 0\n"
              "    seen = set()\n"
              "    stack = [node]\n"
              "    while stack:\n"
              "        n = stack.pop()\n"
              "        if id(n) in seen:\n"
              "            continue\n"
              "        seen.add(id(n))\n"
              "        for nb in n.neighbors:\n"
              "            stack.append(nb)\n"
              "    return len(seen)\n"
          ),
          "javascript": (
              "function count_nodes(node) {\n"
              "    if (node === null) return 0;\n"
              "    const seen = new Set();\n"
              "    const stack = [node];\n"
              "    while (stack.length) {\n"
              "        const n = stack.pop();\n"
              "        if (seen.has(n)) continue;\n"
              "        seen.add(n);\n"
              "        for (const nb of n.neighbors) stack.push(nb);\n"
              "    }\n"
              "    return seen.size;\n"
              "}\n"
          ),
          "go": (
              "func count_nodes(node *GraphNode) int {\n"
              "    if node == nil {\n"
              "        return 0\n"
              "    }\n"
              "    seen := map[*GraphNode]bool{}\n"
              "    stack := []*GraphNode{node}\n"
              "    for len(stack) > 0 {\n"
              "        n := stack[len(stack)-1]\n"
              "        stack = stack[:len(stack)-1]\n"
              "        if seen[n] {\n"
              "            continue\n"
              "        }\n"
              "        seen[n] = true\n"
              "        for _, nb := range n.Neighbors {\n"
              "            stack = append(stack, nb)\n"
              "        }\n"
              "    }\n"
              "    return len(seen)\n"
              "}\n"
          ),
          "java": (
              "public int count_nodes(GraphNode node) {\n"
              "    if (node == null) return 0;\n"
              "    java.util.Set<GraphNode> seen = new java.util.HashSet<>();\n"
              "    java.util.Deque<GraphNode> stack = new java.util.ArrayDeque<>();\n"
              "    stack.push(node);\n"
              "    while (!stack.isEmpty()) {\n"
              "        GraphNode n = stack.pop();\n"
              "        if (!seen.add(n)) continue;\n"
              "        for (GraphNode nb : n.neighbors) stack.push(nb);\n"
              "    }\n"
              "    return seen.size();\n"
              "}\n"
          ),
      },
  )
  ```

  Update `FIXTURES`:
  ```python
  FIXTURES: list[ProblemFixture] = [
      ADD_TWO_INTS,
      REVERSE_ARRAY,
      IS_PALINDROME,
      REVERSE_LINKED_LIST,
      MAX_TREE_DEPTH,
      GRAPH_NODE_COUNT,
  ]
  ```

- [ ] **Step 12.2: Run the matrix for this fixture**


  Run: `cd backend && .venv/bin/python -m pytest tests/integration/test_harness_matrix.py -m integration -v -k graph-node-count`
  Expected: **4 passed**.

  If the `[]` empty-graph test case fails because the harness can't represent "no node" → drop that single test case from the fixture's `test_cases` and re-run. Leave a comment in the fixture explaining why.

- [ ] **Step 12.3: Run the full matrix to confirm nothing else regressed**

  Run: `cd backend && .venv/bin/python -m pytest tests/integration/test_harness_matrix.py -m integration -v`
  Expected: **24 passed** (6 fixtures × 4 languages).

- [ ] **Step 12.4: Commit**

  ```
  git add backend/tests/integration/fixtures.py
  git commit -m "test(integration): add graph-node-count fixture (GraphNode round-trip)"
  ```

---

## Task 13: Catalog smoke tests (real problems from `dsa-flash-cards/`)

**Why:** Answers "is the real YAML pipeline + catalog content still wired up correctly?" The harness-matrix suite already covers every param-type shape. Two catalog problems are enough — primitives/arrays (`two-sum`) and a custom type (`maximum-depth-of-binary-tree`).

**Note on loading:** `app.loader.load_coding_problems()` uses its own engine from `app.database`, so it can't be called against the TestContainers session. Instead, the smoke test reads the YAML files directly and inserts them via the test session — lightweight and self-contained.

**Files:**
- Create: `backend/tests/integration/catalog_solutions.py`
- Create: `backend/tests/integration/test_catalog_smoke.py`

- [ ] **Step 13.1: Create `backend/tests/integration/catalog_solutions.py`**

  ```python
  """Canonical known-good solutions for catalog smoke tests.

  Keys are catalog problem titles (matching the `title:` field in the YAML).
  Adding a smoke case: pick a catalog YAML, add its title as a new outer key
  with {lang: solution} inner dict, then add the title to
  test_catalog_smoke.CATALOG_SLUGS.
  """

  CATALOG_SOLUTIONS: dict[str, dict[str, str]] = {
      "Two Sum": {
          "python": (
              "def two_sum(nums, target):\n"
              "    seen = {}\n"
              "    for i, n in enumerate(nums):\n"
              "        if target - n in seen:\n"
              "            return [seen[target - n], i]\n"
              "        seen[n] = i\n"
              "    return []\n"
          ),
          "javascript": (
              "function two_sum(nums, target) {\n"
              "    const seen = new Map();\n"
              "    for (let i = 0; i < nums.length; i++) {\n"
              "        const complement = target - nums[i];\n"
              "        if (seen.has(complement)) return [seen.get(complement), i];\n"
              "        seen.set(nums[i], i);\n"
              "    }\n"
              "    return [];\n"
              "}\n"
          ),
          "go": (
              "func two_sum(nums []int, target int) []int {\n"
              "    seen := map[int]int{}\n"
              "    for i, n := range nums {\n"
              "        if j, ok := seen[target-n]; ok {\n"
              "            return []int{j, i}\n"
              "        }\n"
              "        seen[n] = i\n"
              "    }\n"
              "    return []int{}\n"
              "}\n"
          ),
          "java": (
              "public int[] two_sum(int[] nums, int target) {\n"
              "    java.util.Map<Integer, Integer> seen = new java.util.HashMap<>();\n"
              "    for (int i = 0; i < nums.length; i++) {\n"
              "        int complement = target - nums[i];\n"
              "        if (seen.containsKey(complement)) {\n"
              "            return new int[]{seen.get(complement), i};\n"
              "        }\n"
              "        seen.put(nums[i], i);\n"
              "    }\n"
              "    return new int[0];\n"
              "}\n"
          ),
      },
      "Maximum Depth of Binary Tree": {
          "python": (
              "def max_depth(root):\n"
              "    if root is None:\n"
              "        return 0\n"
              "    return 1 + max(max_depth(root.left), max_depth(root.right))\n"
          ),
          "javascript": (
              "function max_depth(root) {\n"
              "    if (root === null) return 0;\n"
              "    return 1 + Math.max(max_depth(root.left), max_depth(root.right));\n"
              "}\n"
          ),
          "go": (
              "func max_depth(root *TreeNode) int {\n"
              "    if root == nil {\n"
              "        return 0\n"
              "    }\n"
              "    l := max_depth(root.Left)\n"
              "    r := max_depth(root.Right)\n"
              "    if l > r {\n"
              "        return l + 1\n"
              "    }\n"
              "    return r + 1\n"
              "}\n"
          ),
          "java": (
              "public int max_depth(TreeNode root) {\n"
              "    if (root == null) return 0;\n"
              "    return 1 + Math.max(max_depth(root.left), max_depth(root.right));\n"
              "}\n"
          ),
      },
  }
  ```

- [ ] **Step 13.2: Create `backend/tests/integration/test_catalog_smoke.py`**

  ```python
  """Catalog smoke tests.

  Loads real CodingProblem rows by reading YAML files directly from the
  dsa-flash-cards submodule, then submits canonical solutions in all four
  languages. Complements the synthetic fixture matrix by validating that
  real catalog content still flows through the harness + Judge0 pipeline.
  """
  from pathlib import Path

  import pytest
  import yaml
  from sqlmodel import select

  from app.models import CodingProblem

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
  ```

  **Note on function names for catalog problems:** The harness builders derive the function name from the Python starter. Look at the catalog YAML to confirm — `two-sum.yaml` Python starter has `def two_sum(...)`, and `maximum-depth-of-binary-tree.yaml` has `def max_depth(...)`. If the catalog evolves and uses different names, the `CATALOG_SOLUTIONS` entries in Step 13.1 must match. Verify before running:

  ```
  grep -A1 "^  python:" "dsa-flash-cards/data structures/problems/two-sum.yaml" | head
  grep -A1 "^  python:" "dsa-flash-cards/data structures/problems/maximum-depth-of-binary-tree.yaml" | head
  ```

  If the function names differ from `two_sum` / `max_depth`, update the solutions in `catalog_solutions.py` accordingly before running Step 13.3.

- [ ] **Step 13.3: Run the catalog smoke tests**

  Run: `cd backend && .venv/bin/python -m pytest tests/integration/test_catalog_smoke.py -m integration -v`
  Expected: **8 passed** (2 titles × 4 languages).

  If a test fails:
  - `FileNotFoundError: ... not found under ... dsa-flash-cards` → the catalog title was renamed. Update `CATALOG_SOLUTIONS` and `_find_yaml_by_title` call sites.
  - `status=='Compilation Error'` for a specific language → the catalog's function name for that language differs from what `CATALOG_SOLUTIONS` provides. Read the catalog YAML for that problem and align.
  - `status=='Wrong Answer'` equivalent (status=='Accepted' but `passed=False`) → the solution source has a bug; fix it and re-run.

- [ ] **Step 13.4: Run the full integration suite**

  Run: `make test-integration`
  Expected: **32 passed** (24 harness matrix + 8 catalog smoke).

- [ ] **Step 13.5: Commit**

  ```
  git add backend/tests/integration/catalog_solutions.py backend/tests/integration/test_catalog_smoke.py
  git commit -m "test(integration): add catalog smoke tests (two-sum, max-depth)"
  ```

---

## Task 14: Regression-guard spot-check

**Why:** Success criterion #2 in the spec: reverting the Java memory limit must cause Java tests to fail with a clear diagnostic. We verify this manually once so we know the guard works, then revert.

- [ ] **Step 14.1: Temporarily break the Java limit**

  In `backend/app/api/problems.py`, change the Java `memory_limit` from `512000` back to `128000` (the old broken value).

- [ ] **Step 14.2: Run the Java tests and confirm they fail with a heap error**

  Run: `cd backend && .venv/bin/python -m pytest tests/integration/test_harness_matrix.py -m integration -v -k java`
  Expected: **6 failed** (one per fixture). The assertion message for each failure should contain "Could not reserve enough space" or equivalent JVM startup error in `stderr`.

  If the failure message does NOT name the language + fixture + stderr clearly, the assertion-message formatting in `test_harness_matrix.py` is insufficient — improve it before continuing.

- [ ] **Step 14.3: Revert the Java limit**

  Change `memory_limit` back to `512000`.

- [ ] **Step 14.4: Re-run and confirm green**

  Run: `make test-integration`
  Expected: **32 passed**.

- [ ] **Step 14.5: No commit for this task** — nothing changed on disk after the revert. This is a manual verification step, not a code change.

---

## Task 15: Add Phase 2 follow-ups to `TODOS.md`

**Files:**
- Modify: `TODOS.md` (create if it doesn't exist)

- [ ] **Step 15.1: Check whether `TODOS.md` exists**

  Run: `ls TODOS.md 2>/dev/null && echo "exists" || echo "missing"`

  If **missing**, create it with:
  ```markdown
  # TODOs

  Follow-up work tracked outside the scoped task board in `.claude/TASKS.md`.

  ## Integration tests — Phase 2

  Follow-ups from `docs/superpowers/specs/2026-04-05-harness-judge0-config-and-e2e-tests-design.md`:

  - Additional `ProblemFixture` entries: nested types, 2D arrays, map/dict return types.
  - Error path fixtures × 4 languages: function name missing from user code, runtime exception in user code, wrong return type, malformed source.
  - CI workflow: GitHub Actions job that brings up the dev stack and runs `pytest -m integration` on PRs touching `backend/app/harnesses/` or `backend/app/api/problems.py`.
  - Watchdog: if any Phase 1 integration test takes > 15 s wall-clock, flag as potential Judge0 regression.
  ```

  If **exists**, append this section to the end (preserving any existing content):
  ```markdown

  ## Integration tests — Phase 2

  Follow-ups from `docs/superpowers/specs/2026-04-05-harness-judge0-config-and-e2e-tests-design.md`:

  - Additional `ProblemFixture` entries: nested types, 2D arrays, map/dict return types.
  - Error path fixtures × 4 languages: function name missing from user code, runtime exception in user code, wrong return type, malformed source.
  - CI workflow: GitHub Actions job that brings up the dev stack and runs `pytest -m integration` on PRs touching `backend/app/harnesses/` or `backend/app/api/problems.py`.
  - Watchdog: if any Phase 1 integration test takes > 15 s wall-clock, flag as potential Judge0 regression.
  ```

- [ ] **Step 15.2: Commit**

  ```
  git add TODOS.md
  git commit -m "docs: track Phase 2 integration test follow-ups"
  ```

---

## Task 16: Final full-suite verification

- [ ] **Step 16.1: Default pytest run is still fast and green**

  Run: `cd backend && .venv/bin/python -m pytest tests/ -q`
  Expected: all previously-passing tests still pass (84+), integration tests skipped via `-m "not integration"` addopts. Total wall time should be close to the pre-plan baseline (~10 s).

- [ ] **Step 16.2: Integration suite is fully green**

  Run: `make test-integration`
  Expected: **32 passed**, total wall time 60–90 s depending on Judge0 warm/cold state.

- [ ] **Step 16.3: Review the commit history**

  Run: `git log --oneline main..HEAD`
  Expected: a clean sequence of ~13 focused commits (one per task). No commit should contain unrelated file changes.

- [ ] **Step 16.4: Task done** — summarize to the user which commits landed, highlight any deviations from the plan (e.g. a fixture that needed a larger memory budget than the spec said), and offer to open a PR.

---

## Notes for the engineer

- **Do NOT add `Co-Authored-By:` trailers to commits.** Project convention per `.claude/CLAUDE.md` equivalent memory.
- **Conventional commit prefixes:** `fix:`, `feat:`, `test:`, `chore:`, `docs:`. Scope in parens when useful (e.g. `test(integration):`).
- **One task = one commit.** Exception: Task 6 (write the failing test) and Task 7 (fix the config) land as a single commit because the repo should never have a state where the new test exists and fails.
- **If a step says "verify X" and X doesn't happen**, stop and investigate. Do not paper over unexpected behavior — the whole point of the plan is to surface real issues, and unexplained deviations are signal.
- **Rate limiting:** the submit endpoint has `@limiter.limit("10/minute")`. The top-level `backend/tests/conftest.py` has an autouse `reset_rate_limiter` fixture that clears storage between tests, so this is handled. If you see 429s anyway, something broke that fixture — investigate, don't disable it.
- **Running the venv:** prefer `.venv/bin/python -m pytest` over bare `pytest` to avoid any PATH ambiguity.
