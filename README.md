# Stock Research Platform

An AI-powered multi-agent stock research platform with real-time analysis, live news sentiment, bull/bear debates, stock screening, and weighted investment recommendations.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          Frontend (React 18 + TypeScript)               │
│                                                                         │
│  SearchBar (100+ ticker dropdown) ─► POST /api/analyze/{ticker}        │
│  AgentFeed  ◄──────────────────────  SSE /api/stream/{ticker}          │
│  MCPGraph   ◄──────────────────────  GET /api/agents/status (2s poll)  │
│  Screener   ◄──────────────────────  GET /api/screen                   │
│  Charts     ─  lightweight-charts (OHLCV candlestick)                  │
│               + Recharts (sentiment timeline)                           │
└──────────────────────────┬──────────────────────────────────────────────┘
                            │  HTTP / SSE / WebSocket
┌───────────────────────────▼─────────────────────────────────────────────┐
│                    FastAPI Backend (Python 3.11)                        │
│                                                                         │
│  Orchestrator                                                           │
│    ├── Phase 1 (parallel)                                               │
│    │     ├── Historical Agent  ─► Stooq OHLCV + ta library             │
│    │     └── News Agent        ─► Finnhub company news + OpenAI        │
│    ├── Phase 2                                                          │
│    │     └── Market Agent      ─► Finnhub quote + FMP fundamentals     │
│    ├── Phase 2b                                                         │
│    │     ├── Bull Agent    ─► OpenAI gpt-4o-mini                       │
│    │     ├── Bear Agent    ─► OpenAI gpt-4o-mini                       │
│    │     └── Moderator     ─► OpenAI gpt-4o-mini                       │
│    ├── Phase 3                                                          │
│    │     └── Recommender   ─► Weighted composite score                 │
│    └── Phase 4                                                          │
│          └── Monitor Agent ─► Pipeline metrics → Redis                 │
│                                                                         │
└────────┬──────────────────────────────────┬────────────────────────────┘
         │                                  │
┌────────▼──────────┐             ┌─────────▼──────────┐
│  Redis 7          │             │  PostgreSQL 16      │
│  ─ pub/sub bus    │             │  ─ analysis_records │
│  ─ result cache   │             │    (full JSON)      │
│  ─ agent statuses │             └────────────────────┘
│  ─ pipeline stats │
└───────────────────┘
```

## Quick Start

### Prerequisites
- Docker and Docker Compose
- An [OpenAI API key](https://platform.openai.com/api-keys)

### 1. Clone & configure

```bash
git clone https://github.com/Akshay007724/stock-research-platform.git
cd stock-research-platform
cp .env.example .env
```

Open `.env` and set your keys:

```env
OPENAI_API_KEY=sk-...          # Required — all agent reasoning
FINNHUB_API_KEY=...            # Real-time quotes + company news
FMP_API_KEY=...                # Fundamentals (P/E, EPS, beta, 52w range)
```

### 2. Launch all services

```bash
docker compose up -d
```

This starts: PostgreSQL, Redis, Qdrant, FastAPI backend, React frontend.

### 3. Open the dashboard

| Service | URL |
|---------|-----|
| **Dashboard** | http://localhost:3000 |
| **API docs (Swagger)** | http://localhost:8000/docs |
| **API health** | http://localhost:8000/health |
| **Qdrant UI** | http://localhost:6333/dashboard |

### 4. Run your first analysis

Type a company name or ticker (e.g. `NVDA`, `Apple`) in the search bar and click **Analyze**.

---

## API Reference

All endpoints are served at `http://localhost:8000`. Interactive docs are at `/docs`.

---

### `POST /api/analyze/{ticker}`

Run the full 9-agent analysis pipeline for a stock.

**Path parameter**

| Name | Type | Description |
|------|------|-------------|
| `ticker` | string | Stock symbol, 1–10 chars, e.g. `AAPL`, `BRK.B` |

**Response** — `AnalysisResult`

