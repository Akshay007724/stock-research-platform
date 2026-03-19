from __future__ import annotations

import logging

from app.mcp.bus import MCPBus
from app.mcp.registry import registry
from app.schemas import AgentEvent, OHLCV, TechnicalIndicators
from app.services.indicators import compute_indicators
from app.services.market_data import get_ohlcv

logger = logging.getLogger(__name__)


async def run(ticker: str, bus: MCPBus) -> tuple[list[OHLCV], TechnicalIndicators]:
    """Historical Analysis Agent: fetches OHLCV and computes technical indicators."""
    agent = "historical"

    await registry.set_status(agent, "running", bus._redis, f"Fetching historical data for {ticker}")
    await bus.publish(
        ticker,
        AgentEvent(
            agent_name=agent,
            event_type="start",
            message=f"Starting historical analysis for {ticker}",
        ),
    )

    try:
        await bus.publish(
            ticker,
            AgentEvent(
                agent_name=agent,
                event_type="progress",
                message="Fetching 365 days of OHLCV data from Stooq...",
            ),
        )

        ohlcv = await get_ohlcv(ticker, days=365)

        await bus.publish(
            ticker,
            AgentEvent(
                agent_name=agent,
                event_type="progress",
                message=f"Retrieved {len(ohlcv)} trading days of price data",
                data={"bars": len(ohlcv)},
            ),
        )

        await bus.publish(
            ticker,
            AgentEvent(
                agent_name=agent,
                event_type="progress",
                message="Computing EMA 9/21/50/200...",
            ),
        )

        await bus.publish(
            ticker,
            AgentEvent(
                agent_name=agent,
                event_type="progress",
                message="Computing RSI-14, MACD, ATR, Bollinger Bands...",
            ),
        )

        await bus.publish(
            ticker,
            AgentEvent(
                agent_name=agent,
                event_type="progress",
                message="Detecting support and resistance levels...",
            ),
        )

        indicators, _df = compute_indicators(ohlcv)

        trend_str = "Uptrend" if indicators.trend_direction == 1 else "Downtrend"
        rsi_str = f"RSI={indicators.rsi_14:.1f}" if indicators.rsi_14 is not None else "RSI=N/A"
        macd_str = f"MACD={indicators.macd:.3f}" if indicators.macd is not None else "MACD=N/A"

        await bus.publish(
            ticker,
            AgentEvent(
                agent_name=agent,
                event_type="progress",
                message=f"Technical summary: {trend_str} | {rsi_str} | {macd_str}",
                data={
                    "trend": trend_str,
                    "rsi": indicators.rsi_14,
                    "support": indicators.support,
                    "resistance": indicators.resistance,
                },
            ),
        )

        await registry.set_status(agent, "done", bus._redis, f"Historical analysis complete for {ticker}")
        await bus.publish(
            ticker,
            AgentEvent(
                agent_name=agent,
                event_type="complete",
                message=f"Historical analysis complete: {len(ohlcv)} bars analyzed",
            ),
        )

        return ohlcv, indicators

    except Exception as exc:
        logger.exception("Historical agent failed for %s: %s", ticker, exc)
        await registry.set_status(agent, "error", bus._redis, str(exc))
        await bus.publish(
            ticker,
            AgentEvent(
                agent_name=agent,
                event_type="error",
                message=f"Historical analysis failed: {exc}",
            ),
        )
        raise
