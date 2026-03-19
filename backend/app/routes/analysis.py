from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.monitor import run_health_check
from app.agents.orchestrator import get_cached_analysis, run_analysis
from app.config import settings
from app.database import get_analysis_history, get_db, get_redis, save_analysis
from app.mcp.bus import MCPBus
from app.mcp.registry import registry
from app.schemas import AnalysisResult

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/api/analyze/{ticker}", response_model=AnalysisResult)
async def analyze(
    ticker: str,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    ticker = ticker.upper().strip()
    # Allow letters, digits, dots, and hyphens (e.g. BRK.B, BF-B); max 10 chars
    import re as _re
    if not ticker or not _re.match(r'^[A-Z0-9.\-]{1,10}$', ticker):
        raise HTTPException(status_code=400, detail=f"Invalid ticker symbol: {ticker}")

    # Check Redis cache first
    cached = await get_cached_analysis(ticker, redis)
    if cached:
        logger.info("Returning cached analysis for %s", ticker)
        return cached

    bus = MCPBus(redis)

    try:
        result = await run_analysis(ticker, redis, bus)
    except Exception as exc:
        logger.exception("Analysis failed for %s: %s", ticker, exc)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}")

    # Persist to PostgreSQL
    try:
        await save_analysis(db, ticker, result.model_dump_json())
    except Exception as exc:
        logger.warning("Failed to persist analysis to DB for %s: %s", ticker, exc)

    return result


@router.get("/api/analysis/{ticker}/history")
async def get_ticker_history(
    ticker: str,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
):
    ticker = ticker.upper().strip()
    history = await get_analysis_history(db, ticker, limit=limit)
    return {"ticker": ticker, "history": history}


@router.get("/api/agents/status")
async def agents_status(redis=Depends(get_redis)):
    """Returns current agent statuses for the React Flow graph."""
    all_agents = await registry.get_all(redis)

    nodes = []
    edges = []

    positions = {
        "orchestrator": {"x": 400, "y": 0},
        "market": {"x": 100, "y": 150},
        "historical": {"x": 400, "y": 150},
        "news": {"x": 700, "y": 150},
        "debate_bull": {"x": 200, "y": 300},
        "debate_bear": {"x": 500, "y": 300},
        "debate_moderator": {"x": 350, "y": 450},
        "recommender": {"x": 400, "y": 600},
    }

    for agent_id, agent_data in all_agents.items():
        nodes.append(
            {
                "id": agent_id,
                "type": "agentNode",
                "position": positions.get(agent_id, {"x": 0, "y": 0}),
                "data": {
                    "label": agent_data["name"],
                    "status": agent_data["status"],
                    "last_event": agent_data.get("last_event"),
                    "agent_id": agent_id,
                },
            }
        )

        for conn in agent_data.get("connections", []):
            edges.append(
                {
                    "id": f"{agent_id}-{conn}",
                    "source": agent_id,
                    "target": conn,
                    "animated": agent_data["status"] == "running",
                    "type": "smoothstep",
                }
            )

    return {"nodes": nodes, "edges": edges}


@router.get("/api/monitor")
async def get_monitor(redis=Depends(get_redis)):
    """Real-time health check: API providers, Redis, last pipeline metrics."""
    return await run_health_check(redis)


# ── Ticker Lookup ──────────────────────────────────────────────────────────────

