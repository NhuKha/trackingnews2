from decimal import Decimal


def score_insider_transaction(*, code: str | None, value: Decimal | None, is_director: bool,
                              is_officer: bool, officer_title: str | None, is_10b5_1: bool) -> float:
    """Evidence score, not an investment recommendation."""
    if not code:
        return 0.0

    code = code.upper()
    score = 0.0
    title = (officer_title or "").lower()

    if code == "P":
        score += 35
        if "chief executive" in title or "ceo" in title:
            score += 20
        elif "chief financial" in title or "cfo" in title:
            score += 15
        elif is_director:
            score += 10
        elif is_officer:
            score += 8

        amount = float(value or 0)
        if amount >= 5_000_000:
            score += 25
        elif amount >= 1_000_000:
            score += 20
        elif amount >= 500_000:
            score += 15
        elif amount >= 100_000:
            score += 8

    elif code == "S":
        score += 12
        if is_10b5_1:
            score -= 7
        amount = float(value or 0)
        if amount >= 5_000_000:
            score += 8
        elif amount >= 1_000_000:
            score += 5
    elif code in {"M", "F", "A", "G"}:
        score += 2

    return max(0.0, min(100.0, score))
