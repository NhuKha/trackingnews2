from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import AlertRule, Company, EventCluster, InsiderTransaction, MarketSnapshot, NewsArticle, SocialMetric, TickerSignal, Watchlist, WatchlistItem, WhaleFiling
from app.schemas.api import AlertCreate, CompanyCreate, CompanyOut, InsiderTransactionOut, MarketIn, NewsIn, RadarItem, SocialIn, WatchlistCreate
from app.scoring.signal import signal_level
from app.scoring.social import score_social
from app.services.bootstrap import bootstrap_sec_companies
from app.services.events import cluster_recent_news
from app.services.market import add_market_snapshot, ingest_finnhub_quote
from app.services.news import add_news_article, ingest_newsapi
from app.services.sec_ingest import ingest_recent_form4, ingest_recent_whales
from app.services.signals import recompute_signal
from app.services.social import ingest_x_recent
from app.services.summary import ai_summary
from app.config import settings

router = APIRouter(prefix="/api/v1")

def company_or_404(db: Session, ticker: str) -> Company:
    c = db.scalar(select(Company).where(Company.ticker == ticker.upper()))
    if not c: raise HTTPException(404, "Ticker not found. Add/bootstrap it first.")
    return c

@router.get("/health")
def health(): return {"status":"ok", "version":"0.3.0"}

@router.post("/companies", response_model=CompanyOut)
def create_company(body: CompanyCreate, db: Session=Depends(get_db)):
    ticker=body.ticker.upper().strip(); cik=body.cik.zfill(10)
    existing=db.scalar(select(Company).where((Company.ticker==ticker)|(Company.cik==cik)))
    if existing: return existing
    c=Company(ticker=ticker,name=body.name,cik=cik,exchange=body.exchange,sector=body.sector); db.add(c); db.commit(); db.refresh(c); return c

@router.get("/companies", response_model=list[CompanyOut])
def list_companies(db: Session=Depends(get_db)): return list(db.scalars(select(Company).order_by(Company.ticker)).all())

@router.post("/bootstrap/sec-companies")
async def bootstrap(limit:int=Query(1000,ge=1,le=10000),db:Session=Depends(get_db)): return await bootstrap_sec_companies(db,limit)

@router.post("/ingest/sec/{ticker}")
async def ingest_sec(ticker:str,limit:int=Query(20,ge=1,le=100),db:Session=Depends(get_db)): return await ingest_recent_form4(db,company_or_404(db,ticker),limit)

@router.post("/ingest/whales/{ticker}")
async def ingest_whales(ticker:str,limit:int=Query(20,ge=1,le=100),db:Session=Depends(get_db)): return await ingest_recent_whales(db,company_or_404(db,ticker),limit)

@router.post("/ingest/x/{ticker}")
async def ingest_x(ticker:str,max_results:int=Query(25,ge=10,le=100),db:Session=Depends(get_db)):
    try: return await ingest_x_recent(db,company_or_404(db,ticker),max_results)
    except RuntimeError as e: raise HTTPException(400,str(e))

@router.post("/ingest/news/{ticker}")
async def ingest_news(ticker:str,page_size:int=Query(25,ge=1,le=100),db:Session=Depends(get_db)):
    try: return await ingest_newsapi(db,company_or_404(db,ticker),page_size)
    except RuntimeError as e: raise HTTPException(400,str(e))

@router.post("/ingest/market/{ticker}/finnhub")
async def ingest_market(ticker:str,db:Session=Depends(get_db)):
    try: return await ingest_finnhub_quote(db,company_or_404(db,ticker))
    except RuntimeError as e: raise HTTPException(400,str(e))

@router.post("/manual/market/{ticker}")
def manual_market(ticker:str,body:MarketIn,db:Session=Depends(get_db)): return add_market_snapshot(db,company_or_404(db,ticker),**body.model_dump())

@router.post("/manual/social/{ticker}")
def manual_social(ticker:str,body:SocialIn,db:Session=Depends(get_db)):
    c=company_or_404(db,ticker); d=body.model_dump(); score=score_social(**d)
    row=SocialMetric(company_id=c.id,score=score,**d); db.add(row); db.commit(); db.refresh(row); return row

