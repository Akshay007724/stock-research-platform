from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, get_redis

router = APIRouter()

_HEALTH_RESPONSE = {"status": "ok", "service": "stock-research-platform", "version": "2.0.0"}


@router.get("/health")
async def health():
    return _HEALTH_RESPONSE


# Alias for backwards-compatibility with older docker-compose configurations
@router.get("/api/v1/health")
async def health_v1():
    return _HEALTH_RESPONSE


@router.get("/health/detailed")
async def health_detailed(db: AsyncSession = Depends(get_db)):
    health_data: dict = {"status": "ok", "components": {}}

    # Database check
    try:
        from sqlalchemy import text
        await db.execute(text("SELECT 1"))
        health_data["components"]["database"] = "ok"
    except Exception as exc:
        health_data["components"]["database"] = f"error: {exc}"
        health_data["status"] = "degraded"

    return health_data
