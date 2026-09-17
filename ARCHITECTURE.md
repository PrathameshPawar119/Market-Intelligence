# Indian Market Signal Brain — Architecture and Operating Guide

## Scope

This is the Python intelligence layer for Indian equities. It collects current
news and prices for NSE/BSE tickers, assesses the evidence, retrieves
company-specific risk context, and produces an explainable research signal.
It deliberately contains no Spring Boot or browser-streaming implementation.

Every result is informational, not investment advice. The default signal policy
is deterministic and auditable; an LLM can add tool selection and a concise
risk narrative when explicitly enabled.

## Architecture

```text
HTTP request
  │
  ├─ rate limit (Redis when configured; local fallback)
  ├─ five-minute result cache
  ▼
IntelligenceService
  ▼
LangGraph: FetchNews → AnalyseSentiment → GenerateSignal
  │                 │                  │
  │                 │                  └─ structured action, confidence, reasons, risks
  │                 └─ explainable sentiment + optional LLM narrative
  └─ MarketToolAgent + RAG retrieval
       ├─ get_news       → NewsAPI, then Yahoo Finance fallback
       ├─ get_price      → Alpha Vantage, then Yahoo Finance fallback
       └─ get_technicals → closes reused from get_price
```

`MarketIntelligenceState` is a `TypedDict`. It retains every accumulated value
as the graph advances: normalized ticker, market data, headlines, technicals,
retrieved chunks, sentiment, signal, tool calls, and recoverable errors. The
legacy `symbol` field is still accepted, while the new output also exposes
`ticker`.

## End-to-end request flow

1. `POST /api/v1/signals/analyze` validates `ticker`, `market`, and
   `include_news` with Pydantic. `X-User-Id`, normally forwarded by the
   authenticated gateway, identifies the request for rate limiting.
2. The rate limiter allows 10 requests/minute/user by default. `REDIS_URL`
   enables atomic shared counters; if Redis is absent or unavailable, a local
   sliding-window limiter safely takes over.
3. `IntelligenceService` checks a process-local TTL cache keyed by ticker,
   market, analysis type, and news choice. Successful responses are cached for
   300 seconds by default; failed executions are never cached.
4. The `FetchNews` graph node calls the tool agent. News and price calls from
   the same planning turn run with `asyncio.gather`, so independent provider
   latency is not serialized.
5. `AnalyseSentiment` scores headline text and, when enabled, asks the LLM for
   a short, risk-only interpretation of the supplied evidence.
6. `GenerateSignal` combines sentiment, technical trend, and retrieved filing
   context into `BUY`, `HOLD`, or `SELL`, plus confidence, reasons, and a
   disclaimer.
7. The service emits a trace record containing trace ID, ticker, token count,
   latency, and success. The response is returned as validated JSON.

## Tool agent strategy

The agent has exactly three read-only tools:

| Tool | Data returned | Use |
| --- | --- | --- |
| `get_news(ticker)` | Latest normalized headline, source, summary, URL, date | News catalysts and risks |
| `get_price(ticker)` | Latest price and daily close history | Price context and technical input |
| `get_technicals(ticker)` | SMA-20, SMA-50, RSI-14, trend, one-day return | Trend confirmation |

With `ENABLE_LLM=true`, the selected LangChain model receives native bound
tool schemas and can choose tools. Calls selected in one turn execute in
parallel. Technicals reuse the price series instead of creating another remote
call. With LLM use disabled—or if the provider cannot respond—the agent calls
all three tools in a fixed, safe plan. This prevents an LLM outage from
preventing analysis or accidentally consuming tokens in development.

## Market-data and resilience strategy

| Capability | Preferred source | Fallback | Ticker conversion |
| --- | --- | --- | --- |
| Headlines | NewsAPI (`NEWS_API_KEY`) | Yahoo Finance search | `INFY.NS` / `INFY.BO` |
| Daily closes | Alpha Vantage (`ALPHA_VANTAGE_API_KEY`) | Yahoo Finance chart | `INFY.NS` / `INFY.BO` |

All adapters normalize data before passing it to the graph. `JsonProvider`
applies configurable timeouts, retry with exponential backoff for 429/transient
5xx responses, and independent sliding-window limits for news and market
requests. If a provider ultimately fails, the collection node preserves any
other evidence and supplies a structured fallback instead of crashing the
complete signal.

## Sentiment and technical strategy

The default sentiment engine uses an explicit market-catalyst lexicon. Positive
examples include `profit`, `growth`, `upgrade`, and `buyback`; negative examples
include `risk`, `loss`, `downgrade`, `probe`, and `miss`. It examines headline
titles and summaries:

```text
score = (positive_term_count - negative_term_count)
        / (positive_term_count + negative_term_count)
```

No matching terms yields zero. Scores above `+0.15` are positive, below
`-0.15` negative, and the remainder neutral. This lexical policy is visible in
code and testable; it should be calibrated against historical Indian-market
data before any live capital is put at risk.

Technicals derive SMA-20, SMA-50, RSI-14, and the latest daily return from the
same close series. Trend is bullish when `last >= SMA-20 >= SMA-50`, bearish
otherwise when sufficient data is present.

