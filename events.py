import re
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Company, EventCluster, NewsArticle

EVENT_WORDS = {
    "earnings": ["earnings", "revenue", "eps", "quarter"],
    "guidance": ["guidance", "forecast", "outlook"],
    "merger": ["merger", "acquire", "acquisition", "takeover"],
    "contract": ["contract", "award", "deal"],
    "regulatory": ["sec", "doj", "ftc", "fda", "regulator"],
    "lawsuit": ["lawsuit", "sues", "litigation"],
    "management_change": ["ceo", "cfo", "resigns", "appointed"],
}

def classify_event(text: str) -> str:
    t = text.lower()
    for kind, words in EVENT_WORDS.items():
        if any(w in t for w in words): return kind
    return "other"


def _tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 3}


def cluster_recent_news(db: Session, company: Company, hours: int = 48) -> dict:
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    articles = list(db.scalars(select(NewsArticle).where(NewsArticle.company_id == company.id,
                                                        NewsArticle.published_at >= cutoff).order_by(NewsArticle.published_at)).all())
    created = 0
    for a in articles:
        if a.event_cluster_id: continue
        kind = classify_event(a.title + " " + (a.description or ""))
        candidates = list(db.scalars(select(EventCluster).where(EventCluster.company_id == company.id,
                                                                 EventCluster.event_type == kind,
                                                                 EventCluster.last_seen_at >= cutoff)).all())
        match = None; at = _tokens(a.title)
        for c in candidates:
            ct = _tokens(c.title); union = len(at | ct) or 1
            if len(at & ct) / union >= 0.25: match = c; break
        if not match:
            match = EventCluster(company_id=company.id, event_type=kind, title=a.title,
                                 first_seen_at=a.published_at, last_seen_at=a.published_at)
            db.add(match); db.flush(); created += 1
        a.event_cluster_id = match.id
        match.last_seen_at = max(match.last_seen_at, a.published_at)
        same = list(db.scalars(select(NewsArticle).where(NewsArticle.event_cluster_id == match.id)).all())
        match.source_count = len(same)
        match.trusted_source_count = len([x for x in same if x.credibility_score >= 80])
        match.verification_score = min(100.0, max([x.credibility_score for x in same] or [0]) * 0.7 + match.trusted_source_count * 10)
        match.importance_score = min(100.0, 40 + match.trusted_source_count * 15 + len(same) * 4)
        match.status = "confirmed" if match.verification_score >= 80 else "developing" if match.verification_score >= 55 else "unverified"
    db.commit()
    return {"ticker": company.ticker, "clusters_created": created, "articles_processed": len(articles)}
