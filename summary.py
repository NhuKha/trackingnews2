from app.config import settings


def deterministic_summary(ticker: str, *, signal_score: float, insider_score: float, market_score: float,
                          x_score: float, news_score: float, whale_score: float, verification_score: float) -> str:
    drivers = sorted({"social": x_score, "market": market_score, "insider": insider_score,
                      "news": news_score, "whale": whale_score}.items(), key=lambda x: x[1], reverse=True)
    top = [name for name, score in drivers if score >= 40][:3]
    evidence = ", ".join(top) if top else "limited current evidence"
    verified = "strongly verified" if verification_score >= 80 else "partially verified" if verification_score >= 55 else "not yet strongly verified"
    return f"{ticker} has an evidence-strength signal of {signal_score:.0f}/100, led by {evidence}. The underlying information is {verified}. This score measures unusual activity and corroboration, not expected price direction."


async def ai_summary(prompt: str) -> str | None:
    if not settings.openai_api_key:
        return None
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.responses.create(model=settings.openai_model,
            input=[{"role": "system", "content": "Summarize stock intelligence conservatively. Use only supplied facts. Never give buy/sell advice."},
                   {"role": "user", "content": prompt}])
        return response.output_text.strip()
    except Exception:
        return None
