from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import AsyncGenerator

import redis.asyncio as aioredis
from sqlalchemy import Column, DateTime, Integer, String, Text, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

logger = logging.getLogger(__name__)

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    pass


class AnalysisRecord(Base):
    __tablename__ = "analysis_records"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(20), index=True, nullable=False)
    result_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


async def init_db() -> None:
    """Create tables. Uses a pg_advisory_lock so multiple workers don't race."""
    from sqlalchemy import text
    async with engine.begin() as conn:
        # Advisory lock key (arbitrary constant) prevents multi-worker races
        await conn.execute(text("SELECT pg_advisory_xact_lock(9876543210)"))
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created/verified.")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


_redis_client: aioredis.Redis | None = None


async def get_redis_client() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = await aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            max_connections=50,
        )
    return _redis_client


async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    client = await get_redis_client()
    yield client


async def save_analysis(db: AsyncSession, ticker: str, result_json: str) -> None:
    record = AnalysisRecord(ticker=ticker.upper(), result_json=result_json, created_at=datetime.utcnow())
    db.add(record)
    await db.commit()


async def get_analysis_history(db: AsyncSession, ticker: str, limit: int = 10) -> list[dict]:
    result = await db.execute(
        select(AnalysisRecord)
        .where(AnalysisRecord.ticker == ticker.upper())
        .order_by(AnalysisRecord.created_at.desc())
        .limit(limit)
    )
    records = result.scalars().all()
    history = []
    for r in records:
        try:
            data = json.loads(r.result_json)
            data["db_id"] = r.id
            data["db_created_at"] = r.created_at.isoformat()
            history.append(data)
        except Exception:
            pass
    return history
