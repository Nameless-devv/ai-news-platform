import json
import logging
import re
from openai import AsyncOpenAI
from app.config import settings
from app.services.cache_service import cache

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a senior news editor for a multilingual platform covering Uzbekistan and global news.

Your job:
1. Write concise, accurate summaries — 2-3 sentences, no fluff
2. Generate 5 distinct headline variations — each with a different angle or tone
3. Headlines must be specific, factual, and compelling — NO clickbait, NO vague teasers
4. Pick the most precise category from the list
5. Detect sentiment from the article's overall tone
6. Extract 3-5 relevant keyword tags

Rules:
- Never invent facts not in the article
- Headlines must stand alone — reader understands the news without clicking
- Avoid starting headlines with "How", "Why", "What" question-bait patterns
- Respond ONLY with valid JSON — no markdown, no extra text"""

PROCESS_PROMPT = """Analyze this news article and return structured JSON.

SOURCE: {source}
TITLE: {title}

CONTENT:
{content}

Return this exact JSON structure:
{{
  "summary": "2-3 sentence factual summary covering who, what, where, when, why",
  "headlines": [
    "Headline 1 — straightforward news angle",
    "Headline 2 — focus on impact or consequence",
    "Headline 3 — focus on key person or organization",
    "Headline 4 — focus on numbers or specifics if present",
    "Headline 5 — broader context angle"
  ],
  "category": "one of: politics|economy|technology|sports|culture|health|world|society|environment|science",
  "sentiment": "positive|negative|neutral",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"]
}}"""

# Static fallback dictionary: common Uzbek/Russian → English synonyms
QUERY_SYNONYMS: dict[str, list[str]] = {
    # Ta'lim
    "talim": ["ta'lim", "talim", "education", "school", "university", "maktab", "образование"],
    "ta'lim": ["ta'lim", "talim", "education", "school", "university", "maktab", "образование"],
    "maktab": ["maktab", "school", "education", "ta'lim", "учеба"],
    "universitet": ["university", "universitet", "college", "вуз", "институт"],
    # Sog'liq
    "salomatlik": ["salomatlik", "health", "medical", "sog'liq", "здоровье", "медицина"],
    "sog'liq": ["sog'liq", "salomatlik", "health", "medical", "здоровье"],
    "tibbiyot": ["tibbiyot", "medical", "health", "medicine", "медицина"],
    "kasallik": ["kasallik", "disease", "illness", "virus", "болезнь"],
    # Iqtisodiyot
    "iqtisodiyot": ["iqtisodiyot", "economy", "economic", "finance", "экономика", "бизнес"],
    "biznes": ["biznes", "business", "economy", "компания", "firm"],
    "pul": ["pul", "money", "finance", "currency", "деньги"],
    "narx": ["narx", "price", "cost", "инфляция", "inflation"],
    # Siyosat
    "siyosat": ["siyosat", "politics", "political", "government", "политика"],
    "hukumat": ["hukumat", "government", "политика", "власть", "president"],
    "prezident": ["president", "prezident", "presidency", "president"],
    # Texnologiya
    "texnologiya": ["texnologiya", "technology", "tech", "технологии", "AI", "digital"],
    "sun'iy intellekt": ["AI", "artificial intelligence", "machine learning", "sun'iy intellekt"],
    "ai": ["AI", "artificial intelligence", "ChatGPT", "sun'iy intellekt", "технологии"],
    "dastur": ["software", "app", "dastur", "программа", "application"],
    # Sport
    "futbol": ["futbol", "football", "soccer", "FIFA", "матч"],
    "sport": ["sport", "sports", "athletic", "спорт", "championship"],
    "olimpiya": ["olympics", "olympic", "olimpiya", "Олимпиада"],
    # Urush / xavfsizlik
    "urush": ["urush", "war", "conflict", "военный", "война"],
    "tinchlik": ["tinchlik", "peace", "мир", "договор", "agreement"],
    "xavfsizlik": ["xavfsizlik", "security", "безопасность", "safety"],
    # Tabiat / ekologiya
    "iqlim": ["iqlim", "climate", "environment", "weather", "климат"],
    "zilzila": ["zilzila", "earthquake", "natural disaster", "землетрясение"],
    # Madaniyat
    "madaniyat": ["madaniyat", "culture", "cultural", "art", "культура"],
    "musiqa": ["musiqa", "music", "concert", "музыка"],
    "kino": ["kino", "film", "movie", "cinema", "фильм"],
    # O'zbekiston
    "uzbekiston": ["uzbekistan", "o'zbekiston", "Uzbekistán", "узбекистан"],
    "o'zbekiston": ["uzbekistan", "o'zbekiston", "узбекистан"],
    "toshkent": ["tashkent", "toshkent", "Ташкент"],
    # Rus so'zlari
    "образование": ["education", "school", "university", "ta'lim", "образование"],
    "экономика": ["economy", "economic", "iqtisodiyot", "экономика"],
    "политика": ["politics", "government", "siyosat", "политика"],
    "здоровье": ["health", "medical", "salomatlik", "здоровье"],
    "технологии": ["technology", "tech", "texnologiya", "технологии"],
    "спорт": ["sport", "sports", "спорт", "athletic"],
}


SEARCH_EXPAND_PROMPT = """You are a multilingual search query expander for a news platform covering Uzbekistan and global news.

