def signal_level(score: float) -> str:
    if score >= 90:
        return "EXTREME"
    if score >= 75:
        return "STRONG"
    if score >= 60:
        return "ELEVATED"
    if score >= 40:
        return "WATCH"
    return "LOW"


def combine_signal_scores(*, x_score=0.0, market_score=0.0, insider_score=0.0,
                          news_score=0.0, whale_score=0.0, sentiment_score=0.0,
                          verification_score=0.0) -> float:
    base = (
        0.25 * x_score
        + 0.25 * market_score
        + 0.20 * insider_score
        + 0.15 * news_score
        + 0.10 * whale_score
        + 0.05 * sentiment_score
    )
    # Verification can increase confidence, but cannot create a signal from nothing.
    multiplier = 0.80 + 0.20 * max(0.0, min(100.0, verification_score)) / 100.0
    return round(max(0.0, min(100.0, base * multiplier)), 2)
