# ==========================================================================
# VeriQuest Backend — Challenge Pydantic Schemas
# ==========================================================================

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class Difficulty(str, Enum):
    EASY = "Easy"
    MEDIUM = "Medium"
    HARD = "Hard"


class IOPin(BaseModel):
    name: str
    direction: str  # input, output, inout
    width: str
    description: str


class TestCaseExample(BaseModel):
    input: str
    expectedOutput: str
    explanation: Optional[str] = None


class PublicChallengeResponse(BaseModel):
    """Public challenge data — NEVER includes official_solution or hidden_testbench."""

    id: str
    slug: str
    title: str
    description: str
    category: str
    difficulty: str
    level: int = Field(alias="level_number")
    xp: int = Field(alias="xp_reward")
    estimated_minutes: Optional[int] = 15
    starter_code: str
    input_description: Optional[str] = ""
    output_description: Optional[str] = ""
    constraints: list[str] = []
    io_pins: list[IOPin] = Field(alias="io_pins", default=[])
    examples: list[TestCaseExample] = Field(alias="public_examples", default=[])
    hints: list[str] = []
    learning_objective: Optional[str] = ""

    # User-specific progress fields (populated per-request)
    solved: bool = False
    attempts_count: int = 0
    acceptance_rate: int = 0

    model_config = {"populate_by_name": True}


class ChallengeListItem(BaseModel):
    """Compact challenge item for list views."""

    id: str
    slug: str
    title: str
    description: str
    category: str
    difficulty: str
    level: int
    xp: int
    estimated_minutes: Optional[int] = 15
    learning_objective: Optional[str] = ""
    solved: bool = False
    attempts_count: int = 0
    acceptance_rate: int = 0


class ChallengeListResponse(BaseModel):
    challenges: list[ChallengeListItem]
    total: int
    page: int
    page_size: int


class ChallengeFilters(BaseModel):
    search: Optional[str] = None
    difficulty: Optional[str] = None
    category: Optional[str] = None
    level: Optional[int] = None
    status: Optional[str] = None  # All, Solved, Unsolved
    page: int = 1
    page_size: int = 50


# ==========================================================================
# Admin-only schemas (include confidential fields)
# ==========================================================================

class AdminChallengeCreate(BaseModel):
    """Admin challenge creation — includes confidential fields."""

    slug: str
    title: str
    description: str = ""
    category: str = "Fundamentals"
    difficulty: str = "Easy"
    level_number: int = 1
    xp_reward: int = 50
    estimated_minutes: int = 15
    starter_code: str = ""
    input_description: str = ""
    output_description: str = ""
    constraints: list[str] = []
    public_examples: list[dict] = []
    io_pins: list[dict] = []
    hints: list[str] = []
    learning_objective: str = ""
    prerequisite_ids: list[str] = []

    # Confidential
    official_solution: str = ""
    hidden_testbench: str = ""
    evaluator_type: str = "hidden_testbench"
    execution_profile: dict = {}
    private_notes: str = ""


class AdminChallengeUpdate(BaseModel):
    """Partial update — all fields optional."""

    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    difficulty: Optional[str] = None
    level_number: Optional[int] = None
    xp_reward: Optional[int] = None
    estimated_minutes: Optional[int] = None
    starter_code: Optional[str] = None
    input_description: Optional[str] = None
    output_description: Optional[str] = None
    constraints: Optional[list[str]] = None
    public_examples: Optional[list[dict]] = None
    io_pins: Optional[list[dict]] = None
    hints: Optional[list[str]] = None
    learning_objective: Optional[str] = None
    prerequisite_ids: Optional[list[str]] = None

    # Confidential
    official_solution: Optional[str] = None
    hidden_testbench: Optional[str] = None
    evaluator_type: Optional[str] = None
    execution_profile: Optional[dict] = None
    private_notes: Optional[str] = None


class ValidationResult(BaseModel):
    success: bool
    challenge_id: str
    message: str
    compile_output: Optional[str] = None
    simulation_output: Optional[str] = None
    tests_passed: int = 0
    tests_total: int = 0


class AdminChallengeDetailResponse(BaseModel):
    """Full challenge schema including confidential secrets — ONLY accessible from admin endpoints."""

    id: str
    slug: str
    title: str
    description: str
    category: str
    difficulty: str
    level_number: int
    xp_reward: int
    estimated_minutes: Optional[int] = 15
    starter_code: str
    input_description: Optional[str] = ""
    output_description: Optional[str] = ""
    constraints: list[str] = []
    public_examples: list[dict] = []
    io_pins: list[dict] = []
    hints: list[str] = []
    learning_objective: Optional[str] = ""
    is_published: bool = False
    is_archived: bool = False
    validation_status: str = "draft"
    validated_at: Optional[str] = None
    published_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    # Confidential fields (never present on public models)
    official_solution: str = ""
    hidden_testbench: str = ""
    evaluator_type: str = "hidden_testbench"
    execution_profile: dict = {}
    private_notes: str = ""
