.PHONY: setup up down logs test lint format typecheck security migrate migration seed clean

setup:
	cp -n .env.example .env || true
	docker compose pull
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f --tail=200

test:
	docker compose run --rm api pytest -q

lint:
	docker compose run --rm api ruff check .

format:
	docker compose run --rm api ruff format .

typecheck:
	docker compose run --rm api mypy .

security:
	docker compose run --rm security-worker ./scripts/security-check.sh

migrate:
	docker compose run --rm api alembic upgrade head

migration:
	docker compose run --rm api alembic revision --autogenerate -m "$(name)"

seed:
	docker compose run --rm api python -m app.db.seed

clean:
	docker compose down -v --remove-orphans
