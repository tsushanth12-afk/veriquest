# ==========================================================================
# VeriQuest Backend — FastAPI Main Application
# ==========================================================================

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .core.config import get_settings
from .core.errors import AppError
from .db.session import init_db, close_db

from .challenges.router import router as challenges_router
from .submissions.router import router as submissions_router
from .profile.router import router as profile_router
from .leaderboard.router import router as leaderboard_router
from .admin.router import router as admin_router

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("veriquest")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: initialize and cleanup resources."""
    logger.info("VeriQuest backend starting...")
    await init_db()
    logger.info("Database pool initialized")
    yield
    await close_db()
    logger.info("VeriQuest backend stopped")


app = FastAPI(
    title="VeriQuest API",
    description="LeetCode for Verilog HDL — Backend API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# Global error handler for AppError
@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.error_code, "message": exc.error_message}},
    )


# FastAPI validation errors (422) in structured format
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    msg = errors[0]["msg"] if errors else "Invalid request format"
    field = ".".join(str(x) for x in errors[0].get("loc", [])) if errors else ""
    full_message = f"{field}: {msg}" if field else msg
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "VALIDATION_ERROR", "message": full_message}},
    )


# Standard HTTP exceptions (e.g. 404 for nonexistent routes, 405)
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    code_map = {
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        429: "RATE_LIMITED",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
    }
    code = code_map.get(exc.status_code, "HTTP_ERROR")
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": code, "message": detail}},
    )


# Catch unhandled exceptions — never expose stack traces
@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled error on {request.method} {request.url.path}")
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "SYSTEM_ERROR", "message": "Internal server error"}},
    )


# Mount routers
app.include_router(challenges_router)
app.include_router(submissions_router)
app.include_router(profile_router)
app.include_router(leaderboard_router)
app.include_router(admin_router)


# ==========================================================================
# Health & Readiness
# ==========================================================================

@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok", "service": "veriquest-api"}


@app.get("/ready", tags=["health"])
async def readiness():
    """Check database and Redis connectivity."""
    from .db.session import get_db
    try:
        pool = await get_db()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        db_ok = True
    except Exception:
        db_ok = False

    redis_ok = False
    try:
        import redis
        r = redis.from_url(settings.redis_url)
        r.ping()
        redis_ok = True
    except Exception:
        pass

    status = "ok" if db_ok else "degraded"
    return {
        "status": status,
        "database": "connected" if db_ok else "disconnected",
        "redis": "connected" if redis_ok else "disconnected",
    }


# Quests and badges API
@app.get("/api/v1/quests", tags=["quests"])
async def get_quests(pool=None):
    """Get active quests with progress. Placeholder for full implementation."""
    from .core.security import get_current_user
    # For now return from database
    return {"quests": []}


@app.get("/api/v1/badges", tags=["badges"])
async def get_badges():
    """Get all badge definitions."""
    return {"badges": []}
