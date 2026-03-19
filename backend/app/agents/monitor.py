"""
Performance & Monitoring Agent
Tracks latency, API health, and pipeline metrics during analysis runs.
Exposes data via Redis so /api/monitor can serve live dashboards.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from contextlib import asynccontextmanager
from typing import Any

import httpx

from app.config import settings
from app.mcp.bus import MCPBus
from app.mcp.registry import registry
from app.schemas import AgentEvent

logger = logging.getLogger(__name__)

_METRICS_KEY = "monitor:pipeline_metrics"
_METRICS_TTL = 3600  # 1 hour


class PipelineMetrics:
    """Collects timing and health data during a single analysis run."""

    def __init__(self, ticker: str) -> None:
        self.ticker = ticker
        self.start_ts: float = time.monotonic()
        self.phase_times: dict[str, float] = {}
        self.api_calls: list[dict[str, Any]] = []
        self._phase_starts: dict[str, float] = {}

    def phase_start(self, name: str) -> None:
        self._phase_starts[name] = time.monotonic()

    def phase_end(self, name: str) -> float:
        elapsed = time.monotonic() - self._phase_starts.get(name, self.start_ts)
        self.phase_times[name] = round(elapsed, 3)
        return elapsed

    def record_api(self, provider: str, endpoint: str, latency_ms: float, success: bool) -> None:
        self.api_calls.append({
            "provider": provider,
            "endpoint": endpoint,
            "latency_ms": round(latency_ms, 1),
            "success": success,
        })

    def to_dict(self) -> dict[str, Any]:
        total = time.monotonic() - self.start_ts
        return {
            "ticker": self.ticker,
            "total_elapsed_s": round(total, 3),
            "phase_times_s": self.phase_times,
            "api_calls": self.api_calls,
            "api_success_rate": (
                round(sum(1 for c in self.api_calls if c["success"]) / len(self.api_calls), 3)
                if self.api_calls else 1.0
            ),
        }


@asynccontextmanager
async def track_phase(metrics: PipelineMetrics, name: str):
    """Context manager that records phase timing."""
    metrics.phase_start(name)
    try:
        yield
    finally:
        elapsed = metrics.phase_end(name)
        logger.debug("Phase '%s' completed in %.3fs", name, elapsed)


async def _check_finnhub(client: httpx.AsyncClient) -> dict[str, Any]:
    if not settings.finnhub_api_key:
        return {"status": "skipped", "reason": "no key"}
    t0 = time.monotonic()
    try:
        resp = await client.get(
            "https://finnhub.io/api/v1/quote",
            params={"symbol": "AAPL", "token": settings.finnhub_api_key},
            timeout=8,
        )
        ok = resp.status_code == 200 and resp.json().get("c", 0) > 0
        return {"status": "ok" if ok else "degraded", "latency_ms": round((time.monotonic() - t0) * 1000, 1)}
    except Exception as exc:
        return {"status": "error", "error": str(exc), "latency_ms": round((time.monotonic() - t0) * 1000, 1)}


async def _check_fmp(client: httpx.AsyncClient) -> dict[str, Any]:
    if not settings.fmp_api_key:
        return {"status": "skipped", "reason": "no key"}
    t0 = time.monotonic()
    try:
        resp = await client.get(
            f"https://financialmodelingprep.com/api/v3/quote/AAPL",
            params={"apikey": settings.fmp_api_key},
            timeout=8,
        )
        ok = resp.status_code == 200 and len(resp.json()) > 0
        return {"status": "ok" if ok else "degraded", "latency_ms": round((time.monotonic() - t0) * 1000, 1)}
    except Exception as exc:
        return {"status": "error", "error": str(exc), "latency_ms": round((time.monotonic() - t0) * 1000, 1)}


async def _check_stooq(client: httpx.AsyncClient) -> dict[str, Any]:
    t0 = time.monotonic()
    try:
        resp = await client.get(
            "https://stooq.com/q/d/l/?s=aapl.us&i=d",
            timeout=10,
            follow_redirects=True,
        )
        ok = resp.status_code == 200 and len(resp.text) > 50
        return {"status": "ok" if ok else "degraded", "latency_ms": round((time.monotonic() - t0) * 1000, 1)}
    except Exception as exc:
        return {"status": "error", "error": str(exc), "latency_ms": round((time.monotonic() - t0) * 1000, 1)}


async def run_health_check(redis) -> dict[str, Any]:
    """
    Run a full health check: API providers + Redis + OpenAI.
    Called by /api/monitor endpoint.
    """
    async with httpx.AsyncClient() as client:
        fh_check, fmp_check, stooq_check = await asyncio.gather(
            _check_finnhub(client),
            _check_fmp(client),
            _check_stooq(client),
        )

    # Redis ping
    t0 = time.monotonic()
    try:
        await redis.ping()
        redis_status = {"status": "ok", "latency_ms": round((time.monotonic() - t0) * 1000, 1)}
    except Exception as exc:
        redis_status = {"status": "error", "error": str(exc)}

    # Last pipeline metrics
    last_metrics = None
    try:
        raw = await redis.get(_METRICS_KEY)
        if raw:
            last_metrics = json.loads(raw)
    except Exception:
        pass

    providers = {
        "finnhub": fh_check,
        "fmp": fmp_check,
        "stooq": stooq_check,
    }
    all_ok = all(v["status"] in ("ok", "skipped") for v in providers.values())

    return {
        "overall": "healthy" if all_ok and redis_status["status"] == "ok" else "degraded",
        "providers": providers,
        "redis": redis_status,
        "last_pipeline": last_metrics,
    }


async def run(ticker: str, bus: MCPBus, metrics: PipelineMetrics) -> dict[str, Any]:
    """
    Monitor agent: persists pipeline metrics to Redis after a run completes.
    Runs at the end of the orchestration pipeline.
    """
    agent = "monitor"
    redis = bus._redis

    await registry.set_status(agent, "running", redis, f"Recording pipeline metrics for {ticker}")
    await bus.publish(
        ticker,
        AgentEvent(
            agent_name=agent,
            event_type="start",
            message=f"Collecting performance metrics for {ticker}",
        ),
    )

    data = metrics.to_dict()

    await bus.publish(
        ticker,
        AgentEvent(
            agent_name=agent,
            event_type="progress",
            message=(
                f"Pipeline: {data['total_elapsed_s']}s total | "
                f"API success rate: {data['api_success_rate']*100:.0f}%"
            ),
            data=data,
        ),
    )

    # Persist to Redis for /api/monitor
    try:
        await redis.set(_METRICS_KEY, json.dumps(data), ex=_METRICS_TTL)
    except Exception as exc:
        logger.warning("Monitor: failed to persist metrics: %s", exc)

    await registry.set_status(agent, "done", redis, f"Metrics recorded — {data['total_elapsed_s']}s")
    await bus.publish(
        ticker,
        AgentEvent(
            agent_name=agent,
            event_type="complete",
            message="Performance monitoring complete",
            data=data,
        ),
    )

    return data
