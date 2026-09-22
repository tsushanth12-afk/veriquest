# ==========================================================================
# VeriQuest Worker — Dockerfile
# ==========================================================================

FROM python:3.12-slim

# Install Docker CLI for spawning execution containers
RUN apt-get update && \
    apt-get install -y --no-install-recommends docker.io && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir celery redis asyncpg docker

COPY . .

# Mount Docker socket from host
CMD ["celery", "-A", "tasks.hdl_task.celery_app", "worker", "--loglevel=info", "-Q", "hdl_execution"]
