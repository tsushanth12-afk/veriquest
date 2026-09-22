"""
Tests for security invariants, protected field immutability, and evaluator error boundaries.
"""

from app.profile.router import ALLOWED_PROFILE_FIELDS, PROTECTED_FIELDS
from worker.execution.evaluator import normalize_evaluator_output, EvaluatorResult


def test_protected_fields_cannot_be_updated_by_users():
    """Verify Section 1: Users cannot update xp, level, role, is_admin via PATCH."""
    malicious_body = {
        "display_name": "New Name",
        "xp": 999999,
        "level": 99,
        "role": "admin",
        "is_admin": True,
        "total_solved": 100,
        "created_at": "2020-01-01",
    }

    # Simulate profile update filter
    filtered_updates = {k: v for k, v in malicious_body.items() if k in ALLOWED_PROFILE_FIELDS}

    assert filtered_updates == {"display_name": "New Name"}
    for protected in PROTECTED_FIELDS:
        assert protected not in filtered_updates


def test_evaluator_error_boundary_malformed_output():
    """Verify Section 7: Malformed simulator output maps to SYSTEM_ERROR and does NOT count as attempt."""
    malformed_stdout = "Internal error: segfault at 0x000000"
    result = normalize_evaluator_output(
        raw_output=malformed_stdout,
        returncode=0,
        timed_out=False,
    )

    assert result.status == "system_error"
    assert result.counts_as_attempt is False


def test_evaluator_error_boundary_compilation_error():
    """Verify Section 7: Compilation error DOES count as attempt."""
    compiler_error_stdout = "syntax error at line 12"
    result = normalize_evaluator_output(
        raw_output=compiler_error_stdout,
        returncode=1,
        timed_out=False,
    )

    assert result.status == "compilation_error"
    assert result.counts_as_attempt is True


def test_evaluator_error_boundary_timeout():
    """Verify Section 7: Timeout DOES count as attempt."""
    result = normalize_evaluator_output(
        raw_output="",
        returncode=-1,
        timed_out=True,
    )

    assert result.status == "timeout"
    assert result.counts_as_attempt is True
