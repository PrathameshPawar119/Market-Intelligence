# Market Intelligence AI Service

## Setup

Install Python 3.12+ and [uv](https://docs.astral.sh/uv/), then install dependencies:

```bash
uv sync
cp .env.example .env
```

## Environment variables

Set `OPENAI_API_KEY` to enable live LLM analysis. `OPENAI_MODEL` defaults to `gpt-4o-mini`, and `ENVIRONMENT` defaults to `development`. Without an API key, the service uses a local mock analysis so the API can be exercised safely.

## Run

```bash
uv run uvicorn market_intelligence.main:app --reload
```

The service listens on `http://127.0.0.1:8000`.

## API examples

Health check:

```bash
curl http://127.0.0.1:8000/api/v1/health
```

Analyze a symbol:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/intelligence/analyze \
	-H 'Content-Type: application/json' \
	-d '{"symbol":"RELIANCE","market":"NSE","analysis_type":"fundamental","include_news":true}'
```

## Project architecture

```text
FastAPI routes -> IntelligenceService -> LangGraph -> Agents -> Tools / LLM
```

The graph currently runs `research -> analysis -> report`. Provider integrations are deliberately mocked behind tool interfaces and can be added without changing the API layer.

## Spring Boot integration

Configure the Python service base URL in Spring Boot, then send an HTTP `POST` to `/api/v1/intelligence/analyze` with the JSON request shown above. Deserialize the JSON response into a Spring DTO and handle non-2xx responses as service errors.
