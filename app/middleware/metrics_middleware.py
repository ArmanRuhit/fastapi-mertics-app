"""Custom FastAPI middleware that records Prometheus HTTP metrics.

This mirrors the Express middleware in the Node.js reference implementation.
"""
from __future__ import annotations

import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.metrics import http_requests_total, http_request_duration_seconds


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware that records counter & histogram for each request."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Response]):  # type: ignore[override]
        start_time = time.perf_counter()
        response: Response | None = None
        try:
            response = await call_next(request)
            return response
        finally:
            # Ensure we have a response object even in exceptions
            status_code = response.status_code if response else 500
            route = request.scope.get("path", request.url.path)

            http_requests_total.labels(
                method=request.method,
                route=route,
                status_code=status_code,
            ).inc()

            duration = time.perf_counter() - start_time
            http_request_duration_seconds.labels(
                method=request.method,
                route=route,
                status_code=status_code,
            ).observe(duration)
