# ==========================================================================
# VeriQuest Backend — Profile API Routes
# ==========================================================================

import asyncpg
import json
from fastapi import APIRouter, Depends

from ..core.security import get_current_user, AuthenticatedUser
from ..core.errors import not_found
from ..db.session import get_db
from ..gamification.xp import calculate_level

router = APIRouter(prefix="/api/v1/profile", tags=["profile"])


# Fields that users are allowed to update
ALLOWED_PROFILE_FIELDS = {"display_name", "bio", "avatar_url"}

# Fields that are NEVER settable by users
PROTECTED_FIELDS = {
    "id", "xp", "level", "current_streak", "longest_streak",
    "total_solved", "easy_solved", "medium_solved", "hard_solved",
    "total_attempts", "created_at", "updated_at",
}


@router.get("")
async def get_profile(
    user: AuthenticatedUser = Depends(get_current_user),
    pool: asyncpg.Pool = Depends(get_db),
):
    """Get the authenticated user's full profile with stats and topic masteries."""
    async with pool.acquire() as conn:
        profile = await conn.fetchrow(
            """
            SELECT
                id::TEXT, username, display_name, avatar_url, bio,
                level, xp, current_streak, longest_streak,
                total_solved, easy_solved, medium_solved, hard_solved,
                total_attempts, created_at::TEXT
            FROM public.profiles
            WHERE id = $1::UUID
            """,
            user.user_id,
        )

        if not profile:
            raise not_found("Profile")

        # Calculate topic masteries from challenge progress
        masteries = await conn.fetch(
            """
            SELECT
                c.category AS topic,
                COUNT(CASE WHEN ucp.status = 'completed' THEN 1 END) AS completed,
                COUNT(*) AS total
            FROM public.challenges c
            LEFT JOIN public.user_challenge_progress ucp
                ON ucp.challenge_id = c.id AND ucp.user_id = $1::UUID
            WHERE c.is_published = TRUE
            GROUP BY c.category
            ORDER BY c.category
            """,
            user.user_id,
        )

        # Get user badges
        badges = await conn.fetch(
            """
            SELECT b.id::TEXT, b.name, b.description, b.category, b.icon,
                   b.requirement, ub.unlocked_at::TEXT
            FROM public.badges b
            JOIN public.user_badges ub ON ub.badge_id = b.id
            WHERE ub.user_id = $1::UUID
            ORDER BY ub.unlocked_at DESC
            """,
            user.user_id,
        )

        # Get global rank
        rank = await conn.fetchval(
            """
            SELECT COUNT(*) + 1
            FROM public.profiles
            WHERE xp > (SELECT xp FROM public.profiles WHERE id = $1::UUID)
            """,
            user.user_id,
        )

        total_users = await conn.fetchval("SELECT COUNT(*) FROM public.profiles")

    level, level_title = calculate_level(profile["xp"])
    next_level_xp = 0
    settings_breakpoints = [0, 500, 1000, 1500, 2200, 3000, 4000, 5200, 6500, 8000, 10000]
    if level < len(settings_breakpoints):
        next_level_xp = settings_breakpoints[level]

    acceptance_rate = 0
    if profile["total_attempts"] > 0:
        acceptance_rate = round(profile["total_solved"] / profile["total_attempts"] * 100)

    percentile = 0
    if total_users and total_users > 0:
        percentile = round((1 - (rank - 1) / total_users) * 100)

    return {
        "id": profile["id"],
        "username": profile["username"],
        "fullName": profile["display_name"] or profile["username"],
        "bio": profile["bio"] or "",
        "avatarUrl": profile["avatar_url"],
        "joinedDate": profile["created_at"],
        "stats": {
            "level": level,
            "levelTitle": level_title,
            "currentXP": profile["xp"],
            "nextLevelXP": next_level_xp,
            "totalSolved": profile["total_solved"],
            "easySolved": profile["easy_solved"],
            "mediumSolved": profile["medium_solved"],
            "hardSolved": profile["hard_solved"],
            "totalAttempts": profile["total_attempts"],
            "acceptanceRate": acceptance_rate,
            "currentStreak": profile["current_streak"],
            "longestStreak": profile["longest_streak"],
            "globalRank": rank,
            "weeklyRank": 0,
            "percentile": percentile,
        },
        "topicMasteries": [
            {
                "topic": m["topic"],
                "percentage": round(m["completed"] / m["total"] * 100) if m["total"] > 0 else 0,
                "completed": m["completed"],
                "total": m["total"],
            }
            for m in masteries
        ],
        "badges": [
            {
                "id": b["id"],
                "name": b["name"],
                "description": b["description"],
                "category": b["category"],
                "icon": b["icon"],
                "requirement": b["requirement"],
                "unlocked": True,
                "unlockedAt": b["unlocked_at"],
            }
            for b in badges
        ],
    }


@router.patch("")
async def update_profile(
    body: dict,
    user: AuthenticatedUser = Depends(get_current_user),
    pool: asyncpg.Pool = Depends(get_db),
):
    """
    Update allowed profile fields only.
    Users CANNOT modify: xp, level, role, streak, solved counts.
    """
    # Filter to allowed fields only
    updates = {k: v for k, v in body.items() if k in ALLOWED_PROFILE_FIELDS}

    if not updates:
        return {"message": "No valid fields to update"}

    # Build safe SET clause
    set_parts = []
    params = [user.user_id]
    for i, (field, value) in enumerate(updates.items(), start=2):
        set_parts.append(f"{field} = ${i}")
        params.append(value)

    query = f"UPDATE public.profiles SET {', '.join(set_parts)} WHERE id = $1::UUID"

    async with pool.acquire() as conn:
        await conn.execute(query, *params)

    return {"message": "Profile updated", "updated_fields": list(updates.keys())}