_TICKER_LIST = [
    # Technology
    {"ticker": "AAPL", "name": "Apple Inc.", "sector": "Technology"},
    {"ticker": "MSFT", "name": "Microsoft Corporation", "sector": "Technology"},
    {"ticker": "GOOGL", "name": "Alphabet Inc. (Google)", "sector": "Technology"},
    {"ticker": "AMZN", "name": "Amazon.com Inc.", "sector": "Consumer Discretionary"},
    {"ticker": "NVDA", "name": "NVIDIA Corporation", "sector": "Technology"},
    {"ticker": "META", "name": "Meta Platforms Inc.", "sector": "Technology"},
    {"ticker": "TSLA", "name": "Tesla Inc.", "sector": "Consumer Discretionary"},
    {"ticker": "AVGO", "name": "Broadcom Inc.", "sector": "Technology"},
    {"ticker": "AMD", "name": "Advanced Micro Devices", "sector": "Technology"},
    {"ticker": "ORCL", "name": "Oracle Corporation", "sector": "Technology"},
    {"ticker": "CRM", "name": "Salesforce Inc.", "sector": "Technology"},
    {"ticker": "ADBE", "name": "Adobe Inc.", "sector": "Technology"},
    {"ticker": "INTC", "name": "Intel Corporation", "sector": "Technology"},
    {"ticker": "QCOM", "name": "Qualcomm Inc.", "sector": "Technology"},
    {"ticker": "TXN", "name": "Texas Instruments Inc.", "sector": "Technology"},
    {"ticker": "MU", "name": "Micron Technology Inc.", "sector": "Technology"},
    {"ticker": "AMAT", "name": "Applied Materials Inc.", "sector": "Technology"},
    {"ticker": "LRCX", "name": "Lam Research Corporation", "sector": "Technology"},
    {"ticker": "KLAC", "name": "KLA Corporation", "sector": "Technology"},
    {"ticker": "NOW", "name": "ServiceNow Inc.", "sector": "Technology"},
    {"ticker": "SNOW", "name": "Snowflake Inc.", "sector": "Technology"},
    {"ticker": "PLTR", "name": "Palantir Technologies", "sector": "Technology"},
    {"ticker": "PANW", "name": "Palo Alto Networks", "sector": "Technology"},
    {"ticker": "CRWD", "name": "CrowdStrike Holdings", "sector": "Technology"},
    {"ticker": "NET", "name": "Cloudflare Inc.", "sector": "Technology"},
    {"ticker": "ZS", "name": "Zscaler Inc.", "sector": "Technology"},
    {"ticker": "DDOG", "name": "Datadog Inc.", "sector": "Technology"},
    {"ticker": "TEAM", "name": "Atlassian Corporation", "sector": "Technology"},
    {"ticker": "SHOP", "name": "Shopify Inc.", "sector": "Technology"},
    {"ticker": "COIN", "name": "Coinbase Global Inc.", "sector": "Technology"},
    # Financials
    {"ticker": "JPM", "name": "JPMorgan Chase & Co.", "sector": "Financials"},
    {"ticker": "BAC", "name": "Bank of America Corp.", "sector": "Financials"},
    {"ticker": "GS", "name": "Goldman Sachs Group", "sector": "Financials"},
    {"ticker": "MS", "name": "Morgan Stanley", "sector": "Financials"},
    {"ticker": "WFC", "name": "Wells Fargo & Co.", "sector": "Financials"},
    {"ticker": "C", "name": "Citigroup Inc.", "sector": "Financials"},
    {"ticker": "V", "name": "Visa Inc.", "sector": "Financials"},
    {"ticker": "MA", "name": "Mastercard Inc.", "sector": "Financials"},
    {"ticker": "PYPL", "name": "PayPal Holdings Inc.", "sector": "Financials"},
    {"ticker": "SQ", "name": "Block Inc. (Square)", "sector": "Financials"},
    {"ticker": "AXP", "name": "American Express Co.", "sector": "Financials"},
    {"ticker": "BRK.B", "name": "Berkshire Hathaway B", "sector": "Financials"},
    {"ticker": "SCHW", "name": "Charles Schwab Corp.", "sector": "Financials"},
    {"ticker": "BLK", "name": "BlackRock Inc.", "sector": "Financials"},
    {"ticker": "SPGI", "name": "S&P Global Inc.", "sector": "Financials"},
    # Healthcare
    {"ticker": "JNJ", "name": "Johnson & Johnson", "sector": "Healthcare"},
    {"ticker": "UNH", "name": "UnitedHealth Group Inc.", "sector": "Healthcare"},
    {"ticker": "LLY", "name": "Eli Lilly and Co.", "sector": "Healthcare"},
    {"ticker": "PFE", "name": "Pfizer Inc.", "sector": "Healthcare"},
    {"ticker": "ABBV", "name": "AbbVie Inc.", "sector": "Healthcare"},
    {"ticker": "MRK", "name": "Merck & Co. Inc.", "sector": "Healthcare"},
    {"ticker": "AMGN", "name": "Amgen Inc.", "sector": "Healthcare"},
    {"ticker": "GILD", "name": "Gilead Sciences Inc.", "sector": "Healthcare"},
    {"ticker": "REGN", "name": "Regeneron Pharmaceuticals", "sector": "Healthcare"},
    {"ticker": "MRNA", "name": "Moderna Inc.", "sector": "Healthcare"},
    {"ticker": "ISRG", "name": "Intuitive Surgical Inc.", "sector": "Healthcare"},
    {"ticker": "CVS", "name": "CVS Health Corporation", "sector": "Healthcare"},
    {"ticker": "BMY", "name": "Bristol-Myers Squibb", "sector": "Healthcare"},
    {"ticker": "TMO", "name": "Thermo Fisher Scientific", "sector": "Healthcare"},
    {"ticker": "ABT", "name": "Abbott Laboratories", "sector": "Healthcare"},
    # Energy
    {"ticker": "XOM", "name": "Exxon Mobil Corporation", "sector": "Energy"},
    {"ticker": "CVX", "name": "Chevron Corporation", "sector": "Energy"},
    {"ticker": "COP", "name": "ConocoPhillips", "sector": "Energy"},
    {"ticker": "SLB", "name": "SLB (Schlumberger)", "sector": "Energy"},
    {"ticker": "EOG", "name": "EOG Resources Inc.", "sector": "Energy"},
    # Consumer
    {"ticker": "WMT", "name": "Walmart Inc.", "sector": "Consumer Staples"},
    {"ticker": "COST", "name": "Costco Wholesale Corp.", "sector": "Consumer Staples"},
    {"ticker": "HD", "name": "Home Depot Inc.", "sector": "Consumer Discretionary"},
    {"ticker": "TGT", "name": "Target Corporation", "sector": "Consumer Staples"},
    {"ticker": "NKE", "name": "Nike Inc.", "sector": "Consumer Discretionary"},
    {"ticker": "SBUX", "name": "Starbucks Corporation", "sector": "Consumer Discretionary"},
    {"ticker": "MCD", "name": "McDonald's Corporation", "sector": "Consumer Discretionary"},
    {"ticker": "LOW", "name": "Lowe's Companies Inc.", "sector": "Consumer Discretionary"},
    {"ticker": "TJX", "name": "TJX Companies Inc.", "sector": "Consumer Discretionary"},
    {"ticker": "PG", "name": "Procter & Gamble Co.", "sector": "Consumer Staples"},
    {"ticker": "KO", "name": "Coca-Cola Company", "sector": "Consumer Staples"},
    {"ticker": "PEP", "name": "PepsiCo Inc.", "sector": "Consumer Staples"},
    {"ticker": "MDLZ", "name": "Mondelez International", "sector": "Consumer Staples"},
    # Communication / Media
    {"ticker": "NFLX", "name": "Netflix Inc.", "sector": "Communication Services"},
    {"ticker": "DIS", "name": "Walt Disney Company", "sector": "Communication Services"},
    {"ticker": "SPOT", "name": "Spotify Technology SA", "sector": "Communication Services"},
    {"ticker": "T", "name": "AT&T Inc.", "sector": "Communication Services"},
    {"ticker": "VZ", "name": "Verizon Communications", "sector": "Communication Services"},
    {"ticker": "CMCSA", "name": "Comcast Corporation", "sector": "Communication Services"},
    # Transport / Travel
    {"ticker": "UBER", "name": "Uber Technologies Inc.", "sector": "Industrials"},
    {"ticker": "LYFT", "name": "Lyft Inc.", "sector": "Industrials"},
    {"ticker": "ABNB", "name": "Airbnb Inc.", "sector": "Consumer Discretionary"},
    {"ticker": "DASH", "name": "DoorDash Inc.", "sector": "Consumer Discretionary"},
    {"ticker": "UAL", "name": "United Airlines Holdings", "sector": "Industrials"},
    {"ticker": "DAL", "name": "Delta Air Lines Inc.", "sector": "Industrials"},
    # Industrials
    {"ticker": "BA", "name": "Boeing Company", "sector": "Industrials"},
    {"ticker": "CAT", "name": "Caterpillar Inc.", "sector": "Industrials"},
    {"ticker": "GE", "name": "GE Aerospace", "sector": "Industrials"},
    {"ticker": "HON", "name": "Honeywell International", "sector": "Industrials"},
    {"ticker": "RTX", "name": "RTX Corporation (Raytheon)", "sector": "Industrials"},
    {"ticker": "LMT", "name": "Lockheed Martin Corp.", "sector": "Industrials"},
    {"ticker": "DE", "name": "Deere & Company", "sector": "Industrials"},
    {"ticker": "UPS", "name": "United Parcel Service", "sector": "Industrials"},
    {"ticker": "FDX", "name": "FedEx Corporation", "sector": "Industrials"},
    # Utilities / Real Estate
    {"ticker": "NEE", "name": "NextEra Energy Inc.", "sector": "Utilities"},
    {"ticker": "DUK", "name": "Duke Energy Corporation", "sector": "Utilities"},
    {"ticker": "AMT", "name": "American Tower Corp.", "sector": "Real Estate"},
    {"ticker": "PLD", "name": "Prologis Inc.", "sector": "Real Estate"},
    # Materials
    {"ticker": "LIN", "name": "Linde PLC", "sector": "Materials"},
    {"ticker": "APD", "name": "Air Products & Chemicals", "sector": "Materials"},
    {"ticker": "SHW", "name": "Sherwin-Williams Co.", "sector": "Materials"},
    {"ticker": "FCX", "name": "Freeport-McMoRan Inc.", "sector": "Materials"},
    # ETFs
    {"ticker": "SPY", "name": "SPDR S&P 500 ETF", "sector": "ETF"},
    {"ticker": "QQQ", "name": "Invesco QQQ ETF (NASDAQ 100)", "sector": "ETF"},
    {"ticker": "IWM", "name": "iShares Russell 2000 ETF", "sector": "ETF"},
    {"ticker": "VTI", "name": "Vanguard Total Stock Market ETF", "sector": "ETF"},
    {"ticker": "GLD", "name": "SPDR Gold Shares ETF", "sector": "ETF"},
]