```text
combined = sentiment_score + 0.35  (bullish trend)
combined = sentiment_score - 0.35  (bearish trend)

BUY  when combined >=  0.35
SELL when combined <= -0.35
HOLD otherwise
```

Confidence is `0.45 + min(abs(combined), 0.5)`, capped at `0.95`. The response
keeps the component evidence, score, explanation, risks, and disclaimer—so a
consumer never sees an unexplained action.

## RAG for reports and earnings calls

`POST /api/v1/signals/documents` ingests annual-report text or an earnings-call
transcript with its ticker and source label. `LocalRagIndex` splits it into
roughly 900-word chunks and records a chunk ID. The research node queries the
company's chunks for risk, earnings, guidance, debt, and outlook context;
top-matching snippets appear in `signal.risks`.

```text
POST /api/v1/signals/documents
{"ticker":"INFY","source":"FY26 earnings call","text":"..."}

GET /api/v1/signals/INFY/knowledge?question=What%20were%20the%20key%20risks%3F
```

The present index uses deterministic lexical term-overlap ranking. It is useful
for the initial service and unit tests but is in-memory and non-persistent. For
production scale, retain the same `ingest` and `query` interface and replace
the storage with chunk embeddings in pgvector, Qdrant, or OpenSearch. Preserve
source URL, report date, page/section, and embedding version for citations.

## APIs

| Endpoint | Purpose |
| --- | --- |
| `POST /api/v1/signals/analyze` | Analyze one ticker |
| `POST /api/v1/signals/batch` | Analyze one to five tickers concurrently |
| `POST /api/v1/signals/documents` | Index a filing or transcript |
| `GET /api/v1/signals/{ticker}/knowledge` | Inspect retrieved company context |
| `GET /api/v1/signals/usage/daily` | Process-local token/cost totals |
| `POST /api/v1/intelligence/analyze` | Backward-compatible legacy request |
| `GET /api/v1/health` | Process health |

Batch analysis deliberately returns an item per input ticker. Each contains
either `result` or `error`; one failed provider/ticker does not discard the
other analyses. A semaphore bounds parallel batch work to five by default.

A typical single result contains:

```json
{
  "ticker": "INFY",
  "headlines": [{"headline": "...", "source": "..."}],
  "sentiment": {"label": "positive", "score": 0.5},
  "technicals": {"sma_20": 0, "sma_50": 0, "rsi_14": 0, "trend": "bullish"},
  "signal": {"action": "BUY", "confidence": 0.8, "score": 0.85, "risks": []}
}
```

## LLM, tracing, token, and cost strategy

The model factory supports OpenAI, Gemini, and Claude. Enabling the LLM is
explicit (`ENABLE_LLM=true`) after selecting a provider and key. LLM planning
and narrative failures fall back to the deterministic policy.

Each LLM invocation is wrapped with structured prompt, response, input/output
token, latency, and success logging. Each request gets a trace ID. The shape is
compatible with shipping logs into Langfuse or LangSmith; no hosted tracing SDK
or credentials are required for the core path. The in-process `UsageLedger`
tracks token totals by user and ticker, estimates cost from configurable
per-million token prices, exposes the daily usage endpoint, and logs a warning
over `DAILY_COST_ALERT_USD` (default $10). Use a shared database/telemetry
backend for durable multi-worker dashboards and alerts.

## Configuration

Copy `.env.example` to `.env`; never commit credentials.

| Variable | Default | Role |
| --- | --- | --- |
| `NEWS_API_KEY` | empty | Prefer NewsAPI for headlines |
| `ALPHA_VANTAGE_API_KEY` | empty | Prefer Alpha Vantage for closes |
| `ENABLE_LLM` | `false` | Turn on LLM tool selection/narrative |
| `MODEL_PROVIDER` | `openai` | `openai`, `gemini`, or `claude` |
| `REQUEST_TIMEOUT_SECONDS` | `8` | Remote request timeout |
| `PROVIDER_MAX_RETRIES` | `2` | Retries after initial attempt |
| `CACHE_TTL_SECONDS` | `300` | Successful result-cache lifetime |
| `MAX_PARALLEL_TICKERS` | `5` | Batch concurrency cap |
| `REQUESTS_PER_MINUTE_PER_USER` | `10` | API rate limit |
| `REDIS_URL` | empty | Shared rate-limit store |
| `DAILY_COST_ALERT_USD` | `10` | Usage-warning threshold |

## Code map and verification

| Area | Files |
| --- | --- |
| API, validation, limiter | `main.py`, `api/routes/`, `api/rate_limit.py` |
| Cache and batch service | `services/intelligence_service.py` |
| Graph and state | `graph/` |
| Agents and decision policy | `agents/` |
| Provider adapters/retries | `tools/` |
| RAG | `rag.py` |
| Structured traces/ledger | `observability.py` |

Tests cover provider normalization with mock HTTP transports, all three graph
stages, concurrent tools, RAG risk retrieval, batch isolation, legacy routes,
and model configuration. They run without live provider keys:

```bash
uv run pytest -q
uv run ruff check src tests
```
