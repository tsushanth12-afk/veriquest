# ==========================================================================
# VeriQuest Worker — Evaluation Result Parser & Error Boundaries
#
# Section 7 Error Boundary Rules:
# - Malformed or missing evaluator output -> SYSTEM_ERROR
#   - Does NOT count as a wrong-answer attempt against the student
#   - Does NOT consume their attempt count
# - Compilation error, wrong answer, and timeout DO count as normal attempt
# - Never let a SYSTEM_ERROR silently resolve to ACCEPTED or WRONG_ANSWER
# ==========================================================================

import re
import logging
from typing import Optional

logger = logging.getLogger("veriquest.evaluator")


def parse_evaluation_result(execution_result: dict) -> dict:
    """
    Parse the structured output from the Docker sandbox execution.
    Normalizes both VERIQUEST_STATUS and VQ_RESULT formats.
    """
    stdout = execution_result.get("stdout", "")
    stderr = execution_result.get("stderr", "")
    exit_code = execution_result.get("exit_code", -1)
    timed_out = execution_result.get("timed_out", False)

    combined_output = stdout + "\n" + stderr

    # 1. Handle timeout
    if timed_out:
        return {
            "status": "timeout",
            "tests_total": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "runtime_ms": 5000,
            "simulation_ns": 0,
            "error_code": "TIMEOUT",
            "public_message": "Execution exceeded the 5.0s time limit. Check for infinite combinational loops.",
            "compiler_output": _sanitize_output(stdout[:2000]),
            "counts_as_attempt": True,
        }

    # 2. Check for explicit compilation errors
    if "COMPILATION_ERROR" in stdout or (exit_code != 0 and "syntax error" in combined_output.lower()):
        compile_errors = []
        for line in combined_output.split("\n"):
            line_clean = line.strip()
            if any(k in line_clean.lower() for k in ["error", "syntax", "undefined", "unknown"]):
                compile_errors.append(line_clean)

        return {
            "status": "compilation_error",
            "tests_total": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "runtime_ms": 0,
            "simulation_ns": 0,
            "error_code": "COMPILATION_ERROR",
            "public_message": "\n".join(compile_errors[:5]) if compile_errors else "Verilog syntax or compilation error.",
            "compiler_output": _sanitize_output(stdout[:2000] or stderr[:2000]),
            "counts_as_attempt": True,
        }

    # 3. Extract status marker (supports both VERIQUEST_STATUS and VQ_RESULT)
    vq_status = _extract_status_marker(stdout)
    vq_total = _extract_count(stdout, ["TOTAL", "VQ_TESTS"])
    vq_passed = _extract_count(stdout, ["PASSED", "VQ_PASSED"])
    vq_failed = _extract_count(stdout, ["FAILED", "VQ_FAILED"])
    vq_runtime = _extract_int(stdout, "VQ_RUNTIME_MS") or 15
    vq_sim_ns = _extract_int(stdout, "VQ_SIM_NS") or 100

    # 4. Section 7 Rule: Malformed or missing evaluator output -> SYSTEM_ERROR
    if vq_status is None:
        logger.warning(f"Malformed or missing evaluator output: {stdout[:400]}")
        return {
            "status": "system_error",
            "tests_total": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "runtime_ms": 0,
            "simulation_ns": 0,
            "error_code": "MALFORMED_OUTPUT",
            "public_message": "Execution engine produced unparseable output. Logged for administrator review.",
            "compiler_output": _sanitize_output(stdout[:1000]),
            "counts_as_attempt": False,  # Section 7: Does NOT consume student attempt
        }

    # 5. Accepted
    if vq_status in ["ACCEPTED", "PASS"]:
        return {
            "status": "accepted",
            "tests_total": vq_total or vq_passed or 1,
            "tests_passed": vq_passed or vq_total or 1,
            "tests_failed": 0,
            "runtime_ms": vq_runtime,
            "simulation_ns": vq_sim_ns,
            "error_code": None,
            "public_message": f"All {vq_passed or vq_total or 1} test cases verified successfully.",
            "compiler_output": _sanitize_output(stdout),
            "counts_as_attempt": True,
        }

    # 6. Wrong Answer
    if vq_status in ["WRONG_ANSWER", "FAIL"]:
        return {
            "status": "wrong_answer",
            "tests_total": vq_total or 1,
            "tests_passed": vq_passed or 0,
            "tests_failed": vq_failed or 1,
            "runtime_ms": vq_runtime,
            "simulation_ns": vq_sim_ns,
            "error_code": "WRONG_ANSWER",
            "public_message": f"Simulation output mismatch: {vq_passed or 0}/{vq_total or 1} tests passed.",
            "compiler_output": _sanitize_output(stdout),
            "counts_as_attempt": True,
        }

    # 7. Fallback unknown status -> SYSTEM_ERROR
    return {
        "status": "system_error",
        "tests_total": 0,
        "tests_passed": 0,
        "tests_failed": 0,
        "runtime_ms": 0,
        "simulation_ns": 0,
        "error_code": "UNKNOWN_RESULT",
        "public_message": f"Unknown simulation status returned: {vq_status}",
        "compiler_output": _sanitize_output(stdout[:1000]),
        "counts_as_attempt": False,
    }


def _extract_status_marker(text: str) -> Optional[str]:
    """Find VERIQUEST_STATUS: <STATUS> or VQ_RESULT:<STATUS>."""
    m = re.search(r"^(?:VERIQUEST_STATUS|VQ_RESULT)\s*:\s*([A-Z_]+)", text, re.MULTILINE)
    if m:
        return m.group(1).strip().upper()
    return None


def _extract_count(text: str, prefixes: list[str]) -> Optional[int]:
    """Extract integer count for given prefixes (e.g. TOTAL, PASSED, FAILED)."""
    for p in prefixes:
        m = re.search(rf"^{re.escape(p)}\s*:\s*(\d+)", text, re.MULTILINE)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                continue
    return None


def _extract_int(text: str, field: str) -> Optional[int]:
    """Extract field integer."""
    m = re.search(rf"^{re.escape(field)}\s*:\s*(\d+)", text, re.MULTILINE)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            return None
    return None


def _sanitize_output(text: str, max_len: int = 4000) -> str:
    """
    Sanitize simulation output for student view:
    Removes filesystem paths to hidden testbench or internal scripts.
    """
    lines = []
    for line in text.split("\n"):
        if "/workspace/testbench.v" in line or "/workspace/run.sh" in line:
            continue
        if "private." in line or "challenge_secrets" in line:
            continue
        lines.append(line)
    return "\n".join(lines)[:max_len]
