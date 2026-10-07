# Stock Signal MVP v0.2

Evidence-first stock intelligence app that combines SEC insider activity, whale filings, market activity, X momentum, trusted news, event clustering, watchlists, alerts and a unified 0-100 signal score.

> The score measures unusual activity + corroboration. It is **not** a buy/sell recommendation or expected-return forecast.

## Included

- FastAPI REST API + Swagger docs
- SQLite locally / PostgreSQL with Docker
- SEC ticker bootstrap from official SEC company ticker data
- SEC Form 4 / 4-A discovery and parsing
- Insider transaction classification (P/S/M/F/A/G) and evidence scoring
- Rule 10b5-1 footnote detection
- SC 13D / 13G whale-filing detection
- Manual market-data ingestion for zero-key testing
- Optional Finnhub quote adapter
- Manual social metrics for zero-key testing
- Optional X recent-search adapter
- Manual news ingestion for zero-key testing
- Optional NewsAPI adapter
- Source credibility weighting
- News event classification + clustering
- Verification scoring
- Unified signal scoring
- Deterministic evidence-grounded summaries
- Optional OpenAI Responses API summaries
- Watchlists
- Threshold alerts
- `/refresh/{ticker}` orchestration endpoint
- Lightweight web radar at `/dashboard`
- Demo seeding script
- Tests

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and set a descriptive SEC user agent with your contact email:

```env
SEC_USER_AGENT=StockSignal/0.2 you@example.com
```

Start:

```bash
uvicorn app.main:app --reload
```

Open:

- Dashboard: http://localhost:8000/dashboard
- Swagger: http://localhost:8000/docs
- API root: http://localhost:8000

## Fastest no-key demo

```bash
python scripts/demo_seed.py
```

Then open `/dashboard`.

The demo uses synthetic `DEMO` ticker data and `example.com` URLs. It never pretends demo data is live market information.

## Bootstrap real SEC companies

```bash
curl -X POST 'http://localhost:8000/api/v1/bootstrap/sec-companies?limit=1000'
```

Or add one manually:

```bash
curl -X POST http://localhost:8000/api/v1/companies \
  -H 'Content-Type: application/json' \
  -d '{"ticker":"MSFT","name":"Microsoft Corporation","cik":"789019","exchange":"NASDAQ"}'
```

## Live SEC refresh

```bash
curl -X POST http://localhost:8000/api/v1/ingest/sec/MSFT
curl -X POST http://localhost:8000/api/v1/ingest/whales/MSFT
curl -X POST http://localhost:8000/api/v1/signals/MSFT/recompute
```

Or run all configured providers plus SEC:

```bash
curl -X POST http://localhost:8000/api/v1/refresh/MSFT
```

## Test market/social/news without paid APIs

```bash
curl -X POST http://localhost:8000/api/v1/manual/market/MSFT \
  -H 'Content-Type: application/json' \
  -d '{"price":530,"previous_close":500,"volume":36000000,"average_volume":18000000}'

curl -X POST http://localhost:8000/api/v1/manual/social/MSFT \
  -H 'Content-Type: application/json' \
  -d '{"mentions_1h":900,"baseline_mentions_1h":180,"unique_authors_1h":620,"engagement_1h":12000,"sentiment":68}'

curl -X POST http://localhost:8000/api/v1/manual/news/MSFT \
  -H 'Content-Type: application/json' \
  -d '{"source":"Reuters","title":"Example verified story","url":"https://example.com/story-1","published_at":"2026-10-07T18:00:00Z"}'

curl -X POST http://localhost:8000/api/v1/events/MSFT/cluster
curl -X POST http://localhost:8000/api/v1/signals/MSFT/recompute
```

## Optional provider keys

`.env` supports:

```env
X_BEARER_TOKEN=
NEWSAPI_KEY=
FINNHUB_API_KEY=
OPENAI_API_KEY=
OPENAI_MODEL=gpt-6-luna
```

All are optional. Missing provider keys produce a clear error on that provider-specific endpoint but do not prevent the rest of the app from running.

## Main endpoints

### Core
- `GET /api/v1/health`
- `POST /api/v1/bootstrap/sec-companies`
- `POST /api/v1/companies`
- `GET /api/v1/companies`
- `GET /api/v1/radar`
- `GET /api/v1/radar/insiders`
- `GET /api/v1/stocks/{ticker}/snapshot`

### SEC
- `POST /api/v1/ingest/sec/{ticker}`
- `POST /api/v1/ingest/whales/{ticker}`
- `GET /api/v1/stocks/{ticker}/insiders`

### Market / social / news
- `POST /api/v1/manual/market/{ticker}`
- `POST /api/v1/manual/social/{ticker}`
- `POST /api/v1/manual/news/{ticker}`
- `POST /api/v1/ingest/market/{ticker}/finnhub`
- `POST /api/v1/ingest/x/{ticker}`
- `POST /api/v1/ingest/news/{ticker}`

### Intelligence
- `POST /api/v1/events/{ticker}/cluster`
- `POST /api/v1/signals/{ticker}/recompute`
- `POST /api/v1/signals/{ticker}/ai-summary`
- `POST /api/v1/refresh/{ticker}`

### Personalization
- `POST /api/v1/watchlists`
- `POST /api/v1/watchlists/{id}/{ticker}`
- `GET /api/v1/watchlists/{id}`
- `POST /api/v1/alerts`
- `GET /api/v1/alerts/matches`

## Signal formula

Current baseline:

```text
25% X/social
25% market activity
20% insider activity
15% trusted news
10% whale filings
 5% social sentiment
```

Verification is a confidence multiplier and cannot manufacture a high score from no underlying activity.

Levels:

```text
0-39   LOW
40-59  WATCH
60-74  ELEVATED
75-89  STRONG
90-100 EXTREME
```

## Docker/PostgreSQL

```bash
cp .env.example .env
# edit SEC_USER_AGENT and any optional provider keys
docker compose up --build
```

## Tests

```bash
python -m pytest -q
```

## Production work still recommended

Before a public launch, add Alembic migrations, authentication, rate limiting, a durable task queue/scheduler, provider retry/backoff policies, observability, secrets management, richer 13D/13G ownership extraction, historical intraday baselines, X spam/coordination detection, and licensed market/news feeds appropriate to your redistribution terms.

## Personal Safari deployment

Version 0.3 adds a simple password gate so the app can be used as a personal web dashboard.

### Local use

Set `APP_PASSWORD` in `.env` if you want the login screen locally. Leave it blank to skip login on your own computer.

### Render deployment

This repository includes `render.yaml`.

1. Push the contents of this folder to GitHub.
2. In Render, create a new Blueprint / web service from that GitHub repository.
3. When Render asks for environment variables, set:
   - `APP_PASSWORD`: a password only you know.
   - `SEC_USER_AGENT`: e.g. `StockSignal/0.3 your-email@example.com` using your real email.
4. Optional: add `X_BEARER_TOKEN`, `NEWSAPI_KEY`, `FINNHUB_API_KEY`, and `OPENAI_API_KEY` later.
5. Deploy and open the generated HTTPS URL in Safari.

`APP_SECRET` is generated automatically by `render.yaml`, and `COOKIE_SECURE=true` is configured for HTTPS hosting.

### Important persistence note

The default deployed database is SQLite for simplicity. Some hosting setups use ephemeral filesystems, meaning SQLite data can be lost when the service is rebuilt or moved. Once the app is useful to you, switch `DATABASE_URL` to a persistent PostgreSQL database before relying on saved history/watchlists.