```json
{
  "ticker": "AAPL",
  "market_data": {
    "ticker": "AAPL",
    "price": 213.49,
    "change": -1.23,
    "change_pct": -0.57,
    "volume": 54321000,
    "market_cap": 3280000000000,
    "pe_ratio": 34.2,
    "eps": 6.43,
    "beta": 1.21,
    "week_52_high": 237.23,
    "week_52_low": 164.08,
    "sector": "Technology",
    "industry": "Consumer Electronics",
    "name": "Apple Inc."
  },
  "ohlcv": [
    {
      "ticker": "AAPL",
      "timestamp": "2024-03-18T00:00:00",
      "open": 214.10,
      "high": 215.50,
      "low": 212.30,
      "close": 213.49,
      "volume": 54321000,
      "adjusted_close": 213.49
    }
  ],
  "indicators": {
    "ticker": "AAPL",
    "timestamp": "2024-03-18T00:00:00",
    "ema_9": 212.3,
    "ema_21": 210.1,
    "ema_50": 207.5,
    "ema_200": 195.2,
    "rsi_14": 58.4,
    "macd": 1.23,
    "macd_signal": 0.98,
    "macd_hist": 0.25,
    "atr": 3.2,
    "bb_upper": 220.1,
    "bb_middle": 213.0,
    "bb_lower": 205.9,
    "bb_pct": 0.57,
    "adx": 22.4,
    "obv": 12345678,
    "vwap": 213.1,
    "volume_zscore": 0.3,
    "support": 208.0,
    "resistance": 220.0,
    "trend_direction": 1
  },
  "news": [
    {
      "title": "Apple beats Q2 estimates on services revenue",
      "url": "https://...",
      "source": "Finnhub",
      "published_at": "2024-03-18T10:30:00Z",
      "sentiment_score": 0.72,
      "sentiment_label": "positive",
      "relevance_score": 0.88,
      "summary": "..."
    }
  ],
  "debate": {
    "ticker": "AAPL",
    "bull": {
      "side": "bull",
      "points": ["Strong services growth", "Loyal customer base"],
      "score": 72,
      "key_metrics": {"P/E": "34.2", "Beta": "1.21"}
    },
    "bear": {
      "side": "bear",
      "points": ["China headwinds", "Slowing hardware growth"],
      "score": 55,
      "key_metrics": {}
    },
    "verdict": "Slight bull advantage",
    "verdict_score": 62,
    "moderator_summary": "Apple shows resilient fundamentals..."
  },
  "recommendation": {
    "ticker": "AAPL",
    "action": "BUY",
    "confidence": 0.78,
    "technical_score": 68,
    "sentiment_score": 71,
    "fundamental_score": 65,
    "debate_score": 62,
    "composite_score": 67,
    "reasoning": ["Strong technical momentum", "Positive news sentiment"],
    "allocation_pct": 5.0,
    "risk_level": "Medium",
    "target_price": 235.0,
    "stop_loss": 200.0,
    "timestamp": "2024-03-18T12:00:00Z"
  },
  "agent_log": [
    {
      "id": "evt_abc123",
      "agent_name": "orchestrator",
      "event_type": "start",
      "message": "Starting full analysis pipeline for AAPL",
      "data": {},
      "timestamp": "2024-03-18T12:00:00Z"
    }
  ]
}
```

**Notes**
- Results are cached in Redis for **1 hour**. Subsequent calls for the same ticker return the cached result instantly.
- Analysis typically takes 5–15 seconds (limited by OpenAI latency for debate + recommendation phases).

---

### `GET /api/stream/{ticker}`

Server-Sent Events stream of real-time agent activity during an analysis run.

**Path parameter**

| Name | Type | Description |
|------|------|-------------|
| `ticker` | string | Must match an active or recent analysis ticker |

**Response** — `text/event-stream`

Each event is a JSON `AgentEvent` object:

```
data: {"id":"evt_001","agent_name":"historical","event_type":"start","message":"Fetching OHLCV for AAPL","data":{},"timestamp":"2024-03-18T12:00:01Z"}

data: {"id":"evt_002","agent_name":"historical","event_type":"progress","message":"Downloaded 365 days, computing indicators...","data":{"rows":365},"timestamp":"2024-03-18T12:00:02Z"}

data: {"id":"evt_003","agent_name":"recommender","event_type":"complete","message":"Recommendation: BUY (composite 67)","data":{"action":"BUY"},"timestamp":"2024-03-18T12:00:10Z"}
```

`event_type` values: `start`, `progress`, `complete`, `error`

**Usage**
```js
const es = new EventSource('/api/stream/AAPL')
es.onmessage = (e) => console.log(JSON.parse(e.data))
```

---

### `WS /ws/{ticker}`

WebSocket for live price updates and agent events.

```js
const ws = new WebSocket('ws://localhost:8000/ws/AAPL')
ws.onmessage = (e) => console.log(JSON.parse(e.data))
```

---

### `GET /api/agents/status`

Returns the current status of all agents in React Flow graph format.

**Response**

```json
{
  "nodes": [
    {
      "id": "orchestrator",
      "type": "agentNode",
      "position": {"x": 400, "y": 0},
      "data": {
        "label": "Orchestrator",
        "status": "done",
        "last_event": "Analysis complete for AAPL — recommendation: BUY",
        "agent_id": "orchestrator"
      }
    }
  ],
  "edges": [
    {
      "id": "orchestrator-market",
      "source": "orchestrator",
      "target": "market",
      "animated": false,
      "type": "smoothstep"
    }
  ]
}
```

