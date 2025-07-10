"""Database connection pool using asyncpg with Prometheus metrics.

This module provides an async PostgreSQL connection pool and utility functions
for executing queries with built-in Prometheus metrics collection.
"""
from __future__ import annotations

import os
import time
from typing import Any, Iterable, Optional, TypeVar, Callable, Awaitable, TypeVar, cast

import asyncpg
from asyncpg.pool import Pool

from app.metrics import (
    db_query_duration_seconds,
    db_operations_total,
    db_connections_active,
)

__all__ = ["init_db", "close_db", "fetch", "fetchrow", "execute"]

# Type variable for generic function return type
T = TypeVar("T")

# The connection pool – will be created in *init_db()*
pool: Optional[Pool] = None

# Status constants for metrics
ACTION_STATUS_SUCCESS = "success"
ACTION_STATUS_ERROR = "error"


async def init_db() -> None:
    """Initialize the asyncpg connection pool using environment variables.
    
    Environment variables:
        DB_HOST: Database host (default: localhost)
        DB_PORT: Database port (default: 5432)
        DB_NAME: Database name (default: appdb)
        DB_USER: Database user (default: appuser)
        DB_PASSWORD: Database password (default: apppass123)
        DB_MAX_CONNECTIONS: Maximum number of connections (default: 20)
    """
    global pool
    if pool is not None:
        return  # already initialized

    db_host = os.getenv("DB_HOST", "postgres")  # Changed default to 'postgres' for Docker
    db_port = int(os.getenv("DB_PORT", "5432"))
    db_name = os.getenv("DB_NAME", "appdb")
    db_user = os.getenv("DB_USER", "appuser")
    db_password = os.getenv("DB_PASSWORD", "apppass123")
    max_connections = int(os.getenv("DB_MAX_CONNECTIONS", "20"))

    logger = logging.getLogger("uvicorn")
    
    # Log connection parameters (except password)
    logger.info(f"Connecting to database: {db_user}@{db_host}:{db_port}/{db_name}")
    
    max_retries = 5
    retry_delay = 2  # seconds
    
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Attempting database connection (attempt {attempt}/{max_retries})...")
            pool = await asyncpg.create_pool(
                host=db_host,
                port=db_port,
                database=db_name,
                user=db_user,
                password=db_password,
                min_size=1,
                max_size=max_connections,
                max_queries=50000,
                max_inactive_connection_lifetime=300,
                command_timeout=30,
                server_settings={
                    'application_name': 'fastapi-metrics-app',
                    'search_path': 'public',
                }
            )
            
            # Test the connection
            async with pool.acquire() as conn:
                await conn.execute('SELECT 1')
            
            # Update the active connections gauge
            db_connections_active.set(len(pool._holders))
            logger.info("Database connection established successfully")
            return
            
        except Exception as e:
            logger.error(f"Database connection failed (attempt {attempt}/{max_retries}): {str(e)}")
            if attempt < max_retries:
                logger.info(f"Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.critical("Max retries reached. Could not connect to database.")
                raise


async def close_db() -> None:
    """Close the connection pool on application shutdown."""
    global pool
    if pool is not None:
        await pool.close()
        pool = None


async def _instrument_db_call(
    operation: str, 
    func: Callable[..., Awaitable[T]], 
    *args: Any, 
    **kwargs: Any
) -> T:
    """Execute a database operation with metrics collection.
    
    Args:
        operation: Operation name for metrics (e.g., 'select', 'insert')
        func: The async database function to call
        *args: Positional arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        The result of the database operation
        
    Raises:
        Any exception raised by the database operation
    """
    if pool is None:
        raise RuntimeError("Database pool not initialized")

    start_time = time.perf_counter()
    try:
        result = await func(*args, **kwargs)
        db_operations_total.labels(
            operation=operation, 
            status=ACTION_STATUS_SUCCESS
        ).inc()
        return result
    except Exception as e:
        db_operations_total.labels(
            operation=operation, 
            status=ACTION_STATUS_ERROR
        ).inc()
        raise e
    finally:
        duration = time.perf_counter() - start_time
        db_query_duration_seconds.labels(operation=operation).observe(duration)
        
        # Update active connections gauge if pool is available
        if pool is not None:
            db_connections_active.set(len(pool._holders))


async def fetch(query: str, *args: Any) -> list[dict[str, Any]]:
    """Execute a SELECT query and return all rows as a list of dictionaries."""
    if pool is None:
        raise RuntimeError("Database pool not initialized")
    
    rows = await _instrument_db_call(
        "select", 
        pool.fetch, 
        query, 
        *args
    )
    return [dict(row) for row in rows]


async def fetchrow(query: str, *args: Any) -> Optional[dict[str, Any]]:
    """Execute a SELECT query and return the first row as a dictionary."""
    if pool is None:
        raise RuntimeError("Database pool not initialized")
        
    row = await _instrument_db_call(
        "select", 
        pool.fetchrow, 
        query, 
        *args
    )
    return dict(row) if row else None


async def execute(query: str, *args: Any) -> str:
    """Execute a SQL command and return status."""
    if pool is None:
        raise RuntimeError("Database pool not initialized")
        
    operation = query.split()[0].lower()  # Extract operation type from query
    return await _instrument_db_call(
        operation,
        pool.execute,
        query,
        *args
    )


async def execute_returning(query: str, *args: Any) -> Optional[dict[str, Any]]:
    """Execute a SQL command with RETURNING clause and return the result."""
    if pool is None:
        raise RuntimeError("Database pool not initialized")
        
    row = await _instrument_db_call(
        "modify",
        pool.fetchrow,
        query,
        *args
    )
    return dict(row) if row else None
