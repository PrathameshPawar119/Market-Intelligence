# Market Intelligence AI Service - Complete Architecture & Flow Guide

## 🏗️ Project Overview

**Market Intelligence AI Service** is a FastAPI-based microservice that analyzes financial market symbols using LangGraph workflows and LLM-powered agents. It supports multiple LLM providers (OpenAI, Google Gemini, Anthropic Claude) with a single configurable factory pattern.

---

## 📊 High-Level Architecture

```
┌─────────────────┐
│   FastAPI App   │  (main.py)
│   HTTP Server   │
└────────┬────────┘
         │
    ┌────┴────────────────────────┐
    │                             │
    ▼                             ▼
┌──────────────────┐    ┌─────────────────┐
│ Health Routes    │    │ Intelligence    │
│ (/api/v1/health) │    │ Routes          │
│                  │    │ (/api/v1/intel) │
└──────────────────┘    └────────┬────────┘
                                 │
                                 ▼
                      ┌──────────────────────┐
                      │ Intelligence Service │  (orchestrator)
                      └──────────┬───────────┘
                                 │
                                 ▼
                      ┌──────────────────────┐
                      │  LangGraph Workflow  │  (execution engine)
                      │   build_graph()      │
                      └──────────┬───────────┘
                                 │
         ┌───────────────┬────────┴─────────────┬──────────────┐
         │               │                      │              │
         ▼               ▼                      ▼              ▼
    ┌────────────┐  ┌─────────────┐  ┌──────────────┐  ┌────────────┐
    │ Research   │  │ Analysis    │  │ Report       │  │ Config &   │
    │ Agent      │  │ Agent       │  │ Agent        │  │ LLM Models │
    └─────┬──────┘  └──────┬──────┘  └──────┬───────┘  └────────────┘
          │                │               │
          ▼                ▼               ▼
    ┌─────────────────────────────────────────────┐
    │         Tools (Market Data, News)           │
    └─────────────────────────────────────────────┘
```

---

## 🔄 Request-to-Response Flow

### Step 1: HTTP Request Entry Point
```
Client sends:
POST /api/v1/intelligence/analyze
Content-Type: application/json
{
    "symbol": "TCS",
    "market": "NSE",
    "analysis_type": "fundamental",
    "include_news": true
}
```

**File: [src/market_intelligence/api/routes/intelligence.py](src/market_intelligence/api/routes/intelligence.py)**
- Route handler receives request
- Validates against `IntelligenceRequest` Pydantic model
- Calls `IntelligenceService.analyze()`
- Catches exceptions and returns 502 Bad Gateway on error

---

### Step 2: Service Orchestration

**File: [src/market_intelligence/services/intelligence_service.py](src/market_intelligence/services/intelligence_service.py)**

```python
class IntelligenceService:
    def __init__(self):
        self._graph = build_graph()  # ← Compile LangGraph at init
    
    async def analyze(self, request):
        result = await self._graph.ainvoke(request.model_dump())
        # Pass result through response validator
        return IntelligenceResponse.model_validate(result)
```

**What happens:**
1. Service creates a single cached `LangGraph` workflow on initialization
2. Converts request to dict and invokes the graph
3. Graph returns final state as dict
4. Validates output against `IntelligenceResponse` schema
5. Returns structured response

---

### Step 3: LangGraph Workflow Execution

**File: [src/market_intelligence/graph/graph.py](src/market_intelligence/graph/graph.py)**

```python
def build_graph():
    workflow = StateGraph(MarketIntelligenceState)
    
    # Add three sequential nodes
    workflow.add_node("research", research_node(ResearchAgent()))
    workflow.add_node("analysis", analysis_node(AnalysisAgent()))
    workflow.add_node("report", report_node(ReportAgent()))
    
    # Define execution order
    workflow.add_edge(START, "research")        # Entry point
    workflow.add_edge("research", "analysis")   # Chain 1
    workflow.add_edge("analysis", "report")     # Chain 2
    workflow.add_edge("report", END)            # Exit point
    
    return workflow.compile()
```

