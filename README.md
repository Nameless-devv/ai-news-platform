# AI News Platform

Real-time news platform for Uzbekistan and global sources — powered by OpenAI GPT.

## Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14, Tailwind CSS, TypeScript |
| Backend | FastAPI, Python 3.12 |
| Database | PostgreSQL 16 |
| Cache/Queue | Redis 7 |
| Worker | Celery + Celery Beat |
| AI | OpenAI GPT-4o-mini |
| Proxy | Nginx |

## Quick Start

### 1. Clone & configure

```bash
cp .env.example .env
# Edit .env — add your OPENAI_API_KEY and set SECRET_KEY
```

### 2. Run with Docker

```bash
make build
make up
make migrate
```

Services:
- Frontend: http://localhost:3000
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Via Nginx: http://localhost:80

### 3. Trigger first news fetch

```bash
make trigger-fetch
```

## Local Development (without Docker)

**Prerequisites:** Python 3.12, Node 20, PostgreSQL, Redis

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env  # edit DATABASE_URL to localhost
uvicorn app.main:app --reload

# Worker (separate terminal)
celery -A app.workers.celery_app worker --loglevel=info -Q fetcher,processor

# Beat scheduler (separate terminal)
celery -A app.workers.celery_app beat --loglevel=info

# Frontend
cd frontend
npm install
npm run dev
```

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/news` | List processed news (pagination, filter by category/country/search) |
| GET | `/api/v1/news/{id}` | Single news detail |
| GET | `/api/v1/news/trending` | Trending topic categories |
| POST | `/api/v1/news/generate` | Generate headlines from custom text |
| POST | `/api/v1/news/bookmarks` | Save a bookmark |
| GET | `/api/v1/news/bookmarks/{session_id}` | Get user bookmarks |
| DELETE | `/api/v1/news/bookmarks/{session_id}/{news_id}` | Remove bookmark |
| GET | `/api/v1/admin/stats` | Platform statistics (requires X-Admin-Key header) |
| POST | `/api/v1/admin/trigger-fetch` | Manually trigger news fetch |
| POST | `/api/v1/admin/flush-cache` | Flush Redis cache |
| WS | `/ws` | WebSocket for real-time updates |

## Environment Variables

See `.env.example` for all variables. Key ones:

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | **Required.** Your OpenAI API key |
| `SECRET_KEY` | Admin API key — keep secret |
| `POSTGRES_PASSWORD` | PostgreSQL password |
| `FETCH_INTERVAL_MINUTES` | How often to fetch RSS feeds (default: 5) |
| `RATE_LIMIT_PER_MINUTE` | API rate limit per IP (default: 60) |

## Database Schema

```sql
news_raw
  id, source, source_country, title, content, url, image_url,
  published_at, fetched_at, is_processed

news_processed
  id, raw_id (FK), summary, ai_headlines (JSON), category,
  sentiment, tags (JSON), processed_at

bookmarks
  id, news_id (FK), session_id, created_at
```

## Production Deployment

1. Set production env vars (strong passwords, real domain)
2. Update `NEXT_PUBLIC_API_URL` and `NEXT_PUBLIC_WS_URL` to your domain
3. Add SSL via Certbot to Nginx config
4. `make build && make up && make migrate`

## Architecture

```
Browser ──► Nginx (port 80)
               ├── /api/*  ──► FastAPI backend (port 8000)
               ├── /ws     ──► FastAPI WebSocket
               └── /*      ──► Next.js frontend (port 3000)

FastAPI ──► PostgreSQL (persistent data)
        └── Redis (cache + task queue)

Celery Beat ──► Redis queue ──► Celery Worker
                                   ├── Fetch RSS feeds
                                   └── OpenAI API → store processed news
```
