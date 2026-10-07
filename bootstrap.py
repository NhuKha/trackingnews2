import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.config import settings
from app.models import Company


async def bootstrap_sec_companies(db: Session, limit: int = 1000) -> dict:
    headers = {"User-Agent": settings.sec_user_agent, "Accept-Encoding": "gzip, deflate"}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get("https://www.sec.gov/files/company_tickers.json", headers=headers)
        r.raise_for_status(); payload = r.json()
    inserted = 0
    for item in list(payload.values())[:limit]:
        ticker = str(item.get("ticker", "")).upper().strip()
        cik = str(item.get("cik_str", "")).zfill(10)
        if not ticker or not cik: continue
        if db.scalar(select(Company.id).where((Company.ticker == ticker) | (Company.cik == cik))): continue
        db.add(Company(ticker=ticker, name=item.get("title") or ticker, cik=cik)); inserted += 1
    db.commit()
    return {"inserted": inserted, "considered": min(limit, len(payload))}
