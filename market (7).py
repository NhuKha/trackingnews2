def score_market(*, change_percent: float | None, relative_volume: float | None, dollar_volume: float | None = None) -> float:
    score = 0.0
    rv = max(0.0, float(relative_volume or 0.0))
    move = abs(float(change_percent or 0.0))
    dv = max(0.0, float(dollar_volume or 0.0))

    score += min(45.0, max(0.0, (rv - 1.0) * 22.5))
    score += min(35.0, move * 5.0)
    if dv >= 1_000_000_000:
        score += 20
    elif dv >= 250_000_000:
        score += 14
    elif dv >= 50_000_000:
        score += 8
    return round(min(100.0, score), 2)
