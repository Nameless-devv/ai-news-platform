from datetime import datetime
from sqlalchemy import (
    Integer, String, Text, DateTime, ForeignKey,
    Boolean, JSON, Index, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class NewsRaw(Base):
    __tablename__ = "news_raw"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    source_country: Mapped[str] = mapped_column(String(10), default="UZ")
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str] = mapped_column(String(1000), nullable=False, unique=True)
    image_url: Mapped[str | None] = mapped_column(String(1000))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False)
    hint_category: Mapped[str | None] = mapped_column(String(50), nullable=True)

    processed: Mapped["NewsProcessed | None"] = relationship(
        "NewsProcessed", back_populates="raw", uselist=False
    )

    __table_args__ = (
        Index("ix_news_raw_source", "source"),
        Index("ix_news_raw_fetched_at", "fetched_at"),
        Index("ix_news_raw_is_processed", "is_processed"),
    )


class NewsProcessed(Base):
    __tablename__ = "news_processed"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    raw_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("news_raw.id", ondelete="CASCADE"), unique=True
    )
    summary: Mapped[str | None] = mapped_column(Text)
    ai_headlines: Mapped[list] = mapped_column(JSON, default=list)
    category: Mapped[str | None] = mapped_column(String(50))
    sentiment: Mapped[str | None] = mapped_column(String(20))
    tags: Mapped[list] = mapped_column(JSON, default=list)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    raw: Mapped["NewsRaw"] = relationship("NewsRaw", back_populates="processed")

    __table_args__ = (
        Index("ix_news_processed_category", "category"),
        Index("ix_news_processed_processed_at", "processed_at"),
    )


class Bookmark(Base):
    __tablename__ = "bookmarks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    news_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("news_raw.id", ondelete="CASCADE")
    )
    session_id: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    raw: Mapped["NewsRaw"] = relationship("NewsRaw")

    __table_args__ = (
        UniqueConstraint("news_id", "session_id", name="uq_bookmark_news_session"),
    )
