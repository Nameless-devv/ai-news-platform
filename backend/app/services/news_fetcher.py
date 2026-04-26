import logging
import re
from datetime import datetime, timezone

import aiohttp
import feedparser

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}

RSS_SOURCES = [
    # ── O'zbekiston (O'zbek tili) ──────────────────────────
    {"url": "https://kun.uz/news/rss",          "source": "Kun.uz",          "country": "UZ", "category": None},
    {"url": "https://uza.uz/rss",               "source": "UzA",             "country": "UZ", "category": None},
    {"url": "https://gazeta.uz/uz/rss/",        "source": "Gazeta.uz (UZ)",  "country": "UZ", "category": None},
    {"url": "https://daryo.uz/feed/",           "source": "Daryo.uz",        "country": "UZ", "category": None},
    {"url": "https://anhor.uz/feed",            "source": "Anhor.uz",        "country": "UZ", "category": None},
    {"url": "https://uzreport.news/feed",       "source": "UzReport",        "country": "UZ", "category": None},

    # ── O'zbekiston (Rus tili) ─────────────────────────────
    {"url": "https://gazeta.uz/ru/rss/",        "source": "Gazeta.uz (RU)",  "country": "UZ", "category": None},
    {"url": "https://uza.uz/ru/rss",            "source": "UzA (RU)",        "country": "UZ", "category": None},
    {"url": "https://spot.uz/ru/rss/",          "source": "Spot.uz",         "country": "UZ", "category": None},

    # ── Dunyo — Umumiy yangiliklar ─────────────────────────
    {"url": "https://feeds.bbci.co.uk/news/world/rss.xml",           "source": "BBC World",    "country": "GLOBAL", "category": "world"},
    {"url": "https://www.aljazeera.com/xml/rss/all.xml",             "source": "Al Jazeera",   "country": "GLOBAL", "category": "world"},
    {"url": "https://www.theguardian.com/world/rss",                 "source": "The Guardian", "country": "GLOBAL", "category": "world"},
    {"url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml","source": "NY Times",     "country": "GLOBAL", "category": "world"},
    {"url": "https://feeds.npr.org/1001/rss.xml",                    "source": "NPR News",     "country": "GLOBAL", "category": "world"},
    {"url": "https://www.euronews.com/rss?format=mrss&level=theme&name=news", "source": "Euronews", "country": "GLOBAL", "category": "world"},

    # ── Texnologiya ────────────────────────────────────────
    {"url": "https://techcrunch.com/feed/",                           "source": "TechCrunch",      "country": "GLOBAL", "category": "technology"},
    {"url": "https://feeds.bbci.co.uk/news/technology/rss.xml",      "source": "BBC Tech",        "country": "GLOBAL", "category": "technology"},
    {"url": "https://www.theverge.com/rss/index.xml",                "source": "The Verge",       "country": "GLOBAL", "category": "technology"},
    {"url": "https://feeds.arstechnica.com/arstechnica/index",       "source": "Ars Technica",    "country": "GLOBAL", "category": "technology"},
    {"url": "https://www.wired.com/feed/rss",                        "source": "Wired",           "country": "GLOBAL", "category": "technology"},
    {"url": "https://www.technologyreview.com/feed/",                "source": "MIT Tech Review", "country": "GLOBAL", "category": "technology"},
    {"url": "https://feeds.feedburner.com/venturebeat/SZYF",         "source": "VentureBeat",     "country": "GLOBAL", "category": "technology"},
    {"url": "https://www.zdnet.com/news/rss.xml",                    "source": "ZDNet",           "country": "GLOBAL", "category": "technology"},
    {"url": "https://hnrss.org/frontpage",                           "source": "Hacker News",     "country": "GLOBAL", "category": "technology"},

    # ── Sport ──────────────────────────────────────────────
    {"url": "https://feeds.bbci.co.uk/sport/rss.xml",               "source": "BBC Sport",    "country": "GLOBAL", "category": "sports"},
    {"url": "https://feeds.bbci.co.uk/sport/football/rss.xml",      "source": "BBC Football", "country": "GLOBAL", "category": "sports"},
    {"url": "https://www.espn.com/espn/rss/news",                   "source": "ESPN",         "country": "GLOBAL", "category": "sports"},
    {"url": "https://www.skysports.com/rss/12040",                  "source": "Sky Sports",   "country": "GLOBAL", "category": "sports"},
    {"url": "https://api.foxsports.com/v1/rss",                     "source": "Fox Sports",   "country": "GLOBAL", "category": "sports"},
]


