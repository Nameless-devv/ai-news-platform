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

# Static synonym dictionary: Uzbek/Russian/English ↔ expansions
QUERY_SYNONYMS: dict[str, list[str]] = {
    # Ta'lim / Education
    "talim":        ["education", "school", "university", "ta'lim", "talim", "maktab", "образование", "учеба"],
    "ta'lim":       ["education", "school", "university", "ta'lim", "talim", "maktab", "образование"],
    "maktab":       ["school", "maktab", "education", "ta'lim", "учеба", "класс"],
    "universitet":  ["university", "college", "institut", "вуз", "университет", "higher education"],
    "oliy ta'lim":  ["university", "college", "higher education", "вуз", "ta'lim"],
    "stipendiya":   ["scholarship", "grant", "stipend", "стипендия"],
    "imtihon":      ["exam", "test", "examination", "экзамен", "имтихон"],

    # Sog'liq / Health
    "salomatlik":   ["health", "medical", "sog'liq", "salomatlik", "здоровье", "медицина", "wellness"],
    "soglik":       ["health", "medical", "salomatlik", "здоровье", "медицина"],
    "sog'liq":      ["health", "medical", "salomatlik", "здоровье", "медицина"],
    "tibbiyot":     ["medical", "health", "medicine", "hospital", "медицина", "tibbiyot"],
    "kasallik":     ["disease", "illness", "virus", "infection", "болезнь", "эпидемия"],
    "koronavirus":  ["coronavirus", "covid", "pandemic", "вирус", "ковид"],
    "dori":         ["medicine", "drug", "pharmaceutical", "лекарство", "препарат"],
    "shifoxona":    ["hospital", "clinic", "больница", "клиника", "medical"],

    # Iqtisodiyot / Economy
    "iqtisodiyot":  ["economy", "economic", "finance", "GDP", "iqtisodiyot", "экономика", "бюджет"],
    "biznes":       ["business", "company", "firm", "бизнес", "компания", "корпорация"],
    "pul":          ["money", "currency", "cash", "деньги", "валюта", "финансы"],
    "narx":         ["price", "cost", "inflation", "narx", "цена", "инфляция"],
    "inflyatsiya":  ["inflation", "price", "cost", "нарх", "инфляция"],
    "byudjet":      ["budget", "finance", "spending", "бюджет", "финансирование"],
    "investitsiya": ["investment", "invest", "capital", "инвестиция", "капитал"],
    "bank":         ["bank", "banking", "finance", "банк", "кредит"],
    "ish":          ["work", "job", "employment", "labor", "работа", "занятость"],
    "ish o'rni":    ["job", "employment", "vacancy", "работа", "вакансия"],

    # Siyosat / Politics
    "siyosat":      ["politics", "political", "government", "policy", "siyosat", "политика", "власть"],
    "hukumat":      ["government", "cabinet", "ministry", "hukumat", "правительство", "власть"],
    "prezident":    ["president", "presidency", "leader", "президент", "глава"],
    "parlament":    ["parliament", "senate", "congress", "парламент", "олий мажлис"],
    "saylov":       ["election", "vote", "voting", "референдум", "выборы"],
    "vazir":        ["minister", "ministry", "cabinet", "министр", "правительство"],
    "qonun":        ["law", "legislation", "legal", "закон", "законодательство"],
    "davlat":       ["state", "government", "nation", "государство", "страна"],
    "diplomatiya":  ["diplomacy", "diplomatic", "foreign affairs", "дипломатия"],

    # Texnologiya / Technology
    "texnologiya":  ["technology", "tech", "digital", "innovation", "технологии", "texnologiya", "AI"],
    "texnolog":     ["technology", "tech", "digital", "технологии"],
    "sun'iy intellekt": ["AI", "artificial intelligence", "machine learning", "ChatGPT", "sun'iy intellekt"],
    "suniy intellekt":  ["AI", "artificial intelligence", "machine learning", "sun'iy intellekt"],
    "ai":           ["AI", "artificial intelligence", "ChatGPT", "GPT", "machine learning", "технологии"],
    "internet":     ["internet", "web", "online", "digital", "интернет"],
    "dastur":       ["software", "app", "application", "program", "программа", "приложение"],
    "ilovа":        ["app", "application", "software", "мобильный", "mobile"],
    "kompyuter":    ["computer", "PC", "laptop", "компьютер", "digital"],
    "telefon":      ["phone", "smartphone", "mobile", "телефон", "мобильный"],
    "kiberhujum":   ["cyberattack", "hacking", "cybersecurity", "кибератака", "хакер"],

    # Sport
    "futbol":       ["football", "soccer", "FIFA", "goal", "матч", "футбол", "futbol"],
    "sport":        ["sport", "sports", "athletic", "championship", "спорт", "соревнование"],
    "olimpiya":     ["olympics", "olympic", "olympiad", "Олимпиада", "Olympic Games"],
    "chempionat":   ["championship", "tournament", "league", "чемпионат", "турнир"],
    "basketbol":    ["basketball", "NBA", "баскетбол"],
    "tennis":       ["tennis", "ATP", "WTA", "теннис"],
    "boks":         ["boxing", "fight", "бокс", "поединок"],
    "yengil atletika": ["athletics", "running", "track", "лёгкая атлетика"],

    # Urush / Xavfsizlik
    "urush":        ["war", "conflict", "military", "war zone", "urush", "война", "военный"],
    "tinchlik":     ["peace", "ceasefire", "agreement", "мир", "перемирие", "договор"],
    "xavfsizlik":   ["security", "safety", "defense", "безопасность", "оборона"],
    "terrorchilik": ["terrorism", "terrorist", "attack", "теракт", "терроризм"],
    "qurolli":      ["armed", "military", "weapons", "вооружённый", "оружие"],
    "harbiy":       ["military", "army", "defense", "армия", "военный"],

    # Tabiat / Muhit
    "iqlim":        ["climate", "environment", "global warming", "weather", "климат", "экология"],
    "zilzila":      ["earthquake", "disaster", "tremor", "землетрясение", "стихия"],
    "suv toshqini": ["flood", "flooding", "disaster", "наводнение", "стихийное бедствие"],
    "ekologiya":    ["ecology", "environment", "climate", "экология", "окружающая среда"],
    "ob-havo":      ["weather", "climate", "forecast", "погода", "прогноз"],

    # Madaniyat / San'at
    "madaniyat":    ["culture", "cultural", "art", "tradition", "мадания", "культура", "искусство"],
    "musiqa":       ["music", "concert", "song", "album", "музыка", "концерт"],
    "kino":         ["film", "movie", "cinema", "кино", "фильм", "режиссер"],
    "san'at":       ["art", "artist", "exhibition", "искусство", "выставка"],
    "kitob":        ["book", "literature", "author", "книга", "литература"],

    # O'zbekiston joylari
    "uzbekiston":   ["uzbekistan", "o'zbekiston", "UZ", "узбекистан", "Ўзбекистон"],
    "o'zbekiston":  ["uzbekistan", "o'zbekiston", "UZ", "узбекистан"],
    "toshkent":     ["tashkent", "toshkent", "Ташкент", "capital"],
    "samarqand":    ["samarkand", "samarqand", "Самарканд"],
    "buxoro":       ["bukhara", "buxoro", "Бухара"],
    "farg'ona":     ["fergana", "farg'ona", "Фергана"],
    "namangan":     ["namangan", "Наманган"],
    "andijon":      ["andijan", "andijon", "Андижан"],

    # Rus so'zlari (kirilcha)
    "образование":  ["education", "school", "university", "ta'lim", "образование"],
    "экономика":    ["economy", "economic", "finance", "iqtisodiyot", "экономика"],
    "политика":     ["politics", "government", "policy", "siyosat", "политика"],
    "здоровье":     ["health", "medical", "salomatlik", "здоровье", "медицина"],
    "технологии":   ["technology", "tech", "AI", "texnologiya", "технологии"],
    "спорт":        ["sport", "sports", "athletic", "спорт", "чемпионат"],
    "война":        ["war", "conflict", "military", "urush", "война"],
    "безопасность": ["security", "safety", "xavfsizlik", "безопасность"],
    "наука":        ["science", "research", "ilm", "наука", "исследование"],
    "бизнес":       ["business", "company", "economy", "biznes", "бизнес"],
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
        """Expand search query into multilingual synonyms using static dictionary (no AI API needed)."""
        if not query or not query.strip():
            return [query]

        q = query.strip().lower()
        cache_key = cache.make_key("search", "expand", cache.hash_key(q))
        cached = await cache.get(cache_key)
        if cached:
            return cached

        terms: set[str] = {query.strip()}

        # Normalize: remove apostrophes for broader matching
        q_norm = q.replace("'", "").replace("'", "").replace("`", "")

        # 1. Exact match
        if q in QUERY_SYNONYMS:
            terms.update(QUERY_SYNONYMS[q])

        # 2. Normalized match (e.g. "sog'liq" → "soglik")
        if q_norm in QUERY_SYNONYMS:
            terms.update(QUERY_SYNONYMS[q_norm])

        # 3. Prefix match — "texnolog" matches "texnologiya"
        for key, synonyms in QUERY_SYNONYMS.items():
            key_norm = key.replace("'", "").replace("'", "")
            if key_norm.startswith(q_norm) or q_norm.startswith(key_norm):
                terms.update(synonyms)

        # 4. Multi-word: expand each token separately
        tokens = q.split()
        if len(tokens) > 1:
            for token in tokens:
                tok_norm = token.replace("'", "").replace("'", "")
                if token in QUERY_SYNONYMS:
                    terms.update(QUERY_SYNONYMS[token])
                elif tok_norm in QUERY_SYNONYMS:
                    terms.update(QUERY_SYNONYMS[tok_norm])
                else:
                    for key, synonyms in QUERY_SYNONYMS.items():
                        key_norm = key.replace("'", "").replace("'", "")
                        if key_norm == tok_norm or key_norm.startswith(tok_norm):
                            terms.update(synonyms)

        result = list(terms)[:10]
        await cache.set(cache_key, result, ttl=3600)
        logger.info("Query expanded '%s' → %s", query, result)
        return result

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
