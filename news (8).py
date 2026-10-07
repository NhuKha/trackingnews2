SOURCE_WEIGHTS = {
    "sec": 100.0,
    "company": 95.0,
    "reuters": 92.0,
    "bloomberg": 92.0,
    "associated press": 90.0,
    "ap": 90.0,
    "financial times": 90.0,
    "wall street journal": 90.0,
    "wsj": 90.0,
    "cnbc": 80.0,
    "barron's": 80.0,
}


def source_credibility(source: str) -> float:
    lowered = (source or "").strip().lower()
    for key, value in SOURCE_WEIGHTS.items():
        if key in lowered:
            return value
    return 55.0


def source_tier(score: float) -> str:
    if score >= 95:
        return "A"
    if score >= 88:
        return "B"
    if score >= 72:
        return "C"
    return "D"


def score_news(credibilities: list[float]) -> float:
    if not credibilities:
        return 0.0
    top = sorted(credibilities, reverse=True)[:5]
    base = max(top)
    confirmation_bonus = min(20.0, max(0, len([v for v in top if v >= 80]) - 1) * 7.0)
    return round(min(100.0, base * 0.8 + confirmation_bonus), 2)
