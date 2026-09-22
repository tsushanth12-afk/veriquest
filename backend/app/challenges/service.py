# ==========================================================================
# VeriQuest Backend — Challenge Service (Business Logic)
# ==========================================================================

import asyncpg
import json
import logging
from typing import Optional
from .schemas import ChallengeListItem, ChallengeFilters

logger = logging.getLogger("veriquest.challenges")


async def get_published_challenges(
    pool: asyncpg.Pool,
    filters: ChallengeFilters,
    user_id: Optional[str] = None,
) -> tuple[list[ChallengeListItem], int]:
    """
    Retrieve published challenges with filtering, pagination, and user progress.
    Returns (items, total_count).
    """
    conditions = ["c.is_published = TRUE", "c.is_archived = FALSE"]
    params: list = []
    param_idx = 1

    if filters.search:
        conditions.append(
            f"(c.title ILIKE ${param_idx} OR c.description ILIKE ${param_idx} OR c.category ILIKE ${param_idx})"
        )
        params.append(f"%{filters.search}%")
        param_idx += 1

    if filters.difficulty and filters.difficulty != "All":
        conditions.append(f"c.difficulty = ${param_idx}")
        params.append(filters.difficulty)
        param_idx += 1

    if filters.category and filters.category != "All":
        conditions.append(f"c.category = ${param_idx}")
        params.append(filters.category)
        param_idx += 1

    if filters.level:
        conditions.append(f"c.level_number = ${param_idx}")
        params.append(filters.level)
        param_idx += 1

    where_clause = " AND ".join(conditions)

    # Count query
    count_query = f"SELECT COUNT(*) FROM public.challenges c WHERE {where_clause}"
    
    # Main query with user progress join
    query = f"""
        SELECT
            c.id::TEXT,
            c.slug,
            c.title,
            c.description,
            c.category,
            c.difficulty,
            c.level_number,
            c.xp_reward,
            c.estimated_minutes,
            c.learning_objective,
            COALESCE(p.status = 'completed', FALSE) AS solved,
            COALESCE(p.attempts, 0) AS attempts_count
        FROM public.challenges c
        LEFT JOIN public.user_challenge_progress p
            ON p.challenge_id = c.id AND p.user_id = ${param_idx}::UUID
        WHERE {where_clause}
        ORDER BY c.level_number ASC, c.difficulty ASC, c.title ASC
        LIMIT ${param_idx + 1}
        OFFSET ${param_idx + 2}
    """
    params.append(user_id or "00000000-0000-0000-0000-000000000000")
    params.append(filters.page_size)
    params.append((filters.page - 1) * filters.page_size)

    async with pool.acquire() as conn:
        total = await conn.fetchval(count_query, *params[:param_idx - 1])
        rows = await conn.fetch(query, *params)

    items = []
    for row in rows:
        items.append(ChallengeListItem(
            id=row["id"],
            slug=row["slug"],
            title=row["title"],
            description=row["description"],
            category=row["category"],
            difficulty=row["difficulty"],
            level=row["level_number"],
            xp=row["xp_reward"],
            estimated_minutes=row["estimated_minutes"],
            learning_objective=row["learning_objective"] or "",
            solved=row["solved"],
            attempts_count=row["attempts_count"],
            acceptance_rate=0,  # Computed separately if needed
        ))

    return items, total or 0


async def get_challenge_by_slug(
    pool: asyncpg.Pool,
    slug: str,
    user_id: Optional[str] = None,
) -> Optional[dict]:
    """
    Retrieve a single published challenge by slug.
    Returns public fields only — NEVER includes official_solution or hidden_testbench.
    """
    query = """
        SELECT
            c.id::TEXT,
            c.slug,
            c.title,
            c.description,
            c.category,
            c.difficulty,
            c.level_number,
            c.xp_reward,
            c.estimated_minutes,
            c.starter_code,
            c.input_description,
            c.output_description,
            c.constraints,
            c.public_examples,
            c.io_pins,
            c.hints,
            c.learning_objective,
            COALESCE(p.status = 'completed', FALSE) AS solved,
            COALESCE(p.attempts, 0) AS attempts_count
        FROM public.challenges c
        LEFT JOIN public.user_challenge_progress p
            ON p.challenge_id = c.id AND p.user_id = $2::UUID
        WHERE c.slug = $1
          AND c.is_published = TRUE
          AND c.is_archived = FALSE
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            query,
            slug,
            user_id or "00000000-0000-0000-0000-000000000000",
        )

    if not row:
        return None

    return {
        "id": row["id"],
        "slug": row["slug"],
        "title": row["title"],
        "description": row["description"],
        "category": row["category"],
        "difficulty": row["difficulty"],
        "level_number": row["level_number"],
        "xp_reward": row["xp_reward"],
        "estimated_minutes": row["estimated_minutes"],
        "starter_code": row["starter_code"],
        "input_description": row["input_description"] or "",
        "output_description": row["output_description"] or "",
        "constraints": json.loads(row["constraints"]) if isinstance(row["constraints"], str) else (row["constraints"] or []),
        "public_examples": json.loads(row["public_examples"]) if isinstance(row["public_examples"], str) else (row["public_examples"] or []),
        "io_pins": json.loads(row["io_pins"]) if isinstance(row["io_pins"], str) else (row["io_pins"] or []),
        "hints": json.loads(row["hints"]) if isinstance(row["hints"], str) else (row["hints"] or []),
        "learning_objective": row["learning_objective"] or "",
        "solved": row["solved"],
        "attempts_count": row["attempts_count"],
        "acceptance_rate": 0,
    }