@router.post("/manual/news/{ticker}")
def manual_news(ticker:str,body:NewsIn,db:Session=Depends(get_db)): return add_news_article(db,company_or_404(db,ticker),**body.model_dump())

@router.post("/events/{ticker}/cluster")
def cluster(ticker:str,db:Session=Depends(get_db)): return cluster_recent_news(db,company_or_404(db,ticker))

@router.post("/signals/{ticker}/recompute")
def recompute(ticker:str,db:Session=Depends(get_db)): return recompute_signal(db,company_or_404(db,ticker))


@router.post("/refresh/{ticker}")
async def refresh_ticker(ticker:str,db:Session=Depends(get_db)):
    c=company_or_404(db,ticker); steps={}
    try: steps["sec"] = await ingest_recent_form4(db,c,20)
    except Exception as e: steps["sec"]={"error":str(e)}
    try: steps["whales"] = await ingest_recent_whales(db,c,20)
    except Exception as e: steps["whales"]={"error":str(e)}
    if settings.x_bearer_token:
        try: steps["x"] = await ingest_x_recent(db,c,25)
        except Exception as e: steps["x"]={"error":str(e)}
    if settings.newsapi_key:
        try: steps["news"] = await ingest_newsapi(db,c,25)
        except Exception as e: steps["news"]={"error":str(e)}
    if settings.finnhub_api_key:
        try: steps["market"] = {"id":(await ingest_finnhub_quote(db,c)).id}
        except Exception as e: steps["market"]={"error":str(e)}
    steps["events"] = cluster_recent_news(db,c)
    signal = recompute_signal(db,c)
    return {"ticker":c.ticker,"steps":steps,"signal_score":signal.signal_score,"summary":signal.summary}

@router.post("/signals/{ticker}/ai-summary")
async def generate_ai_summary(ticker:str,db:Session=Depends(get_db)):
    c=company_or_404(db,ticker)
    s=db.scalar(select(TickerSignal).where(TickerSignal.company_id==c.id).order_by(TickerSignal.generated_at.desc()).limit(1))
    if not s: s=recompute_signal(db,c)
    articles=list(db.scalars(select(NewsArticle).where(NewsArticle.company_id==c.id).order_by(NewsArticle.published_at.desc()).limit(8)).all())
    evidence={"ticker":c.ticker,"signal_score":s.signal_score,"x_score":s.x_score,"market_score":s.market_score,"insider_score":s.insider_score,"news_score":s.news_score,"whale_score":s.whale_score,"verification_score":s.verification_score,"recent_news":[{"source":a.source,"title":a.title} for a in articles]}
    text=await ai_summary(str(evidence))
    if not text: return {"summary":s.summary,"provider":"deterministic","note":"Set OPENAI_API_KEY to enable AI summaries."}
    s.summary=text; db.commit(); return {"summary":text,"provider":"openai"}

@router.get("/stocks/{ticker}/insiders",response_model=list[InsiderTransactionOut])
def insiders(ticker:str,limit:int=Query(50,ge=1,le=500),db:Session=Depends(get_db)):
    c=company_or_404(db,ticker); return list(db.scalars(select(InsiderTransaction).where(InsiderTransaction.company_id==c.id).order_by(InsiderTransaction.transaction_date.desc()).limit(limit)).all())

@router.get("/stocks/{ticker}/snapshot")
def snapshot(ticker:str,db:Session=Depends(get_db)):
    c=company_or_404(db,ticker)
    return {"company":c,"signal":db.scalar(select(TickerSignal).where(TickerSignal.company_id==c.id).order_by(TickerSignal.generated_at.desc()).limit(1)),
            "market":db.scalar(select(MarketSnapshot).where(MarketSnapshot.company_id==c.id).order_by(MarketSnapshot.observed_at.desc()).limit(1)),
            "social":db.scalar(select(SocialMetric).where(SocialMetric.company_id==c.id).order_by(SocialMetric.observed_at.desc()).limit(1)),
            "events":list(db.scalars(select(EventCluster).where(EventCluster.company_id==c.id).order_by(EventCluster.last_seen_at.desc()).limit(10)).all()),
            "news":list(db.scalars(select(NewsArticle).where(NewsArticle.company_id==c.id).order_by(NewsArticle.published_at.desc()).limit(10)).all()),
            "whales":list(db.scalars(select(WhaleFiling).where(WhaleFiling.company_id==c.id).order_by(WhaleFiling.filing_date.desc()).limit(10)).all())}

