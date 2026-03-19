from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime

from app.agents import debate as debate_agent
from app.agents import historical as historical_agent
from app.agents import market as market_agent
from app.agents import monitor as monitor_agent
from app.agents import news as news_agent
from app.agents import recommender as recommender_agent
from app.agents.monitor import PipelineMetrics, track_phase
from app.mcp.bus import MCPBus
from app.mcp.registry import registry
from app.schemas import AgentEvent, AnalysisResult

logger = logging.getLogger(__name__)

_CACHE_TTL = 3600  # 1 hour


async def run_analysis(ticker: str, redis, bus: MCPBus) -> AnalysisResult:
    """
    Orchestrates all agents in optimal parallel order:
    Phase 1 (parallel): historical + news (to get OHLCV before market_data)
    Phase 2 (parallel): market_data (uses OHLCV) + debate (needs market_data + indicators)
    Phase 3: recommender (needs all)
    """
    ticker = ticker.upper()
    orchestrator = "orchestrator"
    metrics = PipelineMetrics(ticker)

    await registry.reset_all(redis)
    await registry.set_status(orchestrator, "running", redis, f"Starting analysis for {ticker}")

    await bus.publish(
        ticker,
        AgentEvent(
            agent_name=orchestrator,
            event_type="start",
            message=f"Starting full analysis pipeline for {ticker}",
            data={"ticker": ticker, "phase": "init"},
        ),
    )

    # ── Phase 1: Historical + News in parallel ──────────────────────────────
    await bus.publish(
        ticker,
        AgentEvent(
            agent_name=orchestrator,
            event_type="progress",
            message="Phase 1: Fetching historical data and news concurrently",
            data={"phase": 1},
        ),
    )

    async with track_phase(metrics, "phase1_historical_news"):
        historical_task = asyncio.create_task(historical_agent.run(ticker, bus))
        news_task = asyncio.create_task(news_agent.run(ticker, bus))

        try:
            (ohlcv, indicators), (news_articles, sentiment) = await asyncio.gather(
                historical_task, news_task, return_exceptions=False
            )
        except Exception as exc:
            logger.exception("Phase 1 failed for %s: %s", ticker, exc)
            await bus.publish(
                ticker,
                AgentEvent(
                    agent_name=orchestrator,
                    event_type="error",
                    message=f"Phase 1 critical failure: {exc}",
                ),
            )
            raise

    await registry.record_data_flow("historical", "orchestrator", redis)
    await registry.record_data_flow("news", "orchestrator", redis)

    # ── Phase 2: Market data ────────────────────────────────────────────────
    await bus.publish(
        ticker,
        AgentEvent(
            agent_name=orchestrator,
            event_type="progress",
            message="Phase 2: Fetching market fundamentals and running bull/bear debate",
            data={"phase": 2},
        ),
    )

    async with track_phase(metrics, "phase2_market"):
        market_data = await market_agent.run(ticker, bus, ohlcv=ohlcv)

    await registry.record_data_flow("market", "orchestrator", redis)

    # Now run debate with actual market_data
    await bus.publish(
        ticker,
        AgentEvent(
            agent_name=orchestrator,
            event_type="progress",
            message="Phase 2b: Running bull vs bear debate with market data",
            data={"phase": "2b"},
        ),
    )

    async with track_phase(metrics, "phase2b_debate"):
        debate_result = await debate_agent.run(ticker, market_data, indicators, bus)
    await registry.record_data_flow("debate_moderator", "orchestrator", redis)

    # ── Phase 3: Recommender ────────────────────────────────────────────────
    await bus.publish(
        ticker,
        AgentEvent(
            agent_name=orchestrator,
            event_type="progress",
            message="Phase 3: Generating final recommendation",
            data={"phase": 3},
        ),
    )

    async with track_phase(metrics, "phase3_recommender"):
        recommendation = await recommender_agent.run(
            ticker, market_data, indicators, sentiment, debate_result, bus
        )
    await registry.record_data_flow("recommender", "orchestrator", redis)

    # ── Phase 4: Monitor — record pipeline metrics ──────────────────────────
    await monitor_agent.run(ticker, bus, metrics)
    await registry.record_data_flow("monitor", "orchestrator", redis)

    # ── Collect agent log from bus history ─────────────────────────────────
    agent_log = await bus.get_history(ticker, limit=100)

    result = AnalysisResult(
        ticker=ticker,
        market_data=market_data,
        ohlcv=ohlcv,
        indicators=indicators,
        news=news_articles,
        debate=debate_result,
        recommendation=recommendation,
        agent_log=agent_log,
    )

    # Cache in Redis
    try:
        cache_key = f"analysis:{ticker}"
        await redis.set(cache_key, result.model_dump_json(), ex=_CACHE_TTL)
    except Exception as exc:
        logger.warning("Failed to cache analysis result: %s", exc)

    await registry.set_status(orchestrator, "done", redis, f"Analysis complete for {ticker}")
    await bus.publish(
        ticker,
        AgentEvent(
            agent_name=orchestrator,
            event_type="complete",
            message=f"Analysis pipeline complete for {ticker} — recommendation: {recommendation.action}",
            data={
                "action": recommendation.action,
                "confidence": recommendation.composite_score,
                "ticker": ticker,
            },
        ),
    )

    return result


async def get_cached_analysis(ticker: str, redis) -> AnalysisResult | None:
    """Check Redis cache for a recent analysis result."""
    cache_key = f"analysis:{ticker.upper()}"
    try:
        raw = await redis.get(cache_key)
        if raw:
            return AnalysisResult.model_validate_json(raw)
    except Exception as exc:
        logger.warning("Cache read failed for %s: %s", ticker, exc)
    return None
