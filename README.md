# Indian Market Signal Brain

An async Python service for research signals on NSE/BSE equities. It is the
Python intelligence layer only; no Spring Boot code is included.

## What is implemented

- `FetchNews → AnalyseSentiment → GenerateSignal` LangGraph workflow.
- NewsAPI, Alpha Vantage, and Yahoo Finance adapters, with normalized output,
  retries, exponential backoff, timeouts, and process-local rate limits.
- Concurrent news/price collection and up to five independent ticker analyses
  in parallel. One ticker failure does not abort the others.
- A read-only tool agent exposing `get_news`, `get_price`, and
  `get_technicals`. Calls selected in a tool turn execute concurrently.
- Local RAG index for annual reports and earnings-call transcripts; retrieved
  risk context is included in signal generation.
- Five-minute result cache, trace IDs, structured completion logs, and an
  in-memory token ledger. Signals are informational—not investment advice.

## Setup

```bash
uv sync
cp .env.example .env
```

Set `NEWS_API_KEY` and/or `ALPHA_VANTAGE_API_KEY` in `.env`. Without those,
the providers use Yahoo Finance where available; failures produce a safe,
structured fallback for local/offline runs. To enable LLM narrative and LLM
tool selection, configure your provider key and set `ENABLE_LLM=true`.

```bash
uv run uvicorn market_intelligence.main:app --reload
```

## APIs

Generate one signal:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/signals/analyze \
  -H 'Content-Type: application/json' \
  -d '{"ticker":"INFY","market":"NSE"}'
```

The response includes `ticker`, `headlines`, `sentiment`, `technicals`, and a
structured `signal` (`action`, `confidence`, reasons, retrieved risks).

Index an earnings transcript, then retrieve the evidence used by signals:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/signals/documents \
  -H 'Content-Type: application/json' \
  -d '{"ticker":"INFY","source":"FY26 earnings call","text":"... transcript text ..."}'

curl 'http://127.0.0.1:8000/api/v1/signals/INFY/knowledge?question=What%20were%20the%20key%20risks%3F'
```

`POST /api/v1/signals/batch` accepts one to five ticker objects and processes
them concurrently. The original `/api/v1/intelligence/analyze` endpoint is
preserved for existing clients.

## Verification

```bash
uv run pytest -q
uv run ruff check src tests
```
