from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticker: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    cik: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    exchange: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    sector: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SecFiling(Base):
    __tablename__ = "sec_filings"
    __table_args__ = (UniqueConstraint("accession_number", name="uq_sec_accession"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    accession_number: Mapped[str] = mapped_column(String(32), index=True)
    form_type: Mapped[str] = mapped_column(String(16), index=True)
    filing_date: Mapped[date] = mapped_column(Date)
    primary_document: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source_url: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    company: Mapped[Company] = relationship()


class InsiderTransaction(Base):
    __tablename__ = "insider_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    filing_id: Mapped[int] = mapped_column(ForeignKey("sec_filings.id"), index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    insider_name: Mapped[str] = mapped_column(String(255))
    insider_cik: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    is_director: Mapped[bool] = mapped_column(Boolean, default=False)
    is_officer: Mapped[bool] = mapped_column(Boolean, default=False)
    is_ten_percent_owner: Mapped[bool] = mapped_column(Boolean, default=False)
    officer_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    transaction_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    security_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    transaction_code: Mapped[Optional[str]] = mapped_column(String(8), nullable=True, index=True)
    shares: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 6), nullable=True)
    price: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 6), nullable=True)
    transaction_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(24, 2), nullable=True)
    acquired_or_disposed: Mapped[Optional[str]] = mapped_column(String(1), nullable=True)
    ownership_type: Mapped[Optional[str]] = mapped_column(String(1), nullable=True)
    shares_owned_after: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 6), nullable=True)
    is_10b5_1: Mapped[bool] = mapped_column(Boolean, default=False)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    filing: Mapped[SecFiling] = relationship()
    company: Mapped[Company] = relationship()


class WhaleFiling(Base):
    __tablename__ = "whale_filings"
    __table_args__ = (UniqueConstraint("accession_number", name="uq_whale_accession"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    accession_number: Mapped[str] = mapped_column(String(32), index=True)
    form_type: Mapped[str] = mapped_column(String(16), index=True)
    filing_date: Mapped[date] = mapped_column(Date)
    filer_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ownership_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    source_url: Mapped[str] = mapped_column(Text)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MarketSnapshot(Base):
    __tablename__ = "market_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    previous_close: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    change_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    volume: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    average_volume: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    relative_volume: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    dollar_volume: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    provider: Mapped[str] = mapped_column(String(64), default="manual")


class XPost(Base):
    __tablename__ = "x_posts"
    __table_args__ = (UniqueConstraint("post_id", name="uq_x_post_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    post_id: Mapped[str] = mapped_column(String(64), index=True)
    author_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    author_username: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    likes: Mapped[int] = mapped_column(Integer, default=0)
    reposts: Mapped[int] = mapped_column(Integer, default=0)
    replies: Mapped[int] = mapped_column(Integer, default=0)
    quotes: Mapped[int] = mapped_column(Integer, default=0)
    followers: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    sentiment: Mapped[float] = mapped_column(Float, default=50.0)
    credibility: Mapped[float] = mapped_column(Float, default=50.0)


class SocialMetric(Base):
    __tablename__ = "social_metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    mentions_1h: Mapped[int] = mapped_column(Integer, default=0)
    baseline_mentions_1h: Mapped[float] = mapped_column(Float, default=0.0)
    unique_authors_1h: Mapped[int] = mapped_column(Integer, default=0)
    engagement_1h: Mapped[int] = mapped_column(Integer, default=0)
    sentiment: Mapped[float] = mapped_column(Float, default=50.0)
    score: Mapped[float] = mapped_column(Float, default=0.0)


class NewsArticle(Base):
    __tablename__ = "news_articles"
    __table_args__ = (UniqueConstraint("url", name="uq_news_url"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    source: Mapped[str] = mapped_column(String(128), index=True)
    source_tier: Mapped[str] = mapped_column(String(16), default="D")
    title: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text)
    published_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    author: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    credibility_score: Mapped[float] = mapped_column(Float, default=50.0)
    sentiment: Mapped[float] = mapped_column(Float, default=50.0)
    event_cluster_id: Mapped[Optional[int]] = mapped_column(ForeignKey("event_clusters.id"), nullable=True, index=True)


class EventCluster(Base):
    __tablename__ = "event_clusters"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(64), default="other", index=True)
    title: Mapped[str] = mapped_column(Text)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    source_count: Mapped[int] = mapped_column(Integer, default=0)
    trusted_source_count: Mapped[int] = mapped_column(Integer, default=0)
    x_post_count: Mapped[int] = mapped_column(Integer, default=0)
    importance_score: Mapped[float] = mapped_column(Float, default=0.0)
    verification_score: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(32), default="unverified")


class TickerSignal(Base):
    __tablename__ = "ticker_signals"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    signal_score: Mapped[float] = mapped_column(Float, default=0.0)
    insider_score: Mapped[float] = mapped_column(Float, default=0.0)
    x_score: Mapped[float] = mapped_column(Float, default=0.0)
    market_score: Mapped[float] = mapped_column(Float, default=0.0)
    news_score: Mapped[float] = mapped_column(Float, default=0.0)
    whale_score: Mapped[float] = mapped_column(Float, default=0.0)
    sentiment_score: Mapped[float] = mapped_column(Float, default=50.0)
    verification_score: Mapped[float] = mapped_column(Float, default=0.0)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    company: Mapped[Company] = relationship()


class Watchlist(Base):
    __tablename__ = "watchlists"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"
    __table_args__ = (UniqueConstraint("watchlist_id", "company_id", name="uq_watchlist_company"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    watchlist_id: Mapped[int] = mapped_column(ForeignKey("watchlists.id"), index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AlertRule(Base):
    __tablename__ = "alert_rules"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    ticker: Mapped[Optional[str]] = mapped_column(String(16), nullable=True, index=True)
    min_signal_score: Mapped[float] = mapped_column(Float, default=80.0)
    min_insider_score: Mapped[float] = mapped_column(Float, default=0.0)
    min_market_score: Mapped[float] = mapped_column(Float, default=0.0)
    min_x_score: Mapped[float] = mapped_column(Float, default=0.0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
