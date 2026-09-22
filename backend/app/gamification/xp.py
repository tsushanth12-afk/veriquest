# ==========================================================================
# VeriQuest Backend — Gamification: XP, Levels, Streaks
# ==========================================================================

import asyncpg
import logging
from datetime import datetime, timezone, date

from ..core.config import get_settings

logger = logging.getLogger("veriquest.gamification")


def calculate_level(xp: int) -> tuple[int, str]:
    """
    Deterministic level calculation from XP.
    Returns (level_number, level_title).
    """
    settings = get_settings()
    breakpoints = settings.level_breakpoints
    level_titles = [
        "HDL Novice",        # Level 1
        "Gate Builder",      # Level 2
        "Logic Student",     # Level 3
        "Circuit Designer",  # Level 4
        "HDL Explorer",      # Level 5 (was 7 in mock — adjusted)
        "Module Architect",  # Level 6
        "RTL Engineer",      # Level 7
        "Verification Eng",  # Level 8
        "Silicon Lead",      # Level 9
        "RTL Architect",     # Level 10
        "Silicon Master",    # Level 11+
    ]

    level = 1
    for i, threshold in enumerate(breakpoints):
        if xp >= threshold:
            level = i + 1
        else:
            break

    title_idx = min(level - 1, len(level_titles) - 1)
    return level, level_titles[title_idx]


async def award_xp(
    conn: asyncpg.Connection,
    user_id: str,
    challenge_id: str,
    submission_id: str,
    xp_amount: int,
) -> dict:
    """
    Award XP for completing a challenge. Idempotent — only awards once per challenge.
    Returns the updated profile stats.
    """
    # 1. Ensure user_challenge_progress row exists
    await conn.execute(
        """
        INSERT INTO public.user_challenge_progress (user_id, challenge_id, status, attempts)
        VALUES ($1::UUID, $2::UUID, 'in_progress', 1)
        ON CONFLICT (user_id, challenge_id) DO NOTHING
        """,
        user_id,
        challenge_id,
    )

    # 2. Section 3 Requirement: Lock progress row with SELECT ... FOR UPDATE
    current_status = await conn.fetchval(
        """
        SELECT status FROM public.user_challenge_progress
        WHERE user_id = $1::UUID AND challenge_id = $2::UUID
        FOR UPDATE
        """,
        user_id,
        challenge_id,
    )

    # If already completed, idempotent no-op — no duplicate XP
    if current_status == "completed":
        logger.info(f"Idempotent check: challenge already completed for user={user_id}, challenge={challenge_id}")
        return {"xp_awarded": 0, "already_awarded": True}

    # Also double-check xp_transactions audit table
    existing_tx = await conn.fetchval(
        """
        SELECT id FROM public.xp_transactions
        WHERE user_id = $1::UUID AND challenge_id = $2::UUID AND reason = 'challenge_completion'
        """,
        user_id,
        challenge_id,
    )
    if existing_tx:
        logger.info(f"Idempotent check: XP already awarded in xp_transactions for user={user_id}")
        return {"xp_awarded": 0, "already_awarded": True}

    # 3. Record XP transaction
    await conn.execute(
        """
        INSERT INTO public.xp_transactions (user_id, challenge_id, submission_id, amount, reason)
        VALUES ($1::UUID, $2::UUID, $3::UUID, $4, 'challenge_completion')
        """,
        user_id,
        challenge_id,
        submission_id,
        xp_amount,
    )

    # Get new total XP
    new_xp = await conn.fetchval(
        "SELECT COALESCE(SUM(amount), 0) FROM public.xp_transactions WHERE user_id = $1::UUID",
        user_id,
    )

    # Calculate new level
    new_level, level_title = calculate_level(new_xp)

    # Get challenge difficulty for stats update
    difficulty = await conn.fetchval(
        "SELECT difficulty FROM public.challenges WHERE id = $1::UUID",
        challenge_id,
    )

    # Update profile
    diff_col = {
        "Easy": "easy_solved",
        "Medium": "medium_solved",
        "Hard": "hard_solved",
    }.get(difficulty, "easy_solved")

    await conn.execute(
        f"""
        UPDATE public.profiles
        SET xp = $2, level = $3, total_solved = total_solved + 1,
            {diff_col} = {diff_col} + 1, total_attempts = total_attempts + 1
        WHERE id = $1::UUID
        """,
        user_id,
        new_xp,
        new_level,
    )

    # Mark challenge as completed in progress
    await conn.execute(
        """
        UPDATE public.user_challenge_progress
        SET status = 'completed', best_submission_id = $3::UUID, completed_at = NOW()
        WHERE user_id = $1::UUID AND challenge_id = $2::UUID
        """,
        user_id,
        challenge_id,
        submission_id,
    )

    return {
        "xp_awarded": xp_amount,
        "new_xp": new_xp,
        "new_level": new_level,
        "level_title": level_title,
        "already_awarded": False,
    }