def _parse_date(entry: feedparser.FeedParserDict) -> datetime | None:
    for attr in ("published_parsed", "updated_parsed"):
        val = getattr(entry, attr, None)
        if val:
            try:
                return datetime(*val[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    return None


def _extract_image(entry: feedparser.FeedParserDict) -> str | None:
    if hasattr(entry, "media_content") and entry.media_content:
        url = entry.media_content[0].get("url")
        if url:
            return url
    if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
        url = entry.media_thumbnail[0].get("url")
        if url:
            return url
    if hasattr(entry, "enclosures") and entry.enclosures:
        enc = entry.enclosures[0]
        if enc.get("type", "").startswith("image/"):
            return enc.get("href") or enc.get("url")
    summary = getattr(entry, "summary", "") or ""
    m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', summary)
    if m:
        return m.group(1)
    return None


def _strip_html(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p>|</div>|</li>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = (text
            .replace("&nbsp;", " ").replace("&laquo;", "«").replace("&raquo;", "»")
            .replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
            .replace("&quot;", '"').replace("&#39;", "'").replace("&mdash;", "—")
            .replace("&ndash;", "–").replace("&hellip;", "…"))
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _extract_content(entry: feedparser.FeedParserDict) -> str | None:
    if hasattr(entry, "content") and entry.content:
        raw = entry.content[0].get("value", "")
    else:
        raw = getattr(entry, "summary", None) or ""
    cleaned = _strip_html(raw)
    return cleaned if cleaned else None


class NewsFetcher:
    def __init__(self, timeout: int = 20):
        self.timeout = aiohttp.ClientTimeout(total=timeout)

    async def fetch_feed(self, session: aiohttp.ClientSession, src: dict) -> list[dict]:
        url, source, country = src["url"], src["source"], src["country"]
        hint_category = src.get("category")
        results = []
        try:
            async with session.get(url, timeout=self.timeout, headers=HEADERS) as resp:
                if resp.status != 200:
                    logger.warning("Feed %s returned %s", source, resp.status)
                    return []
                raw = await resp.read()

            feed = feedparser.parse(raw)
            if not feed.entries:
                logger.warning("Feed %s has no entries", source)
                return []

            for entry in feed.entries[:50]:
                title = getattr(entry, "title", "").strip()
                link  = getattr(entry, "link",  "").strip()
                if not title or not link:
                    continue
                results.append({
                    "source":         source,
                    "source_country": country,
                    "title":          title[:500],
                    "content":        (_extract_content(entry) or "")[:6000] or None,
                    "url":            link[:1000],
                    "image_url":      _extract_image(entry),
                    "published_at":   _parse_date(entry),
                    "hint_category":  hint_category,
                })

            logger.info("Feed %s: %d articles", source, len(results))
        except Exception as e:
            logger.error("Error fetching %s (%s): %s", source, url, e)
        return results

    async def fetch_all(self):
        import asyncio
        connector = aiohttp.TCPConnector(limit=20, ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = [self.fetch_feed(session, src) for src in RSS_SOURCES]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            seen: set[str] = set()
            for batch in results:
                if isinstance(batch, Exception):
                    continue
                for item in batch:
                    url = item.get("url", "")
                    if url and url not in seen:
                        seen.add(url)
                        yield item


news_fetcher = NewsFetcher()
