from datetime import datetime
import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Company, MarketSnapshot
from app.scoring.market import score_market


def add_market_snapshot(db: Session, company: Company, *, price: float | None, previous_close: float | None,
                        volume: int | None, average_volume: int | None, provider: str = "manual") -> MarketSnapshot:
    change_percent = None
    if price is not None and previous_close:
        change_percent = (price - previous_close) / previous_close * 100.0
    relative_volume = None
    if volume is not None and average_volume:
        relative_volume = volume / average_volume
    dollar_volume = float(price or 0) * int(volume or 0)
    score = score_market(change_percent=change_percent, relative_volume=relative_volume, dollar_volume=dollar_volume)
    row = MarketSnapshot(company_id=company.id, observed_at=datetime.utcnow(), price=price,
                         previous_close=previous_close, change_percent=change_percent, volume=volume,
                         average_volume=average_volume, relative_volume=relative_volume,
                         dollar_volume=dollar_volume, score=score, provider=provider)
    db.add(row); db.commit(); db.refresh(row)
    return row


async def ingest_finnhub_quote(db: Session, company: Company) -> MarketSnapshot:
    if not settings.finnhub_api_key:
        raise RuntimeError("FINNHUB_API_KEY is not configured")
    async with httpx.AsyncClient(timeout=15) as client:
        q = await client.get("https://finnhub.io/api/v1/quote", params={"symbol": company.ticker, "token": settings.finnhub_api_key})
        q.raise_for_status(); data = q.json()
    price = float(data.get("c") or 0) or None
    previous_close = float(data.get("pc") or 0) or None
    return add_market_snapshot(db, company, price=price, previous_close=previous_close,
                               volume=None, average_volume=None, provider="finnhub")