async def update_streak(conn: asyncpg.Connection, user_id: str) -> dict:
    """
    Record activity for today and update streak counters.
    Uses server timestamps (not client).
    """
    today = date.today()

    # Upsert today's activity
    await conn.execute(
        """
        INSERT INTO public.streak_activity (user_id, activity_date, activity_type, activity_count)
        VALUES ($1::UUID, $2, 'submission', 1)
        ON CONFLICT (user_id, activity_date)
        DO UPDATE SET activity_count = streak_activity.activity_count + 1
        """,
        user_id,
        today,
    )

    # Calculate current streak
    rows = await conn.fetch(
        """
        SELECT activity_date FROM public.streak_activity
        WHERE user_id = $1::UUID
        ORDER BY activity_date DESC
        LIMIT 365
        """,
        user_id,
    )

    streak = 0
    expected = today
    for row in rows:
        if row["activity_date"] == expected:
            streak += 1
            expected = expected.replace(day=expected.day - 1) if expected.day > 1 else expected
            # Simplified — production should use proper date arithmetic
            from datetime import timedelta
            expected = row["activity_date"] - timedelta(days=1)
        else:
            break

    # Update profile streak
    await conn.execute(
        """
        UPDATE public.profiles
        SET current_streak = $2,
            longest_streak = GREATEST(longest_streak, $2)
        WHERE id = $1::UUID
        """,
        user_id,
        streak,
    )

    return {"current_streak": streak}


async def check_quest_completion(conn: asyncpg.Connection, user_id: str, challenge_id: str):
    """
    Check if completing this challenge completes any quests.
    Quest completion is derived from challenge completion status.
    """
    # Find quests that include this challenge
    quest_rows = await conn.fetch(
        """
        SELECT q.id, q.title, q.xp_reward,
            (SELECT COUNT(*) FROM public.quest_challenges qc WHERE qc.quest_id = q.id) AS total,
            (SELECT COUNT(*) FROM public.quest_challenges qc
             JOIN public.user_challenge_progress ucp ON ucp.challenge_id = qc.challenge_id
             WHERE qc.quest_id = q.id AND ucp.user_id = $1::UUID AND ucp.status = 'completed'
            ) AS completed
        FROM public.quests q
        JOIN public.quest_challenges qc ON qc.quest_id = q.id
        WHERE qc.challenge_id = $2::UUID AND q.is_active = TRUE
        """,
        user_id,
        challenge_id,
    )

    for quest in quest_rows:
        if quest["completed"] >= quest["total"]:
            logger.info(f"Quest completed: {quest['title']} for user {user_id}")
            # Award quest XP bonus
            if quest["xp_reward"] > 0:
                await conn.execute(
                    """
                    INSERT INTO public.xp_transactions (user_id, amount, reason)
                    VALUES ($1::UUID, $2, $3)
                    """,
                    user_id,
                    quest["xp_reward"],
                    f"quest_completion:{quest['title']}",
                )


async def check_badge_awards(conn: asyncpg.Connection, user_id: str):
    """
    Check and award any badges the user has newly qualified for.
    Uses rule-based badge definitions from the badges table.
    """
    profile = await conn.fetchrow(
        "SELECT total_solved, current_streak, level, xp FROM public.profiles WHERE id = $1::UUID",
        user_id,
    )
    if not profile:
        return

    # Check rule-based badges
    badges = await conn.fetch(
        """
        SELECT b.id, b.name, b.rule_type, b.rule_config
        FROM public.badges b
        WHERE b.is_active = TRUE
        AND b.id NOT IN (SELECT badge_id FROM public.user_badges WHERE user_id = $1::UUID)
        """,
        user_id,
    )

    for badge in badges:
        config = badge["rule_config"] or {}
        earned = False

        if badge["rule_type"] == "solved_count":
            threshold = config.get("threshold", 1)
            earned = profile["total_solved"] >= threshold

        elif badge["rule_type"] == "streak":
            threshold = config.get("threshold", 7)
            earned = profile["current_streak"] >= threshold

        elif badge["rule_type"] == "level":
            threshold = config.get("threshold", 10)
            earned = profile["level"] >= threshold

        elif badge["rule_type"] == "xp":
            threshold = config.get("threshold", 3000)
            earned = profile["xp"] >= threshold

        if earned:
            await conn.execute(
                """
                INSERT INTO public.user_badges (user_id, badge_id)
                VALUES ($1::UUID, $2::UUID)
                ON CONFLICT (user_id, badge_id) DO NOTHING
                """,
                user_id,
                badge["id"],
            )
            logger.info(f"Badge awarded: {badge['name']} to user {user_id}")