`status` values: `idle`, `running`, `done`, `error`

---

### `GET /api/screen`

Scan ~52 liquid US stocks and return the highest-potential picks.

**Query parameters**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `top_n` | integer | 5 | Number of top picks to return (max 20) |

**Response**

```json
{
  "universe_size": 52,
  "screened": 51,
  "methodology": "Composite score = 40% momentum + 30% RSI (oversold bias) + 30% 52w range upside",
  "top_picks": [
    {
      "ticker": "ORCL",
      "price": 155.52,
      "change_pct": 1.71,
      "week_52_high": 200.35,
      "week_52_low": 100.10,
      "range_position_pct": 55.4,
      "rsi_14": 44.2,
      "composite_score": 0.3886
    }
  ]
}
```

**Scoring formula**

```
composite = (daily_change_pct / 5.0 × 0.4)    # momentum
          + ((50 - rsi_14) / 50 × 0.3)         # RSI oversold bias
          + ((1 - range_position) × 0.3)        # 52w upside room
```

Higher composite = more potential. Negative composite = overextended / weak.

---

### `GET /api/tickers`

Searchable list of 110+ stocks with company names and sectors.

**Query parameters**

| Name | Type | Description |
|------|------|-------------|
| `q` | string | Filter by ticker, company name, or sector (optional) |

**Response**

```json
{
  "tickers": [
    {"ticker": "AAPL", "name": "Apple Inc.", "sector": "Technology"},
    {"ticker": "NVDA", "name": "NVIDIA Corporation", "sector": "Technology"},
    {"ticker": "JPM", "name": "JPMorgan Chase & Co.", "sector": "Financials"}
  ]
}
```

---

### `GET /api/monitor`

Health check for all data providers and last pipeline performance metrics.

**Response**

```json
{
  "overall": "healthy",
  "providers": {
    "finnhub": {"status": "ok", "latency_ms": 313.7},
    "fmp":     {"status": "ok", "latency_ms": 208.6},
    "stooq":   {"status": "ok", "latency_ms": 1457.1}
  },
  "redis": {"status": "ok", "latency_ms": 1.2},
  "last_pipeline": {
    "ticker": "AAPL",
    "total_elapsed_s": 8.4,
    "phase_times_s": {
      "phase1_historical_news": 2.1,
      "phase2_market": 0.9,
      "phase2b_debate": 4.2,
      "phase3_recommender": 1.1
    },
    "api_success_rate": 1.0,
    "api_calls": [
      {"provider": "stooq", "endpoint": "ohlcv_csv", "latency_ms": 820.0, "success": true}
    ]
  }
}
```

`overall`: `"healthy"` (all providers ok) or `"degraded"` (one or more failing)

---

### `GET /api/analysis/{ticker}/history`

Retrieve past analysis results for a ticker from PostgreSQL.

**Path parameter**

| Name | Type | Description |
|------|------|-------------|
| `ticker` | string | Stock symbol |

**Query parameters**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `limit` | integer | 10 | Max records to return |

**Response**

```json
{
  "ticker": "AAPL",
  "history": [
    {
      "ticker": "AAPL",
      "recommendation": {"action": "BUY", "composite_score": 67},
      "db_id": 42,
      "db_created_at": "2024-03-18T12:00:00"
    }
  ]
}
```

---

### `DELETE /api/analysis/{ticker}/cache`

Invalidate the Redis cache for a ticker, forcing a fresh analysis on the next call.

**Response**

```json
{"message": "Cache cleared for AAPL"}
```

---

### `GET /health`

Liveness probe.

```json
{"status": "ok", "service": "stock-research-platform", "version": "2.0.0"}
```

Also available at `/api/v1/health` for backwards compatibility.

---

### `GET /health/detailed`

Checks PostgreSQL connectivity in addition to the basic liveness probe.

```json
{
  "status": "ok",
  "components": {
    "database": "ok"
  }
}
```

---

## Agent Descriptions