@router.get("/api/tickers")
async def get_tickers(q: str = ""):
    """Return searchable list of stocks with names and sectors."""
    q = q.strip().lower()
    if not q:
        return {"tickers": _TICKER_LIST}
    filtered = [
        t for t in _TICKER_LIST
        if q in t["ticker"].lower() or q in t["name"].lower() or q in t["sector"].lower()
    ]
    return {"tickers": filtered}


@router.delete("/api/analysis/{ticker}/cache")
async def clear_cache(ticker: str, redis=Depends(get_redis)):
    """Clear cached analysis for a ticker."""
    ticker = ticker.upper()
    await redis.delete(f"analysis:{ticker}")
    return {"message": f"Cache cleared for {ticker}"}


# ── Stock Screener ─────────────────────────────────────────────────────────────

_SCREEN_UNIVERSE = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AVGO", "AMD",
    "ORCL", "CRM", "ADBE", "INTC", "QCOM", "TXN", "MU", "AMAT", "LRCX",
    "JPM", "BAC", "GS", "MS", "V", "MA", "PYPL", "SQ",
    "JNJ", "UNH", "LLY", "PFE", "ABBV", "MRK",
    "XOM", "CVX", "NEE", "LIN",
    "AMGN", "GILD", "REGN", "MRNA",
    "NFLX", "DIS", "SPOT", "UBER", "LYFT", "ABNB", "DASH",
    "HD", "WMT", "COST", "TGT", "NKE",
]


