"""
Tests for schema isolation, Pydantic data contracts, and gamification math.
"""

import pytest
from app.challenges.schemas import (
    PublicChallengeResponse,
    AdminChallengeDetailResponse,
    ChallengeListItem,
)
from app.gamification.xp import calculate_level, LEVEL_THRESHOLDS


def test_public_challenge_schema_omits_confidential_fields():
    """Verify Section 8: Confidential fields do not exist on PublicChallengeResponse."""
    secret_fields = [
        "official_solution",
        "hidden_testbench",
        "evaluator_type",
        "execution_profile",
        "private_notes",
    ]
    model_fields = PublicChallengeResponse.model_fields.keys()
    for field in secret_fields:
        assert field not in model_fields, f"Secret field '{field}' leaked on PublicChallengeResponse"


def test_admin_challenge_schema_includes_confidential_fields():
    """Verify Admin schema contains confidential fields."""
    admin_fields = AdminChallengeDetailResponse.model_fields.keys()
    assert "official_solution" in admin_fields
    assert "hidden_testbench" in admin_fields
    assert "evaluator_type" in admin_fields
    assert "execution_profile" in admin_fields
    assert "private_notes" in admin_fields


def test_calculate_level_thresholds():
    """Verify level calculation math across XP bounds."""
    # Level 1 at 0 XP
    lvl, title = calculate_level(0)
    assert lvl == 1
    assert title == "Novice Wireman"

    # Level 2 at 500 XP
    lvl, title = calculate_level(500)
    assert lvl == 2

    # Level 10 at 10000 XP
    lvl, title = calculate_level(10000)
    assert lvl == 10
    assert title == "Silicon Architect"