| Agent | Phase | Role |
|-------|-------|------|
| **Orchestrator** | coordinator | Runs phases 1–4 in optimal order, wires all agent outputs |
| **Historical** | 1 (parallel) | Downloads 365-day OHLCV from Stooq; computes EMA/RSI/MACD/BB/ADX/OBV/VWAP via `ta` library |
| **News** | 1 (parallel) | Fetches 7-day company news from Finnhub; scores sentiment via gpt-4o-mini in batches of 10 |
| **Market** | 2 | Real-time quote from Finnhub + fundamentals (P/E, EPS, beta, 52w range) from FMP |
| **Bull** | 2b (parallel) | Constructs the strongest possible BUY thesis using OpenAI |
| **Bear** | 2b (parallel) | Constructs the strongest possible SELL thesis using OpenAI |
| **Moderator** | 2b | Evaluates both cases objectively and assigns scores |
| **Recommender** | 3 | Computes weighted composite → BUY/SELL/HOLD + allocation % + target/stop-loss |
| **Monitor** | 4 | Records per-phase latency and API success rates to Redis |

### Composite Score Weights

```
composite = 0.30 × technical_score
          + 0.25 × sentiment_score
          + 0.25 × fundamental_score
          + 0.20 × debate_score

BUY   if composite ≥ 65
HOLD  if 35 < composite < 65
SELL  if composite ≤ 35
```

---

## Data Sources

| Data | Provider | Notes |
|------|----------|-------|
| Real-time price / quote | **Finnhub** `/api/v1/quote` | c, d, dp fields |
| Company news | **Finnhub** `/api/v1/company-news` | 7-day window; RSS fallback |
| Company profile | **Finnhub** `/api/v1/stock/profile2` | sector, name |
| Fundamentals | **FMP** `/api/v3/key-metrics-ttm` + `/api/v3/quote` | P/E, EPS, beta, 52w |
| OHLCV history | **Stooq** CSV API | Free, no key, up to 20 yr |
| Sentiment scoring | **OpenAI** `gpt-4o-mini` | Batch of 10 headlines |

---

## Environment Variables

Copy `.env.example` to `.env` and fill in:

```env
# Required
OPENAI_API_KEY=sk-...

# Strongly recommended — live data
FINNHUB_API_KEY=...            # https://finnhub.io  (free tier: 60 req/min)
FMP_API_KEY=...                # https://financialmodelingprep.com  (free tier)

# Optional
ALPHA_VANTAGE_KEY=             # https://www.alphavantage.co
POLYGON_API_KEY=               # https://polygon.io
NEWS_API_KEY=                  # https://newsapi.org

# Infrastructure — default values match docker-compose.yml
DATABASE_URL=postgresql+asyncpg://srp:srp@postgres:5432/srp
REDIS_URL=redis://redis:6379/0
QDRANT_HOST=qdrant

# Model
OPENAI_MODEL=gpt-4o-mini

# Logging
LOG_LEVEL=info
```

---

## Claude Code Skills

This project includes built-in Claude Code slash commands:

| Command | Description |
|---------|-------------|
| `/analyze TICKER` | Test analysis pipeline for a ticker |
| `/screen` | Run stock screener against 52-stock universe |
| `/monitor` | Check live API provider health + last pipeline metrics |
| `/rebuild backend\|frontend\|all` | Rebuild and restart Docker services |

---

## Development (without Docker)

### Backend

```bash
cd backend
pip install -r requirements.txt

# Start infrastructure
docker run -d -p 5432:5432 -e POSTGRES_USER=srp -e POSTGRES_PASSWORD=srp -e POSTGRES_DB=srp postgres:16-alpine
docker run -d -p 6379:6379 redis:7-alpine

# Set env vars
export OPENAI_API_KEY=sk-...
export FINNHUB_API_KEY=...
export FMP_API_KEY=...
export DATABASE_URL=postgresql+asyncpg://srp:srp@localhost:5432/srp
export REDIS_URL=redis://localhost:6379/0
export QDRANT_HOST=localhost

# Run (single worker for local dev)
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# Opens at http://localhost:5173, proxied to backend at :8000
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend API | FastAPI 0.115, Python 3.11, Uvicorn |
| AI / LLM | OpenAI `gpt-4o-mini` |
| Market Data | Finnhub (quotes + news), FMP (fundamentals), Stooq (OHLCV) |
| Technical Analysis | `ta` library — EMA, RSI, MACD, ATR, BB, ADX, OBV, VWAP |
| News Sentiment | Finnhub company news + RSS fallback → OpenAI batch scoring |
| Message Bus | Redis pub/sub (MCP agent ↔ agent communication) |
| Database | PostgreSQL 16 + SQLAlchemy async |
| Vector Store | Qdrant (available for embeddings extensions) |
| Frontend | React 18, TypeScript, Vite 5 |
| Styling | Tailwind CSS 3 (dark mode `class` strategy) |
| Charts | lightweight-charts v4 (TradingView), Recharts |
| Agent Graph | @xyflow/react v12 (React Flow) |
| Containerisation | Docker, Docker Compose |
