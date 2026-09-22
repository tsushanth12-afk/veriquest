# ==========================================================================
# VeriQuest Backend — Submission Service (Business Logic)
# ==========================================================================

import asyncpg
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("veriquest.submissions")


async def create_submission(
    pool: asyncpg.Pool,
    user_id: str,
    challenge_id: str,
    submitted_code: str,
    idempotency_key: Optional[str] = None,
) -> dict:
    """
    Create a new submission record and return submission metadata.
    Handles idempotency to prevent duplicate submissions.
    """
    async with pool.acquire() as conn:
        # Check idempotency
        if idempotency_key:
            existing = await conn.fetchrow(
                """
                SELECT id::TEXT, status FROM public.submissions
                WHERE idempotency_key = $1 AND user_id = $2::UUID
                """,
                idempotency_key,
                user_id,
            )
            if existing:
                return {
                    "submission_id": existing["id"],
                    "status": existing["status"],
                    "is_duplicate": True,
                }

        # Verify challenge exists and is published
        challenge = await conn.fetchrow(
            """
            SELECT id, xp_reward, difficulty FROM public.challenges
            WHERE id = $1::UUID AND is_published = TRUE
            """,
            challenge_id,
        )
        if not challenge:
            return None  # Signal not found

        # Validate submission size
        if len(submitted_code.encode("utf-8")) > 65536:
            return {"error": "SUBMISSION_TOO_LARGE"}

        # Create submission
        submission_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        await conn.execute(
            """
            INSERT INTO public.submissions (
                id, user_id, challenge_id, status, submitted_code,
                idempotency_key, submitted_at
            ) VALUES ($1::UUID, $2::UUID, $3::UUID, 'queued', $4, $5, $6)
            """,
            submission_id,
            user_id,
            challenge_id,
            submitted_code,
            idempotency_key,
            now,
        )

        # Update attempt count in progress
        await conn.execute(
            """
            INSERT INTO public.user_challenge_progress (user_id, challenge_id, status, attempts)
            VALUES ($1::UUID, $2::UUID, 'in_progress', 1)
            ON CONFLICT (user_id, challenge_id)
            DO UPDATE SET
                attempts = user_challenge_progress.attempts + 1,
                status = CASE
                    WHEN user_challenge_progress.status = 'completed' THEN 'completed'
                    ELSE 'in_progress'
                END,
                updated_at = NOW()
            """,
            user_id,
            challenge_id,
        )

        return {
            "submission_id": submission_id,
            "status": "queued",
            "is_duplicate": False,
        }


async def get_submission(
    pool: asyncpg.Pool,
    submission_id: str,
    user_id: str,
) -> Optional[dict]:
    """
    Retrieve a submission by ID. Users can only access their own submissions.
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT
                s.id::TEXT AS submission_id,
                s.challenge_id::TEXT,
                s.status,
                s.submitted_at::TEXT,
                s.completed_at::TEXT,
                s.runtime_ms,
                s.simulation_ns,
                s.tests_total,
                s.tests_passed,
                s.tests_failed,
                s.error_code,
                s.public_message,
                s.compiler_output,
                s.xp_awarded
            FROM public.submissions s
            WHERE s.id = $1::UUID AND s.user_id = $2::UUID
            """,
            submission_id,
            user_id,
        )

    if not row:
        return None

    return dict(row)


async def get_user_submissions(
    pool: asyncpg.Pool,
    user_id: str,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    """
    Retrieve paginated submission history for a user.
    """
    async with pool.acquire() as conn:
        total = await conn.fetchval(
            "SELECT COUNT(*) FROM public.submissions WHERE user_id = $1::UUID",
            user_id,
        )

        rows = await conn.fetch(
            """
            SELECT
                s.id::TEXT AS submission_id,
                s.challenge_id::TEXT,
                c.title AS challenge_title,
                s.status,
                s.tests_passed,
                s.tests_total,
                s.xp_awarded,
                s.submitted_at::TEXT
            FROM public.submissions s
            LEFT JOIN public.challenges c ON c.id = s.challenge_id
            WHERE s.user_id = $1::UUID
            ORDER BY s.submitted_at DESC
            LIMIT $2 OFFSET $3
            """,
            user_id,
            page_size,
            (page - 1) * page_size,
        )

    return [dict(r) for r in rows], total or 0
