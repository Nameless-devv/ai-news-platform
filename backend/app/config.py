from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    APP_NAME: str = "AI News Platform"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@db:5432/ainews"
    DATABASE_SYNC_URL: str = "postgresql://postgres:postgres@db:5432/ainews"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # Celery
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"

    # AI (OpenAI yoki Grok)
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.x.ai/v1"   # Grok: https://api.x.ai/v1 | OpenAI: https://api.openai.com/v1
    OPENAI_MODEL: str = "grok-3-mini"               # Grok: grok-3-mini | OpenAI: gpt-4o-mini

    # News fetching
    FETCH_INTERVAL_MINUTES: int = 5
    MAX_ARTICLES_PER_SOURCE: int = 20

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    # Cache TTL seconds
    CACHE_TTL: int = 300

    # CORS
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "http://frontend:3000"]

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
