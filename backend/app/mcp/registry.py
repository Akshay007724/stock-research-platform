from __future__ import annotations

import json
import logging

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

_AGENT_DEFINITIONS: dict[str, dict] = {
    "orchestrator": {
        "name": "Orchestrator",
        "status": "idle",
        "connections": [],
        "last_event": None,
    },
    "market": {
        "name": "Market Research Agent",
        "status": "idle",
        "connections": ["orchestrator"],
        "last_event": None,
    },
    "historical": {
        "name": "Historical Analysis Agent",
        "status": "idle",
        "connections": ["orchestrator", "market"],
        "last_event": None,
    },
    "news": {
        "name": "News Sentiment Agent",
        "status": "idle",
        "connections": ["orchestrator"],
        "last_event": None,
    },
    "debate_bull": {
        "name": "Bull Agent",
        "status": "idle",
        "connections": ["debate_moderator", "market"],
        "last_event": None,
    },
    "debate_bear": {
        "name": "Bear Agent",
        "status": "idle",
        "connections": ["debate_moderator", "market"],
        "last_event": None,
    },
    "debate_moderator": {
        "name": "Debate Moderator",
        "status": "idle",
        "connections": ["orchestrator", "debate_bull", "debate_bear"],
        "last_event": None,
    },
    "recommender": {
        "name": "Recommendation Engine",
        "status": "idle",
        "connections": ["orchestrator", "market", "historical", "news", "debate_moderator"],
        "last_event": None,
    },
    "monitor": {
        "name": "Performance Monitor",
        "status": "idle",
        "connections": ["orchestrator", "recommender"],
        "last_event": None,
    },
}

_STATUS_KEY = "agent_registry:status"
_FLOW_KEY = "agent_registry:data_flow"


class AgentRegistry:
    """Tracks registered agents and their live statuses in Redis."""

    def _agent_key(self, agent_id: str) -> str:
        return f"{_STATUS_KEY}:{agent_id}"

    async def set_status(self, agent_id: str, status: str, redis: aioredis.Redis, last_event: str | None = None) -> None:
        key = self._agent_key(agent_id)
        definition = _AGENT_DEFINITIONS.get(agent_id, {})
        data = {
            "id": agent_id,
            "name": definition.get("name", agent_id),
            "status": status,
            "connections": definition.get("connections", []),
            "last_event": last_event,
        }
        try:
            await redis.set(key, json.dumps(data), ex=3600)
        except Exception as exc:
            logger.warning("AgentRegistry.set_status error: %s", exc)

    async def get_all(self, redis: aioredis.Redis) -> dict[str, dict]:
        result: dict[str, dict] = {}
        for agent_id, definition in _AGENT_DEFINITIONS.items():
            key = self._agent_key(agent_id)
            try:
                raw = await redis.get(key)
                if raw:
                    result[agent_id] = json.loads(raw)
                else:
                    result[agent_id] = {
                        "id": agent_id,
                        "name": definition["name"],
                        "status": "idle",
                        "connections": definition["connections"],
                        "last_event": None,
                    }
            except Exception:
                result[agent_id] = {
                    "id": agent_id,
                    "name": definition["name"],
                    "status": "idle",
                    "connections": definition["connections"],
                    "last_event": None,
                }
        return result

    async def record_data_flow(self, from_agent: str, to_agent: str, redis: aioredis.Redis) -> None:
        flow_entry = json.dumps({"from": from_agent, "to": to_agent})
        try:
            await redis.lpush(_FLOW_KEY, flow_entry)
            await redis.ltrim(_FLOW_KEY, 0, 99)
            await redis.expire(_FLOW_KEY, 3600)
        except Exception as exc:
            logger.warning("AgentRegistry.record_data_flow error: %s", exc)

    async def reset_all(self, redis: aioredis.Redis) -> None:
        for agent_id in _AGENT_DEFINITIONS:
            await self.set_status(agent_id, "idle", redis)


registry = AgentRegistry()
