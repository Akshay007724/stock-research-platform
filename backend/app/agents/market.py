from __future__ import annotations

import logging

from app.mcp.bus import MCPBus
from app.mcp.registry import registry
from app.schemas import AgentEvent, MarketData, OHLCV
from app.services import market_data as md_service

logger = logging.getLogger(__name__)


async def run(ticker: str, bus: MCPBus, ohlcv: list[OHLCV] | None = None) -> MarketData:
    """Market Research Agent: fetches fundamental and market data."""
    agent = "market"

    await registry.set_status(agent, "running", bus._redis, f"Starting market data fetch for {ticker}")
    await bus.publish(
        ticker,
        AgentEvent(
            agent_name=agent,
            event_type="start",
            message=f"Fetching market data for {ticker}",
        ),
    )

    try:
        await bus.publish(
            ticker,
            AgentEvent(
                agent_name=agent,
                event_type="progress",
                message="Querying Finnhub (real-time quote) + FMP (fundamentals)...",
            ),
        )

        market_data = await md_service.get_market_data(ticker, ohlcv=ohlcv)

        await bus.publish(
            ticker,
            AgentEvent(
                agent_name=agent,
                event_type="progress",
                message=f"Retrieved: Price=${market_data.price:.2f}, P/E={market_data.pe_ratio}, Beta={market_data.beta}",
                data={
                    "price": market_data.price,
                    "change_pct": market_data.change_pct,
                    "market_cap": market_data.market_cap,
                },
            ),
        )

        if market_data.sector:
            await bus.publish(
                ticker,
                AgentEvent(
                    agent_name=agent,
                    event_type="progress",
                    message=f"Sector: {market_data.sector} | Industry: {market_data.industry}",
                ),
            )

        await registry.set_status(agent, "done", bus._redis, f"Market data ready for {ticker}")
        await bus.publish(
            ticker,
            AgentEvent(
                agent_name=agent,
                event_type="complete",
                message=f"Market data collection complete for {ticker}",
                data={"ticker": ticker, "price": market_data.price},
            ),
        )

        return market_data

    except Exception as exc:
        logger.exception("Market agent failed for %s: %s", ticker, exc)
        await registry.set_status(agent, "error", bus._redis, str(exc))
        await bus.publish(
            ticker,
            AgentEvent(
                agent_name=agent,
                event_type="error",
                message=f"Market data fetch failed: {exc}",
            ),
        )
        # Return a minimal MarketData so orchestration can continue
        price = ohlcv[-1].close if ohlcv else 0.0
        change = (ohlcv[-1].close - ohlcv[-2].close) if ohlcv and len(ohlcv) >= 2 else 0.0
        change_pct = (change / ohlcv[-2].close * 100) if ohlcv and len(ohlcv) >= 2 and ohlcv[-2].close else 0.0
        volume = ohlcv[-1].volume if ohlcv else 0
        return MarketData(
            ticker=ticker.upper(),
            price=price,
            change=change,
            change_pct=change_pct,
            volume=volume,
        )
