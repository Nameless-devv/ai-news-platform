.PHONY: up down logs build migrate seed dev-backend dev-frontend

# ── Docker compose shortcuts ──────────────────────────────
up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build --no-cache

logs:
	docker compose logs -f

# ── Database ──────────────────────────────────────────────
migrate:
	docker compose exec backend alembic upgrade head

makemigration:
	docker compose exec backend alembic revision --autogenerate -m "$(msg)"

# ── Admin helpers ─────────────────────────────────────────
trigger-fetch:
	curl -s -X POST http://localhost:8000/api/v1/admin/trigger-fetch \
	  -H "X-Admin-Key: $$(grep SECRET_KEY .env | cut -d= -f2)" | jq .

flush-cache:
	curl -s -X POST http://localhost:8000/api/v1/admin/flush-cache \
	  -H "X-Admin-Key: $$(grep SECRET_KEY .env | cut -d= -f2)" | jq .

stats:
	curl -s http://localhost:8000/api/v1/admin/stats \
	  -H "X-Admin-Key: $$(grep SECRET_KEY .env | cut -d= -f2)" | jq .

# ── Local dev (no docker) ─────────────────────────────────
dev-backend:
	cd backend && uvicorn app.main:app --reload --port 8000

dev-worker:
	cd backend && celery -A app.workers.celery_app worker --loglevel=info -Q fetcher,processor

dev-beat:
	cd backend && celery -A app.workers.celery_app beat --loglevel=info

dev-frontend:
	cd frontend && npm run dev
