from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncGenerator

import redis.asyncio as aioredis

from app.schemas import AgentEvent

logger = logging.getLogger(__name__)

_HISTORY_MAX = 200


class MCPBus:
    """Redis pub/sub message bus for agent-to-agent communication."""

    def __init__(self, redis: aioredis.Redis) -> None:
        self._redis = redis

    def _channel(self, ticker: str) -> str:
        return f"agent:{ticker.upper()}"

    def _history_key(self, ticker: str) -> str:
        return f"history:{ticker.upper()}"

    async def publish(self, ticker: str, event: AgentEvent) -> None:
        channel = self._channel(ticker)
        history_key = self._history_key(ticker)
        payload = event.model_dump_json()
        try:
            await self._redis.publish(channel, payload)
            await self._redis.lpush(history_key, payload)
            await self._redis.ltrim(history_key, 0, _HISTORY_MAX - 1)
            await self._redis.expire(history_key, 7200)
        except Exception as exc:
            logger.warning("MCPBus.publish error: %s", exc)

    async def subscribe(self, ticker: str) -> AsyncGenerator[AgentEvent, None]:
        channel = self._channel(ticker)
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(channel)
        try:
            while True:
                try:
                    message = await asyncio.wait_for(pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0), timeout=2.0)
                except asyncio.TimeoutError:
                    message = None

                if message is None:
                    await asyncio.sleep(0.05)
                    continue

                if message.get("type") == "message":
                    try:
                        event = AgentEvent.model_validate_json(message["data"])
                        yield event
                    except Exception as exc:
                        logger.warning("MCPBus parse error: %s", exc)
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()

    async def get_history(self, ticker: str, limit: int = 50) -> list[AgentEvent]:
        history_key = self._history_key(ticker)
        try:
            raw_list = await self._redis.lrange(history_key, 0, limit - 1)
            events: list[AgentEvent] = []
            for raw in reversed(raw_list):
                try:
                    events.append(AgentEvent.model_validate_json(raw))
                except Exception:
                    pass
            return events
        except Exception as exc:
            logger.warning("MCPBus.get_history error: %s", exc)
            return []
