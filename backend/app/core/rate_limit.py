# ==========================================================================
# VeriQuest Backend — Rate Limiting Infrastructure
#
# Concrete limits per Master Prompt Section 6:
# - login: 5 attempts / 5 min / IP
# - signup: 3 / hour / IP
# - password reset: 3 / hour / IP
# - submission creation: 10 / min / user
# - admin validate/publish: 20 / min / admin user
#
# Uses Redis sliding-window counter with automatic in-memory fallback
# if Redis is unavailable.
# ==========================================================================

import time
import logging
from collections import defaultdict
from typing import Optional, Callable
from fastapi import Request, Depends

from .config import get_settings, Settings
from .errors import rate_limited
from .security import get_current_user, AuthenticatedUser

logger = logging.getLogger("veriquest.ratelimit")

# In-memory fallback: dict of {key: list_of_timestamps}
_memory_store: dict[str, list[float]] = defaultdict(list)


def _get_client_ip(request: Request) -> str:
    """Extract real client IP, respecting forward proxies."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "unknown"


def _check_memory_rate_limit(key: str, max_requests: int, window_seconds: int) -> bool:
    """Sliding-window counter in memory."""
    now = time.time()
    cutoff = now - window_seconds
    timestamps = _memory_store[key]

    # Clean expired
    _memory_store[key] = [t for t in timestamps if t > cutoff]

    if len(_memory_store[key]) >= max_requests:
        return False

    _memory_store[key].append(now)
    return True


async def check_rate_limit(
    key: str,
    max_requests: int,
    window_seconds: int,
    settings: Settings,
) -> bool:
    """
    Check rate limit using Redis sliding-window.
    Falls back to in-memory store if Redis is down.
    """
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.redis_url, decode_responses=True)
        now = time.time()
        cutoff = now - window_seconds
        redis_key = f"rl:{key}"

        pipe = r.pipeline()
        # Remove timestamps older than window
        pipe.zremrangebyscore(redis_key, 0, cutoff)
        # Count remaining
        pipe.zcard(redis_key)
        # Add current timestamp
        pipe.zadd(redis_key, {str(now): now})
        # Set TTL to window
        pipe.expire(redis_key, window_seconds)
        results = await pipe.execute()

        count = results[1]
        await r.aclose()
        return count < max_requests

    except Exception as e:
        logger.debug(f"Redis rate limit check failed ({e}), falling back to in-memory store")
        return _check_memory_rate_limit(key, max_requests, window_seconds)


class RateLimit:
    """
    FastAPI dependency factory for rate limiting.
    Supports 'ip' keying (unauthenticated) and 'user' keying (authenticated).
    """

    def __init__(
        self,
        action: str,
        max_requests: int,
        window_seconds: int,
        key_type: str = "ip",  # "ip" or "user"
    ):
        self.action = action
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.key_type = key_type

    async def __call__(
        self,
        request: Request,
        settings: Settings = Depends(get_settings),
        user: Optional[AuthenticatedUser] = None,
    ):
        if self.key_type == "user" and user:
            identifier = f"user:{user.user_id}"
        else:
            identifier = f"ip:{_get_client_ip(request)}"

        key = f"{self.action}:{identifier}"
        allowed = await check_rate_limit(key, self.max_requests, self.window_seconds, settings)

        if not allowed:
            logger.warning(f"Rate limit exceeded for {key} (limit: {self.max_requests}/{self.window_seconds}s)")
            raise rate_limited(
                f"Rate limit exceeded for {self.action}. "
                f"Maximum {self.max_requests} requests per {self.window_seconds} seconds. "
                f"Please try again later."
            )


# ======================================================================
# Pre-configured Limiters (Per Master Prompt Section 6)
# ======================================================================

# Unauthenticated IP-based
limit_login = RateLimit("login", max_requests=5, window_seconds=300, key_type="ip")
limit_signup = RateLimit("signup", max_requests=3, window_seconds=3600, key_type="ip")
limit_password_reset = RateLimit("password_reset", max_requests=3, window_seconds=3600, key_type="ip")

# Authenticated User-based
limit_submission = RateLimit("submission", max_requests=10, window_seconds=60, key_type="user")
limit_admin_actions = RateLimit("admin_action", max_requests=20, window_seconds=60, key_type="user")
