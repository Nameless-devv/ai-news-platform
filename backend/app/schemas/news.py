from datetime import datetime
from pydantic import BaseModel, HttpUrl, field_validator


class NewsRawSchema(BaseModel):
    id: int
    source: str
    source_country: str
    title: str
    content: str | None
    url: str
    image_url: str | None
    published_at: datetime | None
    fetched_at: datetime
    is_processed: bool

    model_config = {"from_attributes": True}


class NewsProcessedSchema(BaseModel):
    id: int
    raw_id: int
    summary: str | None
    ai_headlines: list[str]
    category: str | None
    sentiment: str | None
    tags: list[str]
    processed_at: datetime

    # Joined raw fields
    source: str | None = None
    source_country: str | None = None
    title: str | None = None
    url: str | None = None
    image_url: str | None = None
    published_at: datetime | None = None

    model_config = {"from_attributes": True}


class NewsDetailSchema(NewsProcessedSchema):
    content: str | None = None


class NewsListResponse(BaseModel):
    items: list[NewsProcessedSchema]
    total: int
    page: int
    page_size: int
    has_next: bool


class GenerateRequest(BaseModel):
    text: str
    language: str = "uz"

    @field_validator("text")
    @classmethod
    def text_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("text cannot be empty")
        if len(v) > 10000:
            raise ValueError("text too long (max 10000 chars)")
        return v.strip()


class GenerateResponse(BaseModel):
    summary: str
    headlines: list[str]
    category: str
    sentiment: str
    tags: list[str]


class BookmarkCreate(BaseModel):
    news_id: int
    session_id: str


class BookmarkSchema(BaseModel):
    id: int
    news_id: int
    session_id: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TrendingTopic(BaseModel):
    topic: str
    count: int
    category: str | None = None
