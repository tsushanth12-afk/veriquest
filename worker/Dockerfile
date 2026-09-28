# ==========================================================================
# VeriQuest Worker — Dockerfile
# ==========================================================================

FROM python:3.12-slim

# Install Docker CLI for spawning execution containers
RUN apt-get update && \
    apt-get install -y --no-install-recommends docker.io && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install worker dependencies (including closure for shared gamification logic)
COPY worker/requirements.txt ./worker/requirements.txt
RUN pip install --no-cache-dir -r ./worker/requirements.txt

# Copy worker and backend packages
COPY worker ./worker
COPY backend ./backend

ENV PYTHONPATH=/app

# Start Celery worker using canonical package path
CMD ["celery", "-A", "worker.tasks.hdl_task.celery_app", "worker", "--loglevel=info", "-Q", "hdl_execution"]
