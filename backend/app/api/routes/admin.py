from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.news import NewsRaw, NewsProcessed
from app.services.cache_service import cache
from app.config import settings

router = APIRouter(prefix="/admin", tags=["admin"])


def _require_admin(x_admin_key: str | None = Header(default=None)) -> None:
    if x_admin_key != settings.SECRET_KEY:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.get("/stats")
async def stats(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_require_admin),
):
    raw_count = (await db.execute(select(func.count(NewsRaw.id)))).scalar_one()
    processed_count = (await db.execute(select(func.count(NewsProcessed.id)))).scalar_one()
    pending = raw_count - processed_count

    cat_result = await db.execute(
        select(NewsProcessed.category, func.count().label("cnt"))
        .group_by(NewsProcessed.category)
        .order_by(desc("cnt"))
    )
    categories = {row.category: row.cnt for row in cat_result.all()}

    return {
        "total_raw": raw_count,
        "total_processed": processed_count,
        "pending_processing": pending,
        "categories": categories,
    }


@router.post("/flush-cache")
async def flush_cache(_: None = Depends(_require_admin)):
    await cache.delete_pattern("news:*")
    return {"message": "Cache flushed"}


@router.post("/trigger-fetch")
async def trigger_fetch(_: None = Depends(_require_admin)):
    from app.workers.tasks import fetch_and_queue_news
    task = fetch_and_queue_news.delay()
    return {"task_id": task.id, "status": "queued"}
