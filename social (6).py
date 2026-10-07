import math


def score_social(*, mentions_1h: int, baseline_mentions_1h: float, unique_authors_1h: int,
                 engagement_1h: int, sentiment: float = 50.0) -> float:
    baseline = max(1.0, float(baseline_mentions_1h or 0.0))
    acceleration = max(0.0, mentions_1h / baseline)
    acceleration_score = min(45.0, max(0.0, (acceleration - 1.0) * 18.0))
    diversity = unique_authors_1h / max(1, mentions_1h)
    diversity_score = min(20.0, diversity * 25.0)
    engagement_score = min(20.0, math.log10(max(1, engagement_1h)) * 5.0)
    sentiment_shift = min(15.0, abs(float(sentiment) - 50.0) * 0.3)
    return round(min(100.0, acceleration_score + diversity_score + engagement_score + sentiment_shift), 2)
