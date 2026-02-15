.PHONY: dev prod down logs

dev:
	docker compose --profile prod down --remove-orphans
	DEV_MODE=1 docker compose --profile dev up --build

prod:
	docker compose --profile prod up --build -d

down:
	docker compose --profile prod down --remove-orphans
	docker compose --profile dev  down --remove-orphans

logs:
	docker compose logs -f
