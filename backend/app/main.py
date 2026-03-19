from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routes.analysis import router as analysis_router
from app.routes.health import router as health_router
from app.routes.stream import router as stream_router
from app.routes.ws import router as ws_router

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Stock Research Platform API...")
    try:
        await init_db()
        logger.info("Database initialized.")
    except Exception as exc:
        logger.warning("Database init failed (will retry on first request): %s", exc)

    # Optionally verify Qdrant connection
    try:
        from qdrant_client import AsyncQdrantClient
        from qdrant_client.http.models import Distance, VectorParams

        qclient = AsyncQdrantClient(host=settings.qdrant_host, port=6333)
        collections = await qclient.get_collections()
        logger.info("Qdrant connected. Collections: %s", [c.name for c in collections.collections])
        await qclient.close()
    except Exception as exc:
        logger.warning("Qdrant connection failed (non-critical): %s", exc)

    yield

    # Shutdown
    logger.info("Shutting down Stock Research Platform API...")
    try:
        from app.database import _redis_client
        if _redis_client:
            await _redis_client.aclose()
    except Exception:
        pass


app = FastAPI(
    title="Stock Research Platform API",
    version="2.0.0",
    description="AI-powered multi-agent stock research and analysis platform",
    lifespan=lifespan,
)

# CORS — allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router)
app.include_router(analysis_router)
app.include_router(stream_router)
app.include_router(ws_router)


@app.get("/")
async def root():
    return {
        "service": "Stock Research Platform API",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/health",
    }
