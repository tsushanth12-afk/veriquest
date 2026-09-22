# ==========================================================================
# VeriQuest Worker — Celery Configuration
# ==========================================================================

import os

broker_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
result_backend = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

task_serializer = "json"
result_serializer = "json"
accept_content = ["json"]

# Task routing
task_routes = {
    "execute_hdl_submission": {"queue": "hdl_execution"},
    "validate_challenge_task": {"queue": "hdl_execution"},
}

# Concurrency limits
worker_concurrency = int(os.environ.get("WORKER_CONCURRENCY", 4))

# Task time limits
task_soft_time_limit = 30  # seconds
task_time_limit = 60  # hard kill

# Retry policy
task_acks_late = True
task_reject_on_worker_lost = True
