.PHONY: dev prod down logs validate-problems test-integration

dev:
	docker compose --profile prod down --remove-orphans
	DEV_MODE=1 docker compose --profile dev up --build

prod:
	docker compose --profile prod pull
	docker compose --profile prod build backup
	docker compose --profile prod up -d

down:
	docker compose --profile prod down --remove-orphans
	docker compose --profile dev  down --remove-orphans

logs:
	docker compose logs -f

# Run the problem validator against every problem YAML in all installed
# languages (python/javascript/go/java). Mirrors the `validate` CI job — use
# this to catch harness/content regressions before pushing. Requires
# backend/.venv and the relevant runtimes on PATH. Missing runtimes are
# skipped with a warning.
validate-problems:
	@if [ ! -x backend/.venv/bin/python ]; then \
		echo "error: backend/.venv not found. Create it with:"; \
		echo "  cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt -r requirements-test.txt"; \
		exit 1; \
	fi
	cd backend && .venv/bin/python scripts/validate_problems.py

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