**State Flow:**
```
START
  │
  ▼
[Research Node]
  │ Adds: market_data, news, research_findings
  ▼
[Analysis Node]
  │ Adds: analysis (LLM-generated)
  ▼
[Report Node]
  │ Adds: report (formatted with analysis)
  ▼
END
```

**File: [src/market_intelligence/graph/state.py](src/market_intelligence/graph/state.py)**

State schema (TypedDict):
```python
class MarketIntelligenceState(TypedDict):
    # Input fields
    symbol: str              # e.g., "RELIANCE"
    market: str              # e.g., "NSE"
    analysis_type: str       # "fundamental", "technical", "sentiment"
    include_news: bool       # default True
    
    # Accumulated state
    market_data: dict        # From Research Agent
    news: list               # From Research Agent
    research_findings: str   # From Research Agent
    analysis: str            # From Analysis Agent (LLM)
    report: str              # From Report Agent
```

---

## 🤖 Agent Architecture

### Research Agent
**File: [src/market_intelligence/agents/research_agent.py](src/market_intelligence/agents/research_agent.py)**

```
Responsibility: Gather market data and news
├─ Calls: get_market_data(symbol, market)
│  └─ Returns: {"symbol", "market", "price", "currency", "source"}
│
├─ Calls: get_news(symbol, market) [if include_news=True]
│  └─ Returns: [{"headline", "source"}]
│
└─ Outputs to state:
   ├─ market_data
   ├─ news
   └─ research_findings (text summary)
```

**Current Implementation:** Mock data (see [src/market_intelligence/tools/market.py](src/market_intelligence/tools/market.py) and [src/market_intelligence/tools/news.py](src/market_intelligence/tools/news.py))

---

### Analysis Agent
**File: [src/market_intelligence/agents/analysis_agent.py](src/market_intelligence/agents/analysis_agent.py)**

```
Responsibility: LLM-powered analysis
├─ Input: state containing market_data, news, analysis_type
├─ Prompt Construction:
│  └─ "Analyze {symbol} on {market} using {analysis_type} approach.
│      Research: {research_findings}
│      Market data: {market_data}
│      News: {news}"
│
├─ LLM Call:
│  ├─ Gets LLM from get_chat_model()
│  ├─ Sends prompt via llm.ainvoke(prompt)
│  └─ Returns response
│
└─ Output: {"analysis": "...generated text..."}
```

**Mock Fallback:** If no API key is configured (`not settings.has_configured_provider`), returns mock analysis.

**LLM Selection:** Uses `get_chat_model()` which reads from settings and instantiates the right provider.

---

### Report Agent
**File: [src/market_intelligence/agents/report_agent.py](src/market_intelligence/agents/report_agent.py)**

```
Responsibility: Format final report
├─ Input: All accumulated state from previous agents
├─ Formatting:
│  └─ "{SYMBOL} ({MARKET}) report
│      Analysis type: {analysis_type}
│      {analysis_text_from_llm}"
│
└─ Output: {"report": "...formatted string..."}
```

**No LLM call** — just formatting and organization.

---

## 🔧 Configuration & LLM Provider System

### Settings Architecture

**File: [src/market_intelligence/config/settings.py](src/market_intelligence/config/settings.py)**

```python
class Settings(BaseSettings):
    # Provider selection
    model_provider: Literal["openai", "gemini", "claude"] = "openai"
    
    # Provider-specific keys & models
    openai_api_key: str = None
    openai_model: str = "gpt-4o-mini"
    
    gemini_api_key: str = None
    gemini_model: str = "gemini-2.0-flash"
    
    anthropic_api_key: str = None
    anthropic_model: str = "claude-3-5-sonnet-latest"
    
    # Smart properties
    @property
    def active_api_key(self) -> str:
        """Returns the API key for the selected provider"""
        return {"openai": self.openai_api_key,
                "gemini": self.gemini_api_key,
                "claude": self.anthropic_api_key}[self.model_provider]
    
    @property
    def active_model_name(self) -> str:
        """Returns the model name for the selected provider"""
        return {"openai": self.openai_model,
                "gemini": self.gemini_model,
                "claude": self.anthropic_model}[self.model_provider]
    
    @property
    def has_configured_provider(self) -> bool:
        """Checks if active provider has an API key"""
        return bool(self.active_api_key)
```

