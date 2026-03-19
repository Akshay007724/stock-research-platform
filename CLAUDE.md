# Stock Research Platform — Claude Code Guide

## Project Overview
AI-powered stock research platform with multi-agent MCP architecture.
- **Frontend**: React 18 + TypeScript + Vite + TailwindCSS (dark mode)
- **Backend**: FastAPI (Python 3.11) + async SQLAlchemy + Redis pub/sub
- **Agents**: 9 agents — Orchestrator, Market, Historical, News, Bull, Bear, Moderator, Recommender, Monitor
- **Data**: Finnhub (real-time quotes + news), FMP (fundamentals), Stooq CSV (OHLCV)
- **LLM**: gpt-4o-mini for all agent reasoning (lightweight, fast, precise)

## Architecture

```
User → SearchBar → POST /api/analyze/{ticker}
                     │
            Orchestrator (coordinates phases)
           ┌─────────┴──────────┐
     Historical+News         Market (Finnhub+FMP)
     (Phase 1, parallel)     (Phase 2)
           │                     │
     Debate Bull+Bear         Moderator
     (Phase 2b)                  │
                          Recommender (Phase 3)
                                 │
                          Monitor (Phase 4, metrics)
```

## Key Files
- `backend/app/agents/` — all agent modules
- `backend/app/agents/orchestrator.py` — pipeline coordination + phase timing
- `backend/app/agents/monitor.py` — performance monitoring, `/api/monitor` health checks
- `backend/app/mcp/registry.py` — agent status registry (Redis-backed)
- `backend/app/mcp/bus.py` — Redis pub/sub message bus
- `backend/app/services/market_data.py` — Finnhub quotes, FMP fundamentals, Stooq OHLCV
- `backend/app/services/news_service.py` — Finnhub company news + RSS fallback
- `backend/app/routes/analysis.py` — all REST endpoints + screener + tickers
- `frontend/src/components/SearchBar.tsx` — searchable combobox with 100+ tickers
- `frontend/src/components/MCPGraph.tsx` — live agent graph (React Flow)

## API Endpoints
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/analyze/{ticker}` | Run full analysis pipeline |
| GET | `/api/analysis/{ticker}/history` | Past analyses |
| GET | `/api/agents/status` | Live agent graph data |
| GET | `/api/screen?top_n=5` | Stock screener (50-stock universe) |
| GET | `/api/tickers?q=` | Searchable ticker list (100+ stocks) |
| GET | `/api/monitor` | Health check + pipeline metrics |
| DELETE | `/api/analysis/{ticker}/cache` | Clear Redis cache |
| GET | `/api/stream/{ticker}` | SSE agent event stream |

## Development Commands

```bash
# Start all services
docker compose up -d

# Rebuild backend after Python changes
docker compose build --no-cache backend && docker compose up -d backend

# Rebuild frontend after TypeScript/React changes
docker compose build --no-cache frontend && docker compose up -d frontend

# View logs
docker compose logs -f backend
docker compose logs -f frontend

# Backend only (local dev)
cd backend && uvicorn app.main:app --reload --port 8000

# Frontend only (local dev)
cd frontend && npm run dev
```

## Financial Domain Rules

### Data Sources (in priority order)
1. **Real-time prices/quotes** → Finnhub `/api/v1/quote` (c, d, dp fields)
2. **Company news** → Finnhub `/api/v1/company-news` (primary), RSS (fallback)
3. **Fundamentals** → FMP `/api/v3/key-metrics-ttm/{ticker}` + `/api/v3/quote/{ticker}`
4. **OHLCV history** → Stooq CSV (no key, reliable, up to 20yr history)
5. **Company profile** → Finnhub `/api/v1/stock/profile2`

### DO NOT use Yahoo Finance quoteSummary — rate-limited in containers.
### DO NOT use pandas-ta — removed from PyPI. Use `ta==0.11.0` instead.

### Technical Indicators (ta library)
```python
from ta.trend import EMAIndicator, MACD, ADXIndicator
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands, AverageTrueRange
from ta.volume import OnBalanceVolumeIndicator
```
See `backend/app/services/indicators.py` for full implementation.

### Agent Development Pattern
Every agent must:
1. Call `registry.set_status(agent_id, "running", redis, message)` at start
2. Publish `AgentEvent` with `event_type="start"` to the bus
3. Publish progress events with relevant data
4. Call `registry.set_status(agent_id, "done", redis, message)` at end
5. Publish `AgentEvent` with `event_type="complete"` to the bus
6. Handle exceptions — publish `event_type="error"` and re-raise or return fallback

### Screener Universe
~50 liquid US stocks across sectors. See `_SCREEN_UNIVERSE` in `routes/analysis.py`.
Score = 40% momentum + 30% RSI (oversold bias) + 30% 52-week range upside.

### Caching Strategy
- Analysis results → Redis, 1-hour TTL (`analysis:{ticker}`)
- Pipeline metrics → Redis, 1-hour TTL (`monitor:pipeline_metrics`)
- Agent status → Redis, 1-hour TTL per agent

## TypeScript / Frontend Rules
- All API types in `frontend/src/types/index.ts`
- API calls via `frontend/src/lib/api.ts`
- `AgentNodeData` must extend `Record<string, unknown>` (React Flow requirement)
- Charts: lightweight-charts (candlestick), Recharts (sentiment timeline)
- Agent graph: `@xyflow/react` v12

## Docker / Infrastructure
- Qdrant healthcheck: `bash -c 'exec 3<>/dev/tcp/localhost/6333'` (no curl in image)
- Backend depends on postgres + redis + qdrant (all healthy)
- Frontend nginx proxies `/api/*` → backend:8000, `/ws` → ws://backend:8000
- `version:` field removed from docker-compose.yml (deprecated)

## Environment Variables
```
OPENAI_API_KEY=      # Required for all agents
FINNHUB_API_KEY=     # Real-time quotes + company news
FMP_API_KEY=         # Fundamentals, P/E, beta, 52w range
DATABASE_URL=        # PostgreSQL (set auto in compose)
REDIS_URL=           # Redis (set auto in compose)
QDRANT_HOST=         # Qdrant (set auto in compose)
OPENAI_MODEL=gpt-4o-mini
```

## Code Quality
- Python: `ruff` for linting, `mypy --strict` for type checking
- TypeScript: `tsc --noEmit` must pass before frontend build
- All new agents must be registered in `backend/app/mcp/registry.py`
- Never skip `registry.reset_all()` at start of a pipeline run