async def _screen_ticker(ticker: str, client: httpx.AsyncClient) -> dict[str, Any] | None:
    """Fetch Finnhub quote + basic metrics for one ticker."""
    try:
        token = settings.finnhub_api_key
        if not token:
            return None

        quote_resp, metrics_resp = await asyncio.gather(
            client.get("https://finnhub.io/api/v1/quote", params={"symbol": ticker, "token": token}),
            client.get("https://finnhub.io/api/v1/stock/metric", params={"symbol": ticker, "metric": "all", "token": token}),
        )
        quote = quote_resp.json() if quote_resp.status_code == 200 else {}
        metric_data = metrics_resp.json().get("metric", {}) if metrics_resp.status_code == 200 else {}

        price = quote.get("c", 0)
        change_pct = quote.get("dp", 0)
        if not price or price == 0:
            return None

        prev_close = quote.get("pc", price)
        week_high = metric_data.get("52WeekHigh") or price
        week_low = metric_data.get("52WeekLow") or price

        # Position within 52-week range (0=at low, 1=at high) — lower = more upside
        range_pct = ((price - week_low) / (week_high - week_low)) if (week_high - week_low) > 0 else 0.5

        # RSI (14-day) from Finnhub metrics
        rsi = metric_data.get("rsi14") or 50.0

        # Composite score: favor momentum (positive change), oversold RSI, low in range
        momentum_score = min(max(change_pct / 5.0, -1.0), 1.0)  # normalise ±5% → ±1
        rsi_score = (50 - rsi) / 50.0  # negative at overbought, positive at oversold
        range_score = 1.0 - range_pct  # more upside = higher score

        composite = (momentum_score * 0.4) + (rsi_score * 0.3) + (range_score * 0.3)

        return {
            "ticker": ticker,
            "price": price,
            "change_pct": round(change_pct, 2),
            "week_52_high": week_high,
            "week_52_low": week_low,
            "range_position_pct": round(range_pct * 100, 1),
            "rsi_14": round(rsi, 1),
            "composite_score": round(composite, 4),
        }
    except Exception as exc:
        logger.debug("Screener skip %s: %s", ticker, exc)
        return None


@router.get("/api/screen")
async def screen_stocks(top_n: int = 5):
    """
    Scan the liquid stock universe and return the top N highest-potential picks
    based on momentum, RSI oversold signal, and 52-week range position.
    """
    top_n = min(max(top_n, 1), 20)

    async with httpx.AsyncClient(timeout=20) as client:
        tasks = [_screen_ticker(t, client) for t in _SCREEN_UNIVERSE]
        results = await asyncio.gather(*tasks)

    valid = [r for r in results if r is not None]
    valid.sort(key=lambda x: x["composite_score"], reverse=True)

    return {
        "universe_size": len(_SCREEN_UNIVERSE),
        "screened": len(valid),
        "top_picks": valid[:top_n],
        "methodology": "Composite score = 40% momentum + 30% RSI (oversold bias) + 30% 52w range upside",
    }
