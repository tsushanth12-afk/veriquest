"""
Tests for rate limiting algorithms and quotas (Section 6).
"""

import time
from app.core.rate_limit import _check_memory_rate_limit, _memory_store


def test_memory_rate_limiter_allows_up_to_max():
    """Verify rate limiter allows requests up to max_requests and rejects excess."""
    key = "test_action:test_ip_1"
    _memory_store[key] = []

    # Max 5 requests
    for i in range(5):
        assert _check_memory_rate_limit(key, max_requests=5, window_seconds=60) is True

    # 6th request fails
    assert _check_memory_rate_limit(key, max_requests=5, window_seconds=60) is False


def test_memory_rate_limiter_recovers_after_window():
    """Verify expired timestamps are discarded from window."""
    key = "test_action:test_ip_2"
    _memory_store[key] = [time.time() - 70]  # Expired timestamp

    # Should allow 5 requests since old one was > 60s ago
    for i in range(5):
        assert _check_memory_rate_limit(key, max_requests=5, window_seconds=60) is True

    assert _check_memory_rate_limit(key, max_requests=5, window_seconds=60) is False