@router.get("/radar",response_model=list[RadarItem])
def radar(limit:int=Query(25,ge=1,le=100),min_score:float=Query(0,ge=0,le=100),db:Session=Depends(get_db)):
    latest_ids=select(func.max(TickerSignal.id)).group_by(TickerSignal.company_id).subquery()
    rows=db.execute(select(TickerSignal,Company).join(Company,TickerSignal.company_id==Company.id).where(TickerSignal.id.in_(select(latest_ids.c[0])),TickerSignal.signal_score>=min_score).order_by(TickerSignal.signal_score.desc()).limit(limit)).all()
    return [RadarItem(ticker=c.ticker,company_name=c.name,signal_score=s.signal_score,insider_score=s.insider_score,x_score=s.x_score,market_score=s.market_score,news_score=s.news_score,whale_score=s.whale_score,verification_score=s.verification_score,level=signal_level(s.signal_score),summary=s.summary,latest_activity=s.generated_at) for s,c in rows]

@router.get("/radar/insiders",response_model=list[RadarItem])
def insider_radar(limit:int=Query(25,ge=1,le=100),db:Session=Depends(get_db)):
    rows=db.execute(select(Company.ticker,Company.name,func.max(InsiderTransaction.score).label("score"),func.max(InsiderTransaction.created_at).label("at")).join(InsiderTransaction,InsiderTransaction.company_id==Company.id).group_by(Company.id).order_by(func.max(InsiderTransaction.score).desc()).limit(limit)).all()
    return [RadarItem(ticker=r.ticker,company_name=r.name,insider_score=float(r.score or 0),signal_score=float(r.score or 0),level=signal_level(float(r.score or 0)),latest_activity=r.at) for r in rows]

@router.post("/watchlists")
def create_watchlist(body:WatchlistCreate,db:Session=Depends(get_db)):
    w=Watchlist(name=body.name); db.add(w); db.commit(); db.refresh(w); return w
@router.post("/watchlists/{watchlist_id}/{ticker}")
def add_watchlist_item(watchlist_id:int,ticker:str,db:Session=Depends(get_db)):
    w=db.get(Watchlist,watchlist_id); c=company_or_404(db,ticker)
    if not w: raise HTTPException(404,"Watchlist not found")
    existing=db.scalar(select(WatchlistItem).where(WatchlistItem.watchlist_id==w.id,WatchlistItem.company_id==c.id))
    if existing:return existing
    row=WatchlistItem(watchlist_id=w.id,company_id=c.id);db.add(row);db.commit();db.refresh(row);return row
@router.get("/watchlists/{watchlist_id}")
def get_watchlist(watchlist_id:int,db:Session=Depends(get_db)):
    w=db.get(Watchlist,watchlist_id)
    if not w:raise HTTPException(404,"Watchlist not found")
    companies=list(db.scalars(select(Company).join(WatchlistItem,WatchlistItem.company_id==Company.id).where(WatchlistItem.watchlist_id==w.id)).all())
    return {"id":w.id,"name":w.name,"companies":companies}

@router.post("/alerts")
def create_alert(body:AlertCreate,db:Session=Depends(get_db)):
    r=AlertRule(**body.model_dump());db.add(r);db.commit();db.refresh(r);return r
@router.get("/alerts/matches")
def alert_matches(db:Session=Depends(get_db)):
    rules=list(db.scalars(select(AlertRule).where(AlertRule.active==True)).all()); matches=[]
    for r in rules:
        q=select(TickerSignal,Company).join(Company,TickerSignal.company_id==Company.id).order_by(TickerSignal.generated_at.desc())
        if r.ticker:q=q.where(Company.ticker==r.ticker.upper())
        for s,c in db.execute(q.limit(100)).all():
            if s.signal_score>=r.min_signal_score and s.insider_score>=r.min_insider_score and s.market_score>=r.min_market_score and s.x_score>=r.min_x_score:
                matches.append({"alert_id":r.id,"alert":r.name,"ticker":c.ticker,"signal_score":s.signal_score,"generated_at":s.generated_at}); break
    return matches
