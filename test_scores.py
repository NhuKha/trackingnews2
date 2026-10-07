from app.scoring.market import score_market
from app.scoring.news import source_credibility, score_news
from app.scoring.social import score_social
from app.scoring.whale import score_whale_filing


def test_market_signal_strength():
    assert score_market(change_percent=6.0, relative_volume=3.0, dollar_volume=300_000_000) >= 70

def test_social_acceleration():
    assert score_social(mentions_1h=500, baseline_mentions_1h=100, unique_authors_1h=300, engagement_1h=5000, sentiment=70) >= 70

def test_source_weighting():
    assert source_credibility("Reuters") > source_credibility("Random Blog")
    assert score_news([92, 90]) > score_news([55])

def test_whale_13d_higher_than_13g():
    assert score_whale_filing("SC 13D") > score_whale_filing("SC 13G")
