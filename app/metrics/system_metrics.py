"""Background task to collect system / process level metrics."""
from __future__ import annotations

import asyncio
import os
import psutil

from prometheus_client import Gauge

from app.metrics import process_cpu_percentage


async def collect_cpu_percent(interval_seconds: int = 5) -> None:
    """Periodically update *process_cpu_percentage* gauge.

    Uses psutil.Process().cpu_percent(), which calculates CPU usage over the
    interval since last call. First call will always return 0.0, so we ignore
    it by making an initial call before the loop.
    """

    process = psutil.Process(os.getpid())
    process.cpu_percent(None)  # initialise baseline
    while True:
        await asyncio.sleep(interval_seconds)
        percent = process.cpu_percent(None)  # percent across all cores
        process_cpu_percentage.set(percent)
