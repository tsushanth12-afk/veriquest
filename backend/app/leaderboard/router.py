# ==========================================================================
# VeriQuest Backend — Leaderboard API Routes
# ==========================================================================

import asyncpg
from fastapi import APIRouter, Depends, Query

from ..core.security import get_current_user, AuthenticatedUser
from ..db.session import get_db

router = APIRouter(prefix="/api/v1/leaderboard", tags=["leaderboard"])


@router.get("")
async def get_leaderboard(
    tab: str = Query("global", regex="^(global|weekly|monthly)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    user: AuthenticatedUser = Depends(get_current_user),
    pool: asyncpg.Pool = Depends(get_db),
):
    """
    Get leaderboard rankings. All data is server-authoritative.
    Users cannot submit their own rank or XP.
    """
    async with pool.acquire() as conn:
        if tab == "global":
            rows = await conn.fetch(
                """
                SELECT
                    ROW_NUMBER() OVER (ORDER BY xp DESC) AS rank,
                    id::TEXT AS user_id,
                    username,
                    level,
                    xp,
                    total_solved AS solved_count,
                    (id = $1::UUID) AS is_current_user
                FROM public.profiles
                ORDER BY xp DESC
                LIMIT $2 OFFSET $3
                """,
                user.user_id,
                page_size,
                (page - 1) * page_size,
            )
        elif tab == "weekly":
            # Weekly: XP earned in the last 7 days
            rows = await conn.fetch(
                """
                SELECT
                    ROW_NUMBER() OVER (ORDER BY weekly_xp DESC) AS rank,
                    p.id::TEXT AS user_id,
                    p.username,
                    p.level,
                    COALESCE(t.weekly_xp, 0) AS xp,
                    p.total_solved AS solved_count,
                    (p.id = $1::UUID) AS is_current_user
                FROM public.profiles p
                LEFT JOIN (
                    SELECT user_id, SUM(amount) AS weekly_xp
                    FROM public.xp_transactions
                    WHERE created_at >= NOW() - INTERVAL '7 days'
                    GROUP BY user_id
                ) t ON t.user_id = p.id
                ORDER BY weekly_xp DESC NULLS LAST
                LIMIT $2 OFFSET $3
                """,
                user.user_id,
                page_size,
                (page - 1) * page_size,
            )
        else:  # monthly
            rows = await conn.fetch(
                """
                SELECT
                    ROW_NUMBER() OVER (ORDER BY monthly_xp DESC) AS rank,
                    p.id::TEXT AS user_id,
                    p.username,
                    p.level,
                    COALESCE(t.monthly_xp, 0) AS xp,
                    p.total_solved AS solved_count,
                    (p.id = $1::UUID) AS is_current_user
                FROM public.profiles p
                LEFT JOIN (
                    SELECT user_id, SUM(amount) AS monthly_xp
                    FROM public.xp_transactions
                    WHERE created_at >= NOW() - INTERVAL '30 days'
                    GROUP BY user_id
                ) t ON t.user_id = p.id
                ORDER BY monthly_xp DESC NULLS LAST
                LIMIT $2 OFFSET $3
                """,
                user.user_id,
                page_size,
                (page - 1) * page_size,
            )

        total = await conn.fetchval("SELECT COUNT(*) FROM public.profiles")

    entries = []
    for row in rows:
        initials = row["username"][:2].upper() if row["username"] else "??"
        entries.append({
            "rank": row["rank"],
            "username": row["username"],
            "avatarText": initials,
            "level": row["level"],
            "levelTitle": "",
            "xp": row["xp"],
            "solvedCount": row["solved_count"],
            "isCurrentUser": row["is_current_user"],
        })

    return {
        "entries": entries,
        "total": total,
        "page": page,
        "tab": tab,
    }
