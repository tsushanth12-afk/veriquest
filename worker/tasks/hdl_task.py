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
from backend.app.core.task_contract import EXECUTE_TASK, VALIDATE_TASK
from backend.app.db.runtime import create_runtime_pool, close_runtime_pool

from worker.execution.sandbox import DockerSandbox
from worker.execution.evaluator import parse_evaluation_result
from worker.execution.profile import parse_execution_profile

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
    pool = await create_runtime_pool(os.environ.get('DATABASE_URL', ''), 'vq_worker')

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
            try:
                exec_profile = parse_execution_profile(secrets["execution_profile"])
            except ValueError:
                await conn.execute(
                    """UPDATE public.submissions SET status = 'evaluator_not_configured',
                       error_code = 'INVALID_EXECUTION_PROFILE', completed_at = NOW(),
                       public_message = 'Challenge execution configuration is invalid'
                       WHERE id = $1::UUID""", submission_id,
                )
                return

            # 4. Create workspace and execute
            sandbox = DockerSandbox(**exec_profile)

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
            elif status in ["evaluator_not_configured", "system_error", "resource_limit", "cancelled"]:
                # Infrastructure/configuration condition: 0 attempt penalty assessed
                logger.warning(f"Submission {submission_id}: {status} — 0 attempt penalty assessed.")
            else:
                logger.warning(f"Submission {submission_id}: {status} — 0 attempt penalty assessed.")

    except Exception as e:
        logger.error('Worker database/execution failure; private diagnostics withheld')
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
        await close_runtime_pool(pool)


@celery_app.task(name=EXECUTE_TASK, bind=True, max_retries=1)
def execute_hdl_submission(self, submission_id: str):
    """Celery task wrapper for async HDL execution."""
    try:
        asyncio.run(_execute_hdl_submission(submission_id))
    except Exception as e:
        logger.error('Celery task failed; private diagnostics withheld')
        raise self.retry(countdown=5, exc=RuntimeError('Worker task failed')) from None


async def _validate_challenge(challenge_id: str, admin_user_id: str):
    """Ordinary execution errors finalize failure; DB outages/crashes need recovery."""
    pool = await create_runtime_pool(os.environ.get('DATABASE_URL', ''), 'vq_worker')
    try:
        async with pool.acquire() as conn:
            pending = await conn.fetchval(
                """SELECT id FROM public.challenges WHERE id = $1::UUID
                   AND is_published = FALSE AND validation_status = 'validating'""", challenge_id,
            )
            if not pending:
                return
            try:
                secrets = await conn.fetchrow(
                    """SELECT official_solution, hidden_testbench, execution_profile
                       FROM private.challenge_secrets WHERE challenge_id = $1::UUID""", challenge_id,
                )
                if not secrets or not secrets['official_solution'].strip() or not secrets['hidden_testbench'].strip():
                    raise ValueError("Missing evaluator")
                profile = parse_execution_profile(secrets['execution_profile'])
                raw = DockerSandbox(**profile).execute(
                    student_code=secrets['official_solution'], testbench=secrets['hidden_testbench'])
                evaluation = parse_evaluation_result(raw)
                status = 'validated' if evaluation['status'] == 'accepted' else 'validation_failed'
                outcome = evaluation['status']
            except Exception:
                # Do not store solution/testbench or raw transport exceptions.
                status, outcome = 'validation_failed', 'execution_error'
            async with conn.transaction():
                changed = await conn.fetchval(
                    """UPDATE public.challenges SET validation_status = $2,
                       validated_at = CASE WHEN $2 = 'validated' THEN NOW() ELSE NULL END
                       WHERE id = $1::UUID AND is_published = FALSE AND validation_status = 'validating'
                       RETURNING id""", challenge_id, status,
                )
                if changed:
                    await conn.execute(
                        """INSERT INTO public.admin_audit_log (admin_user_id, action, target_type, target_id, details)
                           VALUES ($1::UUID, 'challenge_validated', 'challenge', $2::UUID, $3::JSONB)""",
                        admin_user_id, challenge_id, json.dumps({'result': outcome, 'status': status}),
                    )
    finally:
        await close_runtime_pool(pool)


@celery_app.task(name=VALIDATE_TASK)
def validate_challenge_task(challenge_id: str, admin_user_id: str):
    return asyncio.run(_validate_challenge(challenge_id, admin_user_id))
