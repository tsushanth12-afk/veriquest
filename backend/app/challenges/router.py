# ==========================================================================
# VeriQuest Backend — Challenge API Routes
# ==========================================================================

import asyncpg
from fastapi import APIRouter, Depends, Query
from typing import Optional

from ..core.security import get_optional_user, AuthenticatedUser
from ..core.errors import not_found
from ..db.session import get_db
from .schemas import (
    PublicChallengeResponse,
    ChallengeListResponse,
    ChallengeListItem,
    ChallengeFilters,
)
from .service import get_published_challenges, get_challenge_by_slug

router = APIRouter(prefix="/api/v1/challenges", tags=["challenges"])


@router.get("", response_model=ChallengeListResponse)
async def list_challenges(
    search: Optional[str] = Query(None, max_length=200),
    difficulty: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    level: Optional[int] = Query(None, ge=1),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    user: Optional[AuthenticatedUser] = Depends(get_optional_user),
    pool: asyncpg.Pool = Depends(get_db),
):
    """
    List published challenges with filtering and pagination.
    Returns only public fields — never exposes official solutions or hidden testbenches.
    Accessible to unauthenticated visitors; personalized progress attached if signed in.
    """
    filters = ChallengeFilters(
        search=search,
        difficulty=difficulty,
        category=category,
        level=level,
        status=status,
        page=page,
        page_size=page_size,
    )

    user_id = user.user_id if user else None
    items, total = await get_published_challenges(pool, filters, user_id)

    return ChallengeListResponse(
        challenges=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{slug}", response_model=PublicChallengeResponse)
async def get_challenge(
    slug: str,
    user: Optional[AuthenticatedUser] = Depends(get_optional_user),
    pool: asyncpg.Pool = Depends(get_db),
):
    """
    Retrieve a single challenge by slug.
    Returns only public fields — NEVER includes official_solution, hidden_testbench,
    or any private evaluator configuration.
    """
    user_id = user.user_id if user else None
    challenge = await get_challenge_by_slug(pool, slug, user_id)

    if not challenge:
        raise not_found("Challenge")

    return challenge
