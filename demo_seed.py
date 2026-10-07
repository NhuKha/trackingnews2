from datetime import datetime
from sqlalchemy import select
from app.db import Base, SessionLocal, engine
from app.models import Company, SocialMetric
from app.services.market import add_market_snapshot
from app.services.news import add_news_article
from app.services.events import cluster_recent_news
from app.services.signals import recompute_signal
from app.scoring.social import score_social

Base.metadata.create_all(bind=engine)
db=SessionLocal()
try:
    c=db.scalar(select(Company).where(Company.ticker=="DEMO"))
    if not c:
        c=Company(ticker="DEMO",name="Demo Signal Corp",cik="9999999999",exchange="NASDAQ")
        db.add(c);db.commit();db.refresh(c)
    add_market_snapshot(db,c,price=52.5,previous_close=49.0,volume=3_200_000,average_volume=1_100_000,provider="demo")
    social=dict(mentions_1h=640,baseline_mentions_1h=120,unique_authors_1h=410,engagement_1h=8800,sentiment=72)
    db.add(SocialMetric(company_id=c.id,score=score_social(**social),**social));db.commit()
    add_news_article(db,c,source="Reuters",title="Demo company announces major contract",url="https://example.com/demo-reuters",published_at=datetime.utcnow(),description="Demo trusted-news record used only for local testing.")
    add_news_article(db,c,source="Company IR",title="Demo company confirms major contract",url="https://example.com/demo-ir",published_at=datetime.utcnow(),description="Demo primary-source confirmation.")
    cluster_recent_news(db,c)
    s=recompute_signal(db,c)
    print({"ticker":c.ticker,"signal_score":s.signal_score,"summary":s.summary})
finally:
    db.close()
