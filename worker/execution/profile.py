"""Normalize asyncpg JSONB text or mappings without relaxing sandbox ceilings."""
import json
from decimal import Decimal, InvalidOperation

DEFAULTS = dict(timeout_ms=5000, memory_mb=256, cpu_limit="1.0",
                pids_limit=64, max_output_bytes=65536)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate execution profile key")
        result[key] = value
    return result


def parse_execution_profile(value: object) -> dict:
    if value is None:
        value = {}
    if isinstance(value, str):
        if len(value) > 4096:
            raise ValueError("Execution profile too large")
        try:
            value = json.loads(value, object_pairs_hook=_unique_object)
        except (ValueError, RecursionError):
            raise ValueError("Invalid execution profile JSON") from None
    if not isinstance(value, dict) or set(value) - set(DEFAULTS):
        raise ValueError("Execution profile must contain only supported settings")
    profile = {**DEFAULTS, **value}
    for name, minimum, maximum in [('timeout_ms', 1, 5000), ('memory_mb', 16, 256),
                                    ('pids_limit', 1, 64), ('max_output_bytes', 1, 65536)]:
        if type(profile[name]) is not int or not minimum <= profile[name] <= maximum:
            raise ValueError("Invalid execution profile resource limit")
    cpu = profile['cpu_limit']
    if type(cpu) not in (str, int, float) or len(str(cpu)) > 32:
        raise ValueError("Invalid execution profile CPU limit")
    try:
        cpu = Decimal(str(cpu))
        if not cpu.is_finite() or not Decimal('0.1') <= cpu <= 1:
            raise ValueError("Invalid execution profile CPU limit")
    except InvalidOperation:
        raise ValueError("Invalid execution profile CPU limit") from None
    profile['cpu_limit'] = str(cpu)
    return profile
