# ==========================================================================
# VeriQuest Backend — Database Session & Connection
# ==========================================================================

import asyncpg
import logging
from contextlib import asynccontextmanager
from ..core.config import get_settings
from .runtime import create_runtime_pool, close_runtime_pool

logger = logging.getLogger("veriquest.db")

# Global connection pool
_pool: asyncpg.Pool | None = None


async def init_db():
    """Initialize the database connection pool."""
    global _pool
    settings = get_settings()
    try:
        _pool = await create_runtime_pool(settings.database_url.get_secret_value(), 'vq_api', 2, 10)
        logger.info("Database connection pool initialized")
    except Exception:
        logger.error('Database initialization failed; private diagnostics withheld')
        raise RuntimeError('Database initialization failed') from None


async def close_db():
    """Close the database connection pool."""
    global _pool
    if _pool:
        await close_runtime_pool(_pool)
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
