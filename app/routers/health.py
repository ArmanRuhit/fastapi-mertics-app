"""Health check endpoint similar to Node.js version."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, status

router = APIRouter()


@router.get("/health", status_code=status.HTTP_200_OK)
async def health():
    """Simple health check without external dependencies."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime": float(__import__("time").process_time()),
    }
