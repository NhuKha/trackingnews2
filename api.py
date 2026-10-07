from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field

class CompanyCreate(BaseModel):
    ticker: str; name: str; cik: str; exchange: str | None = None; sector: str | None = None
class CompanyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; ticker: str; name: str; cik: str; exchange: str | None; sector: str | None = None
class InsiderTransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; insider_name: str; officer_title: str | None; transaction_date: date | None; transaction_code: str | None
    shares: Decimal | None; price: Decimal | None; transaction_value: Decimal | None; acquired_or_disposed: str | None
    is_10b5_1: bool; score: float
class RadarItem(BaseModel):
    ticker: str; company_name: str; signal_score: float = 0; insider_score: float = 0; x_score: float = 0
    market_score: float = 0; news_score: float = 0; whale_score: float = 0; verification_score: float = 0
    level: str; summary: str | None = None; latest_activity: datetime | None = None
class MarketIn(BaseModel):
    price: float | None = None; previous_close: float | None = None; volume: int | None = None; average_volume: int | None = None
class SocialIn(BaseModel):
    mentions_1h: int = Field(ge=0); baseline_mentions_1h: float = Field(ge=0); unique_authors_1h: int = Field(ge=0)
    engagement_1h: int = Field(ge=0); sentiment: float = Field(default=50, ge=0, le=100)
class NewsIn(BaseModel):
    source: str; title: str; url: str; published_at: datetime; author: str | None = None; description: str | None = None
class WatchlistCreate(BaseModel): name: str
class AlertCreate(BaseModel):
    name: str; ticker: str | None = None; min_signal_score: float = 80; min_insider_score: float = 0
    min_market_score: float = 0; min_x_score: float = 0
