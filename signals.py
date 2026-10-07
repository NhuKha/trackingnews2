from datetime import datetime, timedelta
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Company, EventCluster, InsiderTransaction, MarketSnapshot, NewsArticle, SocialMetric, TickerSignal, WhaleFiling
from app.scoring.news import score_news
from app.scoring.signal import combine_signal_scores
from app.services.summary import deterministic_summary


def recompute_signal(db: Session, company: Company) -> TickerSignal:
    cutoff = datetime.utcnow() - timedelta(days=7)
    insider = float(db.scalar(select(func.max(InsiderTransaction.score)).where(InsiderTransaction.company_id == company.id,
                                                                               InsiderTransaction.created_at >= cutoff)) or 0)
    market = db.scalar(select(MarketSnapshot).where(MarketSnapshot.company_id == company.id).order_by(MarketSnapshot.observed_at.desc()).limit(1))
    social = db.scalar(select(SocialMetric).where(SocialMetric.company_id == company.id).order_by(SocialMetric.observed_at.desc()).limit(1))
    whale = float(db.scalar(select(func.max(WhaleFiling.score)).where(WhaleFiling.company_id == company.id,
                                                                       WhaleFiling.created_at >= cutoff)) or 0)
    creds = list(db.scalars(select(NewsArticle.credibility_score).where(NewsArticle.company_id == company.id,
                                                                        NewsArticle.published_at >= datetime.utcnow()-timedelta(days=2))).all())
    news = score_news([float(x) for x in creds])
    verification = float(db.scalar(select(func.max(EventCluster.verification_score)).where(EventCluster.company_id == company.id,
                                                                                              EventCluster.last_seen_at >= datetime.utcnow()-timedelta(days=2))) or 0)
    x_score = float(social.score if social else 0); market_score = float(market.score if market else 0)
    sentiment = float(social.sentiment if social else 50)
    total = combine_signal_scores(x_score=x_score, market_score=market_score, insider_score=insider,
                                  news_score=news, whale_score=whale, sentiment_score=sentiment,
                                  verification_score=verification)
    summary = deterministic_summary(company.ticker, signal_score=total, insider_score=insider, market_score=market_score,
                                    x_score=x_score, news_score=news, whale_score=whale, verification_score=verification)
    row = TickerSignal(company_id=company.id, signal_score=total, insider_score=insider, x_score=x_score,
                       market_score=market_score, news_score=news, whale_score=whale, sentiment_score=sentiment,
                       verification_score=verification, reason="evidence-weighted composite", summary=summary)
    db.add(row); db.commit(); db.refresh(row); return row
