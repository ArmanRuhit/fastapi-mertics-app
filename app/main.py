"""FastAPI application entry point with Prometheus metrics support."""
from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from typing import List

from fastapi import FastAPI, Request, Response
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.middleware.metrics_middleware import MetricsMiddleware
from app.metrics import REGISTRY
from app.metrics.system_metrics import collect_cpu_percent
from app.routers import health as health_router
# Add these imports at the top
from app.database import init_db
from app.routers import api

# Add this after creating the FastAPI app

logger = logging.getLogger("uvicorn")

app = FastAPI(title="FastAPI Metrics App")

# ---------------------------------------------------------------------------
# Middleware & Routers
# ---------------------------------------------------------------------------
app.add_middleware(MetricsMiddleware)
app.include_router(health_router.router)
app.include_router(api.router)



# ---------------------------------------------------------------------------
# Metrics endpoint
# ---------------------------------------------------------------------------
@app.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    data = generate_latest(REGISTRY)
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)


# ---------------------------------------------------------------------------
# Root endpoint
# ---------------------------------------------------------------------------
@app.get("/")
async def root():
    return {"message": "FastAPI Metrics App running"}


# ---------------------------------------------------------------------------
# Startup / Shutdown
# ---------------------------------------------------------------------------

_background_tasks: List[asyncio.Task] = []


@app.on_event("startup")
async def _startup() -> None:
    logger = logging.getLogger("uvicorn")
    try:
        logger.info("Starting application initialization...")
        
        # Log environment variables for debugging
        db_host = os.getenv("DB_HOST", "postgres")
        db_port = os.getenv("DB_PORT", "5432")
        logger.info(f"Database connection parameters - Host: {db_host}, Port: {db_port}")
        
        # Initialize database connection with retry logic
        max_retries = 5
        retry_delay = 1  # Start with 1 second delay
        
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"Initializing database connection (attempt {attempt}/{max_retries})...")
                await init_db()
                logger.info("Database connection initialized successfully")
                break
            except Exception as e:
                if attempt == max_retries:
                    logger.error(f"Failed to initialize database after {max_retries} attempts")
                    raise
                logger.warning(f"Database initialization attempt {attempt} failed: {str(e)}")
                logger.info(f"Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 10)  # Exponential backoff, max 10 seconds
        
        # Start background tasks only if database initialization was successful
        logger.info("Starting background tasks...")
        _background_tasks.append(asyncio.create_task(collect_cpu_percent()))
        logger.info("Background tasks started")
        
        logger.info("Application startup complete")
    except Exception as e:
        logger.error(f"Critical error during startup: {str(e)}", exc_info=True)
        # Don't re-raise to prevent Uvicorn from restarting in a loop
        # Instead, we'll let the application start but without database functionality
        logger.error("Application will start without database connectivity")


@app.on_event("shutdown")
async def _shutdown() -> None:
    # Cancel background tasks first
    for task in _background_tasks:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task

    logger.info("Application shutdown complete")
