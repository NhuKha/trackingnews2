from datetime import datetime, timedelta, timezone
import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Company, SocialMetric, XPost
from app.scoring.social import score_social


def _sentiment(text: str) -> float:
    t = text.lower()
    pos = sum(w in t for w in ["beat", "bull", "buy", "growth", "record", "surge", "strong", "upgrade"])
    neg = sum(w in t for w in ["miss", "bear", "sell", "fraud", "cut", "weak", "downgrade", "lawsuit"])
    return max(0.0, min(100.0, 50 + (pos-neg)*8))


def recompute_social_metric(db: Session, company: Company, baseline_mentions_1h: float | None = None) -> SocialMetric:
    cutoff = datetime.utcnow() - timedelta(hours=1)
    posts = list(db.scalars(select(XPost).where(XPost.company_id == company.id, XPost.created_at >= cutoff)).all())
    mentions = len(posts)
    unique_authors = len({p.author_id or p.author_username or str(p.id) for p in posts})
    engagement = sum(p.likes + p.reposts + p.replies + p.quotes for p in posts)
    sentiment = sum(p.sentiment for p in posts) / mentions if mentions else 50.0
    if baseline_mentions_1h is None:
        historical = db.scalar(select(func.avg(SocialMetric.mentions_1h)).where(SocialMetric.company_id == company.id))
        baseline_mentions_1h = float(historical or max(1, mentions))
    score = score_social(mentions_1h=mentions, baseline_mentions_1h=baseline_mentions_1h,
                         unique_authors_1h=unique_authors, engagement_1h=engagement, sentiment=sentiment)
    metric = SocialMetric(company_id=company.id, mentions_1h=mentions, baseline_mentions_1h=baseline_mentions_1h,
                          unique_authors_1h=unique_authors, engagement_1h=engagement, sentiment=sentiment, score=score)
    db.add(metric); db.commit(); db.refresh(metric)
    return metric


async def ingest_x_recent(db: Session, company: Company, max_results: int = 25) -> dict:
    if not settings.x_bearer_token:
        raise RuntimeError("X_BEARER_TOKEN is not configured")
    query = f'("${company.ticker}" OR "{company.ticker}") -is:retweet lang:en'
    params = {"query": query, "max_results": max(10, min(100, max_results)),
              "tweet.fields": "created_at,public_metrics,author_id", "expansions": "author_id",
              "user.fields": "username,public_metrics,verified"}
    headers = {"Authorization": f"Bearer {settings.x_bearer_token}"}
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get("https://api.x.com/2/tweets/search/recent", params=params, headers=headers)
        r.raise_for_status(); payload = r.json()
    users = {u["id"]: u for u in payload.get("includes", {}).get("users", [])}
    inserted = 0
    for item in payload.get("data", []):
        if db.scalar(select(XPost).where(XPost.post_id == item["id"])):
            continue
        u = users.get(item.get("author_id"), {})
        pm = item.get("public_metrics", {})
        upm = u.get("public_metrics", {})
        created = datetime.fromisoformat(item["created_at"].replace("Z", "+00:00")).replace(tzinfo=None)
        row = XPost(company_id=company.id, post_id=item["id"], author_id=item.get("author_id"),
                    author_username=u.get("username"), text=item.get("text", ""), created_at=created,
                    likes=pm.get("like_count", 0), reposts=pm.get("retweet_count", 0), replies=pm.get("reply_count", 0),
                    quotes=pm.get("quote_count", 0), followers=upm.get("followers_count"), verified=bool(u.get("verified", False)),
                    sentiment=_sentiment(item.get("text", "")), credibility=75.0 if u.get("verified") else 50.0)
        db.add(row); inserted += 1
    db.commit()
    metric = recompute_social_metric(db, company)
    return {"ticker": company.ticker, "posts_inserted": inserted, "x_score": metric.score}
