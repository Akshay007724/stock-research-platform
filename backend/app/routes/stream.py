from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

from app.database import get_redis
from app.mcp.bus import MCPBus

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/api/stream/{ticker}")
async def stream_events(ticker: str, redis=Depends(get_redis)):
    """
    SSE endpoint: streams real-time agent events for a given ticker.
    Uses Redis pub/sub so events arrive even if analysis started before SSE connected.
    """
    ticker = ticker.upper().strip()
    bus = MCPBus(redis)

    async def event_generator():
        # First, send any historical events
        try:
            history = await bus.get_history(ticker, limit=50)
            for event in history:
                yield {"data": event.model_dump_json()}
        except Exception as exc:
            logger.warning("Failed to send history for %s: %s", ticker, exc)

        # Then subscribe for live events
        try:
            timeout_count = 0
            async for event in bus.subscribe(ticker):
                yield {"data": event.model_dump_json()}
                timeout_count = 0
                if event.event_type == "complete" and event.agent_name == "orchestrator":
                    break
        except asyncio.CancelledError:
            logger.info("SSE stream cancelled for %s", ticker)
        except Exception as exc:
            logger.warning("SSE stream error for %s: %s", ticker, exc)

    return EventSourceResponse(event_generator())
