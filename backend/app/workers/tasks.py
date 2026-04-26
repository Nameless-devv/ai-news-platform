import asyncio
import logging
from sqlalchemy import select

from app.workers.celery_app import celery_app
from app.config import settings

logger = logging.getLogger(__name__)


def _get_sync_db():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    engine = create_engine(settings.DATABASE_SYNC_URL, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


@celery_app.task(name="app.workers.tasks.fetch_and_queue_news", bind=True, max_retries=3)
def fetch_and_queue_news(self):
    """Fetch RSS feeds and enqueue unprocessed articles."""
    try:
        asyncio.run(_async_fetch_and_queue())
    except Exception as exc:
        logger.error("fetch_and_queue_news failed: %s", exc)
        raise self.retry(exc=exc, countdown=60)


async def _async_fetch_and_queue():
    from app.services.news_fetcher import news_fetcher
    from app.models.news import NewsRaw
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

    engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    queued = 0
    async with SessionLocal() as db:
        async for article_data in news_fetcher.fetch_all():
            url = article_data.get("url", "")
            existing = await db.execute(
                select(NewsRaw).where(NewsRaw.url == url)
            )
            if existing.scalar_one_or_none():
                continue

            skip_keys = {"url_hash"}
            raw = NewsRaw(**{k: v for k, v in article_data.items() if k not in skip_keys})
            db.add(raw)
            await db.flush()

            process_article.delay(raw.id, article_data.get("hint_category"))
            queued += 1

        await db.commit()

    await engine.dispose()
    logger.info("Fetched and queued %d new articles", queued)


@celery_app.task(name="app.workers.tasks.process_article", bind=True, max_retries=3)
def process_article(self, raw_id: int, hint_category: str | None = None):
    """Process a single article with AI."""
    try:
        asyncio.run(_async_process_article(raw_id, hint_category))
    except Exception as exc:
        logger.error("process_article(%s) failed: %s", raw_id, exc)
        raise self.retry(exc=exc, countdown=30)


async def _async_process_article(raw_id: int, hint_category: str | None = None):
    from app.services.ai_service import ai_service
    from app.models.news import NewsRaw, NewsProcessed
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

    engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with SessionLocal() as db:
        raw = await db.get(NewsRaw, raw_id)
        if not raw or raw.is_processed:
            return

        result = await ai_service.process_article(raw.title, raw.content, source=raw.source)
        if not result:
            return

        # Use hint_category as fallback when AI doesn't return one
        category = result.get("category") or hint_category

        processed = NewsProcessed(
            raw_id=raw_id,
            summary=result.get("summary"),
            ai_headlines=result.get("headlines", []),
            category=category,
            sentiment=result.get("sentiment"),
            tags=result.get("tags", []),
        )
        db.add(processed)
        raw.is_processed = True
        await db.commit()

        # Invalidate relevant cache keys
        from app.services.cache_service import cache
        await cache.delete_pattern("news:list:*")

    await engine.dispose()
    logger.info("Processed article raw_id=%s", raw_id)
