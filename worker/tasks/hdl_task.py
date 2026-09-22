# ==========================================================================
# VeriQuest Worker — Celery HDL Execution Task
# ==========================================================================

import asyncio
import asyncpg
import json
import logging
import os
import tempfile
import uuid
from datetime import datetime, timezone

from celery import Celery

from .execution.sandbox import DockerSandbox
from .execution.evaluator import parse_evaluation_result

logger = logging.getLogger("veriquest.worker")

# Celery app
celery_app = Celery("veriquest-worker")
celery_app.config_from_object("worker.celeryconfig")


async def _execute_hdl_submission(submission_id: str):
    """
    Core HDL execution logic:
    1. Retrieve submission + trusted evaluator from DB
    2. Create isolated workspace
    3. Launch Docker container with resource limits
    4. Run iverilog + vvp
    5. Parse structured output
    6. Update submission record
    7. Trigger gamification on ACCEPTED
    8. Cleanup
    """
    db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")
    pool = await asyncpg.create_pool(dsn=db_url, min_size=1, max_size=2)

    try:
        async with pool.acquire() as conn:
            # 1. Retrieve submission
            submission = await conn.fetchrow(
                """
                SELECT s.id, s.user_id, s.challenge_id, s.submitted_code,
                       c.xp_reward, c.difficulty
                FROM public.submissions s
                JOIN public.challenges c ON c.id = s.challenge_id
                WHERE s.id = $1::UUID AND s.status = 'queued'
                """,
                submission_id,
            )

            if not submission:
                logger.warning(f"Submission {submission_id} not found or not queued")
                return

            # Update status to compiling
            await conn.execute(
                "UPDATE public.submissions SET status = 'compiling', started_at = NOW(), worker_id = $2 WHERE id = $1::UUID",
                submission_id,
                f"worker-{os.getpid()}",
            )

            # 2. Retrieve trusted evaluator data (from private schema)
            secrets = await conn.fetchrow(
                """
                SELECT official_solution, hidden_testbench, evaluator_type, execution_profile
                FROM private.challenge_secrets
                WHERE challenge_id = $1::UUID
                """,
                submission["challenge_id"],
            )

            if not secrets or not secrets["hidden_testbench"]:
                await conn.execute(
                    """
                    UPDATE public.submissions
                    SET status = 'system_error', error_code = 'MISSING_EVALUATOR',
                        public_message = 'Challenge evaluator not configured', completed_at = NOW()
                    WHERE id = $1::UUID
                    """,
                    submission_id,
                )
                return

            # 3. Get execution profile
            exec_profile = secrets["execution_profile"] or {}
            timeout_ms = exec_profile.get("timeout_ms", 5000)
            memory_mb = exec_profile.get("memory_mb", 256)
            cpu_limit = exec_profile.get("cpu_limit", "1.0")

            # 4. Create workspace and execute
            sandbox = DockerSandbox(
                timeout_ms=timeout_ms,
                memory_mb=memory_mb,
                cpu_limit=cpu_limit,
            )

            # Update status to running
            await conn.execute(
                "UPDATE public.submissions SET status = 'running' WHERE id = $1::UUID",
                submission_id,
            )

            result = sandbox.execute(
                student_code=submission["submitted_code"],
                testbench=secrets["hidden_testbench"],
            )

            # 5. Parse result
            evaluation = parse_evaluation_result(result)

            # 6. Update submission with results
            status = evaluation["status"]
            await conn.execute(
                """
                UPDATE public.submissions
                SET status = $2, completed_at = NOW(),
                    runtime_ms = $3, simulation_ns = $4,
                    tests_total = $5, tests_passed = $6, tests_failed = $7,
                    error_code = $8, public_message = $9, compiler_output = $10
                WHERE id = $1::UUID
                """,
                submission_id,
                status,
                evaluation.get("runtime_ms", 0),
                evaluation.get("simulation_ns", 0),
                evaluation.get("tests_total", 0),
                evaluation.get("tests_passed", 0),
                evaluation.get("tests_failed", 0),
                evaluation.get("error_code"),
                evaluation.get("public_message"),
                evaluation.get("compiler_output"),
            )

            # 7. Gamification & Attempt Tracking (Section 3 & Section 7)
            if status == "accepted":
                try:
                    from app.gamification.xp import (
                        award_xp,
                        update_streak,
                        check_quest_completion,
                        check_badge_awards,
                    )
                except ImportError:
                    from backend.app.gamification.xp import (
                        award_xp,
                        update_streak,
                        check_quest_completion,
                        check_badge_awards,
                    )

                async with conn.transaction():
                    xp_result = await award_xp(
                        conn,
                        str(submission["user_id"]),
                        str(submission["challenge_id"]),
                        submission_id,
                        submission["xp_reward"],
                    )

                    # Update XP on submission record
                    await conn.execute(
                        "UPDATE public.submissions SET xp_awarded = $2 WHERE id = $1::UUID",
                        submission_id,
                        xp_result.get("xp_awarded", 0),
                    )

                    await update_streak(conn, str(submission["user_id"]))
                    await check_quest_completion(conn, str(submission["user_id"]), str(submission["challenge_id"]))
                    await check_badge_awards(conn, str(submission["user_id"]))

                logger.info(f"Submission {submission_id}: ACCEPTED (+{xp_result.get('xp_awarded', 0)} XP)")
            elif status in ["wrong_answer", "compilation_error", "timeout"]:
                # Section 7 Rule: Compilation error, wrong answer, and timeout DO count as a normal attempt
                await conn.execute(
                    """
                    INSERT INTO public.user_challenge_progress (user_id, challenge_id, status, attempts)
                    VALUES ($1::UUID, $2::UUID, 'in_progress', 1)
                    ON CONFLICT (user_id, challenge_id)
                    DO UPDATE SET attempts = user_challenge_progress.attempts + 1;
                    """,
                    submission["user_id"],
                    submission["challenge_id"],
                )
                await conn.execute(
                    "UPDATE public.profiles SET total_attempts = total_attempts + 1 WHERE id = $1::UUID",
                    submission["user_id"],
                )
                logger.info(f"Submission {submission_id}: {status} (attempt recorded)")
            else:
                # Section 7 Rule: SYSTEM_ERROR does NOT count as a wrong-answer attempt against student
                logger.warning(f"Submission {submission_id}: SYSTEM_ERROR — 0 attempt penalty assessed.")

    except Exception as e:
        logger.exception(f"Worker error for submission {submission_id}: {e}")
        try:
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE public.submissions
                    SET status = 'system_error', error_code = 'WORKER_ERROR',
                        public_message = 'Execution system encountered an error', completed_at = NOW()
                    WHERE id = $1::UUID
                    """,
                    submission_id,
                )
        except Exception:
            pass
    finally:
        await pool.close()


@celery_app.task(name="execute_hdl_submission", bind=True, max_retries=1)
def execute_hdl_submission(self, submission_id: str):
    """Celery task wrapper for async HDL execution."""
    try:
        asyncio.run(_execute_hdl_submission(submission_id))
    except Exception as e:
        logger.exception(f"Celery task failed for {submission_id}: {e}")
        raise self.retry(countdown=5, exc=e)


@celery_app.task(name="validate_challenge_task")
def validate_challenge_task(challenge_id: str, admin_user_id: str):
    """
    Validate a challenge by running the official solution against the hidden testbench.
    Updates the challenge validation_status accordingly.
    """
    async def _validate():
        db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")
        pool = await asyncpg.create_pool(dsn=db_url, min_size=1, max_size=2)

        try:
            async with pool.acquire() as conn:
                secrets = await conn.fetchrow(
                    """
                    SELECT official_solution, hidden_testbench, execution_profile
                    FROM private.challenge_secrets
                    WHERE challenge_id = $1::UUID
                    """,
                    challenge_id,
                )

                if not secrets:
                    await conn.execute(
                        "UPDATE public.challenges SET validation_status = 'validation_failed' WHERE id = $1::UUID",
                        challenge_id,
                    )
                    return

                exec_profile = secrets["execution_profile"] or {}
                sandbox = DockerSandbox(
                    timeout_ms=exec_profile.get("timeout_ms", 5000),
                    memory_mb=exec_profile.get("memory_mb", 256),
                    cpu_limit=exec_profile.get("cpu_limit", "1.0"),
                )

                result = sandbox.execute(
                    student_code=secrets["official_solution"],
                    testbench=secrets["hidden_testbench"],
                )

                evaluation = parse_evaluation_result(result)

                if evaluation["status"] == "accepted":
                    await conn.execute(
                        "UPDATE public.challenges SET validation_status = 'validated', validated_at = NOW() WHERE id = $1::UUID",
                        challenge_id,
                    )
                    logger.info(f"Challenge {challenge_id} validation PASSED")
                else:
                    await conn.execute(
                        "UPDATE public.challenges SET validation_status = 'validation_failed' WHERE id = $1::UUID",
                        challenge_id,
                    )
                    logger.warning(f"Challenge {challenge_id} validation FAILED: {evaluation}")

                # Audit
                await conn.execute(
                    """
                    INSERT INTO public.admin_audit_log (admin_user_id, action, target_type, target_id, details)
                    VALUES ($1::UUID, 'challenge_validated', 'challenge', $2::UUID, $3::JSONB)
                    """,
                    admin_user_id,
                    challenge_id,
                    json.dumps({"result": evaluation["status"]}),
                )
        finally:
            await pool.close()

    asyncio.run(_validate())
