# ==========================================================================
# VeriQuest Backend — Database Session & Connection
# ==========================================================================

import asyncpg
import logging
from contextlib import asynccontextmanager
from .config import get_settings

logger = logging.getLogger("veriquest.db")

# Global connection pool
_pool: asyncpg.Pool | None = None


async def init_db():
    """Initialize the database connection pool."""
    global _pool
    settings = get_settings()
    try:
        _pool = await asyncpg.create_pool(
            dsn=settings.database_url,
            min_size=2,
            max_size=10,
            command_timeout=30,
        )
        logger.info("Database connection pool initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database pool: {e}")
        raise


async def close_db():
    """Close the database connection pool."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("Database connection pool closed")


async def get_db() -> asyncpg.Pool:
    """FastAPI dependency to get the database pool."""
    if _pool is None:
        raise RuntimeError("Database pool not initialized")
    return _pool


@asynccontextmanager
async def get_connection():
    """Get a single database connection from the pool."""
    if _pool is None:
        raise RuntimeError("Database pool not initialized")
    async with _pool.acquire() as conn:
        yield conn