Given a search query in ANY language (Uzbek, Russian, English, or others), return synonyms and translations that will help find relevant news articles.

Rules:
- Always include the original query
- Include Uzbek, Russian, AND English translations/synonyms
- Include common related terms journalists would use
- Max 8 terms total, keep them short (1-2 words each)
- No duplicates, no phrases longer than 3 words

Query: {query}

Return ONLY this JSON:
{{"terms": ["term1", "term2", "term3", "term4", "term5"]}}"""


GENERATE_PROMPT = """Generate news content for the following text.
Language hint: {language}

TEXT:
{text}

Return this exact JSON structure:
{{
  "summary": "2-3 sentence factual summary",
  "headlines": [
    "Headline 1 — main news angle",
    "Headline 2 — impact angle",
    "Headline 3 — context angle"
  ],
  "category": "one of: politics|economy|technology|sports|culture|health|world|society|environment|science",
  "sentiment": "positive|negative|neutral",
  "tags": ["tag1", "tag2", "tag3"]
}}"""


def _clean_html(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = (text
            .replace("&nbsp;", " ").replace("&laquo;", "«").replace("&raquo;", "»")
            .replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
            .replace("&quot;", '"').replace("&#39;", "'").replace("&mdash;", "—")
            .replace("&ndash;", "–").replace("&hellip;", "…"))
    return re.sub(r"\s{2,}", " ", text).strip()


class AIService:
    def __init__(self):
        self._client: AsyncOpenAI | None = None

    def client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_BASE_URL,
            )
        return self._client

    async def process_article(self, title: str, content: str | None, source: str = "") -> dict | None:
        clean_title = _clean_html(title)
        clean_content = _clean_html(content or "")

        cache_key = cache.make_key("ai", "article", cache.hash_key(clean_title + clean_content[:200]))
        cached = await cache.get(cache_key)
        if cached:
            return cached

        prompt = PROCESS_PROMPT.format(
            source=source or "Unknown",
            title=clean_title,
            content=clean_content[:4000],
        )

        try:
            response = await self.client().chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=1000,
                response_format={"type": "json_object"},
            )
            result = json.loads(response.choices[0].message.content)

            # Validate structure
            result.setdefault("headlines", [])
            result.setdefault("tags", [])
            result.setdefault("summary", "")
            result.setdefault("category", "world")
            result.setdefault("sentiment", "neutral")

            await cache.set(cache_key, result, ttl=7200)
            return result
        except Exception as e:
            logger.error("AI processing failed for '%s': %s", clean_title[:60], e)
            return None

    async def expand_query(self, query: str) -> list[str]:
        """Expand search query into multilingual synonyms. Falls back to static dict if AI unavailable."""
        if not query or not query.strip():
            return [query]

        q = query.strip().lower()
        cache_key = cache.make_key("ai", "search", cache.hash_key(q))
        cached = await cache.get(cache_key)
        if cached:
            return cached

        # Static dictionary lookup first (instant, no API needed)
        static_terms = QUERY_SYNONYMS.get(q)

        try:
            response = await self.client().chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "user", "content": SEARCH_EXPAND_PROMPT.format(query=query.strip())}],
                temperature=0.1,
                max_tokens=150,
                response_format={"type": "json_object"},
            )
            data = json.loads(response.choices[0].message.content)
            terms = [t.strip() for t in data.get("terms", []) if t.strip()]
            if query.strip() not in terms:
                terms.insert(0, query.strip())
            terms = terms[:8]
            await cache.set(cache_key, terms, ttl=3600)
            return terms
        except Exception as e:
            logger.warning("Query expansion failed for '%s': %s", query, e)
            # Use static dict if available, otherwise original term
            if static_terms:
                await cache.set(cache_key, static_terms, ttl=3600)
                return static_terms
            return [query.strip()]

    async def generate(self, text: str, language: str = "uz") -> dict | None:
        clean = _clean_html(text)
        cache_key = cache.make_key("ai", "generate", language, cache.hash_key(clean))
        cached = await cache.get(cache_key)
        if cached:
            return cached

        prompt = GENERATE_PROMPT.format(text=clean[:4000], language=language)

        try:
            response = await self.client().chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=700,
                response_format={"type": "json_object"},
            )
            result = json.loads(response.choices[0].message.content)
            result.setdefault("headlines", [])
            result.setdefault("tags", [])

            await cache.set(cache_key, result, ttl=3600)
            return result
        except Exception as e:
            logger.error("AI generation failed: %s", e)
            return None


ai_service = AIService()
