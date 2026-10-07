from datetime import datetime, timedelta
import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Company, NewsArticle
from app.scoring.news import source_credibility, source_tier


def add_news_article(db: Session, company: Company, *, source: str, title: str, url: str,
                     published_at: datetime, author: str | None = None, description: str | None = None) -> NewsArticle:
    existing = db.scalar(select(NewsArticle).where(NewsArticle.url == url))
    if existing:
        return existing
    cred = source_credibility(source)
    row = NewsArticle(company_id=company.id, source=source, source_tier=source_tier(cred), title=title, url=url,
                      published_at=published_at, author=author, description=description, credibility_score=cred)
    db.add(row); db.commit(); db.refresh(row)
    return row


async def ingest_newsapi(db: Session, company: Company, page_size: int = 25) -> dict:
    if not settings.newsapi_key:
        raise RuntimeError("NEWSAPI_KEY is not configured")
    params = {"q": f'"{company.name}" OR {company.ticker}', "language": "en", "sortBy": "publishedAt",
              "pageSize": min(100, page_size), "from": (datetime.utcnow()-timedelta(days=2)).date().isoformat(),
              "apiKey": settings.newsapi_key}
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get("https://newsapi.org/v2/everything", params=params); r.raise_for_status(); payload = r.json()
    inserted = 0
    for a in payload.get("articles", []):
        if not a.get("url") or not a.get("title") or not a.get("publishedAt"):
            continue
        before = db.scalar(select(NewsArticle.id).where(NewsArticle.url == a["url"]))
        add_news_article(db, company, source=(a.get("source") or {}).get("name") or "Unknown", title=a["title"], url=a["url"],
                         published_at=datetime.fromisoformat(a["publishedAt"].replace("Z", "+00:00")).replace(tzinfo=None),
                         author=a.get("author"), description=a.get("description"))
        if not before: inserted += 1
    return {"ticker": company.ticker, "articles_inserted": inserted}
