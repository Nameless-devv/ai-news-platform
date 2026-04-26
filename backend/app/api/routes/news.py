import logging
import re
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select, func, desc, text, over, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.database import get_db
from app.models.news import NewsRaw, NewsProcessed, Bookmark
from app.schemas.news import (
    NewsListResponse, NewsProcessedSchema, NewsDetailSchema,
    GenerateRequest, GenerateResponse, BookmarkCreate, BookmarkSchema,
    TrendingTopic
)
from app.services.ai_service import ai_service
from app.services.cache_service import cache
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/news", tags=["news"])


def _to_schema(p: NewsProcessed) -> NewsProcessedSchema:
    raw = p.raw
    return NewsProcessedSchema(
        id=p.id,
        raw_id=p.raw_id,
        summary=p.summary,
        ai_headlines=p.ai_headlines or [],
        category=p.category,
        sentiment=p.sentiment,
        tags=p.tags or [],
        processed_at=p.processed_at,
        source=raw.source if raw else None,
        source_country=raw.source_country if raw else None,
        title=raw.title if raw else None,
        url=raw.url if raw else None,
        image_url=raw.image_url if raw else None,
        published_at=raw.published_at if raw else None,
    )


def _strip_html(text: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p>|</div>|</li>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = (text
            .replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<")
            .replace("&gt;", ">").replace("&quot;", '"').replace("&#39;", "'")
            .replace("&mdash;", "—").replace("&ndash;", "–").replace("&hellip;", "…"))
    return re.sub(r"\s{2,}", " ", text).strip()


_HN_META_RE = re.compile(r"^(Article URL:|Comments URL:|Points:|\# Comments:)", re.MULTILINE)


def _raw_to_schema(r: NewsRaw) -> NewsProcessedSchema:
    """Fallback: return raw article when AI processing hasn't run yet."""
    summary = None
    if r.content:
        clean = _strip_html(r.content).strip()
        # Skip HN-style metadata (Article URL / Comments URL / Points)
        if clean and not _HN_META_RE.search(clean[:120]):
            summary = clean[:400] + ("..." if len(clean) > 400 else "")
    return NewsProcessedSchema(
        id=r.id,
        raw_id=r.id,
        summary=summary,
        ai_headlines=[],
        category=getattr(r, "hint_category", None),
        sentiment=None,
        tags=[],
        processed_at=r.fetched_at,
        source=r.source,
        source_country=r.source_country,
        title=r.title,
        url=r.url,
        image_url=r.image_url,
        published_at=r.published_at,
    )


async def _check_rate_limit(request: Request) -> None:
    ip = request.client.host if request.client else "unknown"
    key = cache.make_key("rate", ip)
    count = await cache.increment(key, ttl=60)
    if count > settings.RATE_LIMIT_PER_MINUTE:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")


@router.get("", response_model=NewsListResponse)
async def list_news(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: str | None = None,
    country: str | None = None,
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    await _check_rate_limit(request)

    cache_key = cache.make_key(
        "news:list",
        f"p{page}",
        f"ps{page_size}",
        f"cat{category or ''}",
        f"co{country or ''}",
        f"q{search or ''}",
    )
    cached = await cache.get(cache_key)
    if cached:
        return cached

    offset = (page - 1) * page_size

    # Build WHERE filters
    filters_processed: list = []
    filters_raw: list = []
    if category:
        filters_processed.append(NewsProcessed.category == category)
    if country:
        filters_processed.append(NewsRaw.source_country == country.upper())
        filters_raw.append(NewsRaw.source_country == country.upper())
    if search:
        like = f"%{search}%"
        filters_processed.append(
            NewsRaw.title.ilike(like) | NewsProcessed.summary.ilike(like) | NewsRaw.content.ilike(like)
        )
        filters_raw.append(NewsRaw.title.ilike(like) | NewsRaw.content.ilike(like))

    # Count total
    count_q = (
        select(func.count(NewsProcessed.id))
        .join(NewsRaw, NewsProcessed.raw_id == NewsRaw.id)
    )
    for f in filters_processed:
        count_q = count_q.where(f)
    total = (await db.execute(count_q)).scalar_one()

    # Fallback to raw articles when nothing is processed yet
    if total == 0:
        raw_count_q = select(func.count(NewsRaw.id))
        for f in filters_raw:
            raw_count_q = raw_count_q.where(f)
        if category:
            raw_count_q = raw_count_q.where(NewsRaw.hint_category == category)

        raw_total = (await db.execute(raw_count_q)).scalar_one()

        # Build SQL WHERE safely
        clauses = []
        if category:
            clauses.append(f"hint_category = '{category}'")
        if country:
            clauses.append(f"source_country = '{country.upper()}'")
        if search:
            safe = search.replace("'", "''")
            clauses.append(f"title ILIKE '%{safe}%'")
        where_clause = ("WHERE " + " AND ".join(clauses)) if clauses else ""

        # Always round-robin by source; when search use chronological
        if search:
            raw_sql = text(f"""
                SELECT id FROM news_raw
                {where_clause}
                ORDER BY published_at DESC NULLS LAST, fetched_at DESC
                LIMIT :limit OFFSET :offset
            """)
        else:
            raw_sql = text(f"""
                WITH ranked AS (
                    SELECT id,
                        ROW_NUMBER() OVER (
                            PARTITION BY source
                            ORDER BY published_at DESC NULLS LAST, fetched_at DESC
                        ) AS rn,
                        published_at
                    FROM news_raw
                    {where_clause}
                )
                SELECT id FROM ranked
                ORDER BY rn, published_at DESC NULLS LAST
                LIMIT :limit OFFSET :offset
            """)

        id_rows = (await db.execute(raw_sql, {"limit": page_size, "offset": offset})).fetchall()
        ordered_ids = [r[0] for r in id_rows]

        if ordered_ids:
            raw_result = await db.execute(
                select(NewsRaw).where(NewsRaw.id.in_(ordered_ids))
            )
            id_map = {r.id: r for r in raw_result.scalars().all()}
            items = [_raw_to_schema(id_map[i]) for i in ordered_ids if i in id_map]
        else:
            items = []

        response = NewsListResponse(
            items=items, total=raw_total, page=page,
            page_size=page_size, has_next=offset + page_size < raw_total,
        )
        await cache.set(cache_key, response.model_dump(), ttl=60)
        return response

    # ── Round-robin interleave by source ──────────────────────────────────
    # Always interleave by source unless this is a text search (relevance matters more).
    if not search:
        where_parts = []
        if category:
            where_parts.append(f"np.category = '{category}'")
        if country:
            where_parts.append(f"nr.source_country = '{country.upper()}'")
        where_clause_proc = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""

        sql = text(f"""
            WITH ranked AS (
                SELECT
                    np.id                AS np_id,
                    nr.published_at,
                    ROW_NUMBER() OVER (
                        PARTITION BY nr.source
                        ORDER BY nr.published_at DESC NULLS LAST
                    ) AS rn
                FROM news_processed np
                JOIN news_raw nr ON np.raw_id = nr.id
                {where_clause_proc}
            )
            SELECT np_id
            FROM ranked
            ORDER BY rn, published_at DESC NULLS LAST
            LIMIT :limit OFFSET :offset
        """)
        id_rows = (await db.execute(sql, {"limit": page_size, "offset": offset})).fetchall()
        ordered_ids = [r[0] for r in id_rows]

        if ordered_ids:
            result = await db.execute(
                select(NewsProcessed)
                .options(joinedload(NewsProcessed.raw))
                .where(NewsProcessed.id.in_(ordered_ids))
            )
            id_map = {p.id: p for p in result.scalars().all()}
            items = [_to_schema(id_map[i]) for i in ordered_ids if i in id_map]
        else:
            items = []
    else:
        q = (
            select(NewsProcessed)
            .join(NewsRaw, NewsProcessed.raw_id == NewsRaw.id)
            .options(joinedload(NewsProcessed.raw))
            .order_by(desc(NewsRaw.published_at))
        )
        for f in filters_processed:
            q = q.where(f)
        result = await db.execute(q.offset(offset).limit(page_size))
        items = [_to_schema(p) for p in result.scalars().all()]

    response = NewsListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_next=offset + page_size < total,
    )
    await cache.set(cache_key, response.model_dump(), ttl=settings.CACHE_TTL)
    return response


@router.get("/trending", response_model=list[TrendingTopic])
async def trending_topics(
    db: AsyncSession = Depends(get_db),
):
    cache_key = "news:trending"
    cached = await cache.get(cache_key)
    if cached:
        return cached

    result = await db.execute(
        select(NewsProcessed.category, func.count(NewsProcessed.id).label("cnt"))
        .group_by(NewsProcessed.category)
        .order_by(desc("cnt"))
        .limit(10)
    )
    rows = result.all()
    topics = [
        TrendingTopic(topic=row.category or "uncategorized", count=row.cnt, category=row.category)
        for row in rows
    ]
    await cache.set(cache_key, [t.model_dump() for t in topics], ttl=300)
    return topics


@router.get("/ai-search", response_model=NewsListResponse)
async def ai_search(
    request: Request,
    q: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: str | None = None,
    country: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """AI-powered search: expands query to synonyms in UZ/RU/EN then searches all."""
    await _check_rate_limit(request)

    cache_key = cache.make_key("news:ai-search", q.lower().strip(), f"p{page}", f"cat{category or ''}", f"co{country or ''}")
    cached = await cache.get(cache_key)
    if cached:
        return cached

    # Step 1: expand query with AI
    terms = await ai_service.expand_query(q)
    logger.info("AI search '%s' → %s", q, terms)

    offset = (page - 1) * page_size

    # Step 2: build OR conditions across all expanded terms (title + content + summary)
    filters_raw: list = []
    filters_proc: list = []
    for term in terms:
        like = f"%{term}%"
        filters_raw.append(NewsRaw.title.ilike(like) | NewsRaw.content.ilike(like))
        filters_proc.append(
            NewsRaw.title.ilike(like) | NewsProcessed.summary.ilike(like) | NewsRaw.content.ilike(like)
        )

    raw_or = or_(*filters_raw)
    proc_or = or_(*filters_proc)

    extra_filters: list = []
    if category:
        extra_filters.append(NewsProcessed.category == category)
    if country:
        extra_filters.append(NewsRaw.source_country == country.upper())

    # Try processed first
    count_q = select(func.count(NewsProcessed.id)).join(NewsRaw, NewsProcessed.raw_id == NewsRaw.id).where(proc_or)
    for f in extra_filters:
        count_q = count_q.where(f)
    total = (await db.execute(count_q)).scalar_one()

    if total > 0:
        q_stmt = (
            select(NewsProcessed)
            .join(NewsRaw, NewsProcessed.raw_id == NewsRaw.id)
            .options(joinedload(NewsProcessed.raw))
            .where(proc_or)
            .order_by(desc(NewsRaw.published_at))
        )
        for f in extra_filters:
            q_stmt = q_stmt.where(f)
        result = await db.execute(q_stmt.offset(offset).limit(page_size))
        items = [_to_schema(p) for p in result.scalars().all()]
    else:
        # Fallback to raw
        raw_extra: list = []
        if category:
            raw_extra.append(NewsRaw.hint_category == category)
        if country:
            raw_extra.append(NewsRaw.source_country == country.upper())

        raw_count_q = select(func.count(NewsRaw.id)).where(raw_or)
        for f in raw_extra:
            raw_count_q = raw_count_q.where(f)
        total = (await db.execute(raw_count_q)).scalar_one()

        raw_stmt = select(NewsRaw).where(raw_or).order_by(desc(NewsRaw.published_at))
        for f in raw_extra:
            raw_stmt = raw_stmt.where(f)
        result = await db.execute(raw_stmt.offset(offset).limit(page_size))
        items = [_raw_to_schema(r) for r in result.scalars().all()]

    response = NewsListResponse(
        items=items, total=total, page=page,
        page_size=page_size, has_next=offset + page_size < total,
    )
    await cache.set(cache_key, response.model_dump(), ttl=120)
    return response


@router.get("/{news_id}", response_model=NewsDetailSchema)
async def get_news(
    news_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await _check_rate_limit(request)

    cache_key = cache.make_key("news:detail", str(news_id))
    cached = await cache.get(cache_key)
    if cached:
        return cached

    result = await db.execute(
        select(NewsProcessed)
        .options(joinedload(NewsProcessed.raw))
        .where(NewsProcessed.id == news_id)
    )
    processed = result.scalar_one_or_none()

    if processed:
        schema = _to_schema(processed)
        detail = NewsDetailSchema(
            **schema.model_dump(),
            content=processed.raw.content if processed.raw else None,
        )
    else:
        # Fallback: try raw article by id
        raw = await db.get(NewsRaw, news_id)
        if not raw:
            raise HTTPException(status_code=404, detail="News not found")
        base = _raw_to_schema(raw)
        detail = NewsDetailSchema(**base.model_dump(), content=raw.content)

    await cache.set(cache_key, detail.model_dump(), ttl=settings.CACHE_TTL)
    return detail


@router.post("/generate", response_model=GenerateResponse)
async def generate_headlines(
    request: Request,
    body: GenerateRequest,
    db: AsyncSession = Depends(get_db),
):
    await _check_rate_limit(request)

    result = await ai_service.generate(body.text, body.language)
    if not result:
        raise HTTPException(status_code=503, detail="AI service unavailable")

    return GenerateResponse(
        summary=result.get("summary", ""),
        headlines=result.get("headlines", []),
        category=result.get("category", "world"),
        sentiment=result.get("sentiment", "neutral"),
        tags=result.get("tags", []),
    )


@router.post("/bookmarks", response_model=BookmarkSchema)
async def add_bookmark(
    body: BookmarkCreate,
    db: AsyncSession = Depends(get_db),
):
    exists = await db.execute(
        select(Bookmark).where(
            Bookmark.news_id == body.news_id,
            Bookmark.session_id == body.session_id,
        )
    )
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Already bookmarked")

    bm = Bookmark(news_id=body.news_id, session_id=body.session_id)
    db.add(bm)
    await db.commit()
    await db.refresh(bm)
    return bm


@router.get("/bookmarks/{session_id}", response_model=list[NewsProcessedSchema])
async def get_bookmarks(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(NewsRaw)
        .join(Bookmark, Bookmark.news_id == NewsRaw.id)
        .where(Bookmark.session_id == session_id)
        .order_by(desc(Bookmark.created_at))
    )
    raw_items = result.scalars().all()

    # For each raw item, check if there's a processed version
    schemas = []
    for raw in raw_items:
        proc_result = await db.execute(
            select(NewsProcessed)
            .options(joinedload(NewsProcessed.raw))
            .where(NewsProcessed.raw_id == raw.id)
        )
        processed = proc_result.scalar_one_or_none()
        if processed:
            schemas.append(_to_schema(processed))
        else:
            schemas.append(_raw_to_schema(raw))
    return schemas


@router.delete("/bookmarks/{session_id}/{news_id}", status_code=204)
async def remove_bookmark(
    session_id: str,
    news_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Bookmark).where(
            Bookmark.news_id == news_id,
            Bookmark.session_id == session_id,
        )
    )
    bm = result.scalar_one_or_none()
    if not bm:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    await db.delete(bm)
    await db.commit()
