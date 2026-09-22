# ==========================================================================
# VeriQuest Backend — Submission API Routes
# ==========================================================================

import asyncpg
from fastapi import APIRouter, Depends, Query
from typing import Optional

from ..core.security import get_current_user, AuthenticatedUser
from ..core.errors import not_found, validation_error
from ..core.rate_limit import limit_submission
from ..db.session import get_db
from .schemas import (
    SubmissionCreate,
    SubmissionResponse,
    SubmissionListResponse,
    SubmissionListItem,
)
from .service import create_submission, get_submission, get_user_submissions

router = APIRouter(prefix="/api/v1/submissions", tags=["submissions"])


@router.post("", status_code=201)
async def submit_solution(
    body: SubmissionCreate,
    user: AuthenticatedUser = Depends(get_current_user),
    pool: asyncpg.Pool = Depends(get_db),
    _rl: None = Depends(limit_submission),
):
    """
    Submit Verilog code for a challenge.
    Creates a submission record and queues it for background execution.
    Returns a submission_id for status polling.
    """
    result = await create_submission(
        pool=pool,
        user_id=user.user_id,
        challenge_id=body.challenge_id,
        submitted_code=body.submitted_code,
        idempotency_key=body.idempotency_key,
    )

    if result is None:
        raise not_found("Challenge")

    if isinstance(result, dict) and result.get("error"):
        raise validation_error(result["error"])

    # Queue the Celery task for HDL execution
    # Import here to avoid circular dependency at module load
    try:
        from worker.tasks.hdl_task import execute_hdl_submission
        execute_hdl_submission.delay(result["submission_id"])
    except ImportError:
        # Worker not available in this process — that's okay in dev
        pass

    return {
        "submission_id": result["submission_id"],
        "status": result["status"],
    }


@router.get("/{submission_id}", response_model=SubmissionResponse)
async def poll_submission(
    submission_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    pool: asyncpg.Pool = Depends(get_db),
):
    """
    Poll the status of a submission.
    Users can only access their own submissions.
    """
    result = await get_submission(pool, submission_id, user.user_id)

    if not result:
        raise not_found("Submission")

    return SubmissionResponse(**result)


@router.get("", response_model=SubmissionListResponse)
async def list_submissions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: AuthenticatedUser = Depends(get_current_user),
    pool: asyncpg.Pool = Depends(get_db),
):
    """
    List the authenticated user's submission history (paginated).
    """
    items, total = await get_user_submissions(pool, user.user_id, page, page_size)

    return SubmissionListResponse(
        submissions=[SubmissionListItem(**item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )
