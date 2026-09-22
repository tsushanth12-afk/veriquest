# ==========================================================================
# VeriQuest Backend — Submission Pydantic Schemas
# ==========================================================================

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class SubmissionStatus(str, Enum):
    QUEUED = "queued"
    COMPILING = "compiling"
    RUNNING = "running"
    ACCEPTED = "accepted"
    WRONG_ANSWER = "wrong_answer"
    COMPILATION_ERROR = "compilation_error"
    SIMULATION_ERROR = "simulation_error"
    TIMEOUT = "timeout"
    RESOURCE_LIMIT = "resource_limit"
    SYSTEM_ERROR = "system_error"
    CANCELLED = "cancelled"


TERMINAL_STATUSES = {
    SubmissionStatus.ACCEPTED,
    SubmissionStatus.WRONG_ANSWER,
    SubmissionStatus.COMPILATION_ERROR,
    SubmissionStatus.SIMULATION_ERROR,
    SubmissionStatus.TIMEOUT,
    SubmissionStatus.RESOURCE_LIMIT,
    SubmissionStatus.SYSTEM_ERROR,
    SubmissionStatus.CANCELLED,
}


class SubmissionCreate(BaseModel):
    challenge_id: str
    submitted_code: str = Field(..., max_length=65536)
    idempotency_key: Optional[str] = Field(None, max_length=64)


class SubmissionResponse(BaseModel):
    submission_id: str
    challenge_id: str
    status: str
    submitted_at: str
    completed_at: Optional[str] = None
    runtime_ms: Optional[int] = None
    simulation_ns: Optional[int] = None
    tests_total: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    error_code: Optional[str] = None
    public_message: Optional[str] = None
    compiler_output: Optional[str] = None
    xp_awarded: int = 0


class SubmissionListItem(BaseModel):
    submission_id: str
    challenge_id: str
    challenge_title: Optional[str] = None
    status: str
    tests_passed: int = 0
    tests_total: int = 0
    xp_awarded: int = 0
    submitted_at: str


class SubmissionListResponse(BaseModel):
    submissions: list[SubmissionListItem]
    total: int
    page: int
    page_size: int
