from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from app.database import get_redis
from app.mcp.bus import MCPBus

router = APIRouter()
logger = logging.getLogger(__name__)

_PRICE_INTERVAL = 30  # seconds


@router.websocket("/ws/{ticker}")
async def websocket_endpoint(websocket: WebSocket, ticker: str, redis=Depends(get_redis)):
    """
    WebSocket endpoint: streams live price updates and agent events.
    Every 30 seconds, fetches latest quote and sends to client.
    Also forwards any new AgentEvents for this ticker.
    """
    await websocket.accept()
    ticker = ticker.upper()
    bus = MCPBus(redis)

    logger.info("WebSocket connected for %s", ticker)

    async def send_price_update():
        """Periodically fetch and send latest price."""
        while True:
            try:
                # Try to get cached analysis price
                cache_key = f"analysis:{ticker}"
                raw = await redis.get(cache_key)
                if raw:
                    data = json.loads(raw)
                    market_data = data.get("market_data", {})
                    msg = {
                        "type": "price_update",
                        "ticker": ticker,
                        "price": market_data.get("price"),
                        "change": market_data.get("change"),
                        "change_pct": market_data.get("change_pct"),
                        "volume": market_data.get("volume"),
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                    await websocket.send_json(msg)
            except Exception as exc:
                logger.debug("Price update failed for %s: %s", ticker, exc)

            await asyncio.sleep(_PRICE_INTERVAL)

    async def forward_events():
        """Forward new agent events from Redis pub/sub."""
        try:
            async for event in bus.subscribe(ticker):
                try:
                    await websocket.send_json(
                        {
                            "type": "agent_event",
                            "event": event.model_dump(),
                        }
                    )
                except Exception:
                    break
        except Exception as exc:
            logger.debug("Event forwarding ended for %s: %s", ticker, exc)

    # Send initial connected message
    await websocket.send_json({"type": "connected", "ticker": ticker})

    # Run both tasks concurrently
    price_task = asyncio.create_task(send_price_update())
    events_task = asyncio.create_task(forward_events())

    try:
        # Keep alive until client disconnects
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)
                # Handle ping/pong
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                # Send heartbeat
                try:
                    await websocket.send_json({"type": "heartbeat", "timestamp": datetime.utcnow().isoformat()})
                except Exception:
                    break
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for %s", ticker)
    except Exception as exc:
        logger.warning("WebSocket error for %s: %s", ticker, exc)
    finally:
        price_task.cancel()
        events_task.cancel()
        try:
            await asyncio.gather(price_task, events_task, return_exceptions=True)
        except Exception:
            pass