**Loading from environment:**
```
Model reads from .env file
MODEL_PROVIDER=gemini
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.0-flash
```

---

### LLM Factory Pattern

**File: [src/market_intelligence/llm/models.py](src/market_intelligence/llm/models.py)**

```python
@lru_cache
def get_chat_model() -> Any:
    """
    Factory function: Returns the right LLM instance based on settings
    Cached with lru_cache for performance
    """
    settings = get_settings()
    provider = settings.model_provider.lower()
    
    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key
        )
    
    elif provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.gemini_api_key
        )
    
    elif provider == "claude":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=settings.anthropic_model,
            api_key=settings.anthropic_api_key
        )
    
    else:
        raise ValueError("Unsupported provider")
```

**Key Features:**
- ✅ Single factory function for all providers
- ✅ Lazy imports (only loads requested provider's library)
- ✅ LRU cache for performance (creates instance once)
- ✅ All agents call `get_chat_model()` — no hardcoding of OpenAI
- ✅ Provider switching via `MODEL_PROVIDER` env variable

---

## 📝 API Schemas

### Request Schema
**File: [src/market_intelligence/api/schemas/requests.py](src/market_intelligence/api/schemas/requests.py)**

```python
class IntelligenceRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=20)
    market: str = Field(min_length=1, max_length=20)
    analysis_type: Literal["fundamental", "technical", "sentiment"] = "fundamental"
    include_news: bool = True
```

**Validation:** Pydantic ensures:
- Non-empty symbol/market
- Max 20 chars
- Exact analysis types
- Boolean for news flag

---

### Response Schema
**File: [src/market_intelligence/api/schemas/responses.py](src/market_intelligence/api/schemas/responses.py)**

```python
class IntelligenceResponse(BaseModel):
    symbol: str
    market: str
    analysis_type: str
    include_news: bool
    market_data: dict[str, Any]
    news: list[dict[str, Any]]
    research_findings: str
    analysis: str
    report: str
```

**Matches the graph's final state** — all fields must be present.

---

## 🛠️ Tools (Data Sources)

### Market Data Tool
**File: [src/market_intelligence/tools/market.py](src/market_intelligence/tools/market.py)**

```python
async def get_market_data(symbol: str, market: str) -> dict:
    # Currently returns mock data
    # TODO: Integrate with financial data provider (Alpha Vantage, etc.)
    return {
        "symbol": symbol.upper(),
        "market": market.upper(),
        "price": None,              # Ready for real data
        "currency": "INR" if market.upper() == "NSE" else None,
        "source": "mock"
    }
```

---

### News Tool
**File: [src/market_intelligence/tools/news.py](src/market_intelligence/tools/news.py)**

```python
async def get_news(symbol: str, market: str) -> list:
    # Currently returns mock data
    # TODO: Integrate with news provider (NewsAPI, Bloomberg, etc.)
    return [
        {
            "headline": f"No live news loaded for {symbol.upper()} ({market.upper()})",
            "source": "mock"
        }
    ]
```

---

## 📊 Complete Data Flow Diagram

```
┌─────────────────────────────────────┐
│ HTTP POST Request                   │
│ {symbol, market, analysis_type,...} │
└──────────────┬──────────────────────┘
               │
               ▼
        ┌──────────────┐
        │ FastAPI      │
        │ Route        │
        │ Handler      │
        └──────┬───────┘
               │ Validates request schema
               ▼
        ┌──────────────────────┐
        │ Intelligence Service │
        │ .analyze()           │
        └──────┬───────────────┘
               │ Invokes compiled LangGraph
               ▼
        ┌─────────────────────────────┐
        │ LangGraph Workflow          │
        │ START → research → analysis │
        │     → report → END          │
        └──────┬──────────────────────┘
               │
    ┌──────────┼──────────────┐
    │          │              │
    ▼          ▼              ▼
  ┌─────┐  ┌────────┐  ┌──────────┐
  │ RES │  │ANALYSIS│  │ REPORT   │
  └─────┘  └────────┘  └──────────┘
    │         │            │
    │         │ Calls:     │
    │         │ get_chat   │
    │         │ _model()   │
    │         │    ↓       │
    │         │ ┌──────┐   │
    │         │ │ LLM  │   │
    │         │ │(OAI/ │   │
    │         │ │GEM/  │   │
    │         │ │CLAU) │   │
    │         │ └──────┘   │
    │         │    ↓       │
    │         │ Returns    │
    │         │ analysis   │
    │         │ text       │
    │         │            │
    │         └─────┬──────┘
    │               │
    │               ▼
    │         State updated
    │         with: analysis
    │               & report
    │               │
    └───────────────┼──────┐
                    │      │
                    ▼      ▼
            ┌──────────────────────┐
            │ Final State          │
            │ (all fields filled)  │
            └──────┬───────────────┘
                   │
                   ▼
            ┌──────────────────────┐
            │ Validate against     │
            │ IntelligenceResponse │
            └──────┬───────────────┘
                   │
                   ▼
            ┌──────────────────────┐
            │ JSON Response        │
            │ HTTP 200 OK          │
            └──────────────────────┘
```

---

## 🧪 Testing Architecture

**Files in [tests/](tests/) directory:**

- `test_health.py` — Health endpoint validation
- `test_intelligence.py` — API endpoint with mock LLM
- `test_intelligence_service.py` — Service orchestration
- `test_graph.py` — Graph workflow execution
- `test_llm_models.py` — Provider factory tests (new)

**Mock behavior:** When `has_configured_provider` is False, agents return mock data instead of calling LLM.

---

## 🔐 Environment Configuration

```env
# Provider selection
MODEL_PROVIDER=openai  # or "gemini" or "claude"

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# Google Gemini
GEMINI_API_KEY=AIza...
GEMINI_MODEL=gemini-1.5-flash

# Anthropic Claude
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-3-5-sonnet-latest

# Deployment
ENVIRONMENT=development
```

---

## 🚀 Startup Sequence

```
1. FastAPI app creates instance
   ↓
2. Health route imported
   ↓
3. Intelligence route imported
   ├─ Creates IntelligenceService instance
   └─ Calls build_graph() [lazy-compiled]
   ↓
4. Settings loaded from .env via Pydantic
   ↓
5. get_settings() cached
   ↓
6. Server listening on 0.0.0.0:8000
```

---

## 📈 Key Design Patterns

| Pattern | Location | Purpose |
|---------|----------|---------|
| **Factory** | `get_chat_model()` | Instantiate correct LLM provider |
| **Singleton** | `@lru_cache` on `get_settings()` & `get_chat_model()` | Single config & LLM instance |
| **State Machine** | `LangGraph` + `MarketIntelligenceState` | Orchestrate agent workflow |
| **Dependency Injection** | Agents accept optional `llm` param | Testability & mock support |
| **Data Validation** | Pydantic schemas | Request/response contracts |
| **Lazy Loading** | `if provider == "x": from langchain_x` | Only load needed libraries |

---

## 🔗 Dependencies

```toml
fastapi>=0.128.8              # HTTP framework
langchain>=0.3.30             # LLM orchestration
langgraph>=0.6.11             # Workflow graph execution
langchain-openai>=0.3.35      # OpenAI integration
langchain-google-genai>=2.2.0 # Google Gemini integration (NEW)
langchain-anthropic>=0.3.35   # Claude integration (NEW)
pydantic-settings>=2.11.0     # Config from .env
uvicorn[standard]>=0.39.0     # ASGI server
```

---

## Summary

The system follows a clean **layered architecture**:

1. **API Layer** → FastAPI routes & schemas
2. **Service Layer** → Business logic & orchestration
3. **Graph Layer** → LangGraph workflow & state
4. **Agent Layer** → Domain-specific workers
5. **Tool Layer** → External integrations (mocked)
6. **LLM Layer** → Provider-agnostic factory

**Key improvement:** `get_chat_model()` factory now supports **OpenAI, Gemini, Claude** with a single configuration switch (`MODEL_PROVIDER` env variable).
