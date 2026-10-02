# ==========================================================================
# VeriQuest Worker — Celery Configuration
# ==========================================================================

import os
from backend.app.core.task_contract import EXECUTE_TASK, VALIDATE_TASK, TASK_QUEUE

broker_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
result_backend = os.environ.get("REDIS_URL", "redis://redis:6379/0")

task_serializer = "json"
result_serializer = "json"
accept_content = ["json"]

# Task routing
task_routes = {
    EXECUTE_TASK: {"queue": TASK_QUEUE},
    VALIDATE_TASK: {"queue": TASK_QUEUE},
}

# Concurrency limits
worker_concurrency = int(os.environ.get("WORKER_CONCURRENCY", 4))

# Task time limits
task_soft_time_limit = 30  # seconds
task_time_limit = 60  # hard kill

# Retry policy
task_acks_late = True
task_reject_on_worker_lost = True
