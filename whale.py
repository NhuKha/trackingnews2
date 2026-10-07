def score_whale_filing(form_type: str, ownership_percent: float | None = None) -> float:
    form = (form_type or "").upper()
    score = 0.0
    if "13D" in form:
        score = 78.0
    elif "13G" in form:
        score = 60.0
    if form.endswith("/A"):
        score -= 5.0
    if ownership_percent is not None:
        if ownership_percent >= 10:
            score += 15
        elif ownership_percent >= 5:
            score += 8
    return max(0.0, min(100.0, score))
