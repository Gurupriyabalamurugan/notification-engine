.PHONY: up down logs test migrate seed api worker retry-worker topics

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f api worker retry-worker

migrate:
	alembic upgrade head

test:
	pytest -v

seed:
	python scripts/seed_events.py

topics:
	python scripts/init_kafka_topics.py

api:
	uvicorn app.main:app --reload --port 8000

worker:
	python -m app.workers.dispatcher_worker

retry-worker:
	python -m app.workers.retry_worker
