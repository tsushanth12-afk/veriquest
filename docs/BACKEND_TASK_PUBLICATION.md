# Backend task publication contract

The backend image owns its publisher in `app.core.task_publisher`. It imports no
worker package and needs no Docker socket. Both images include the dependency-free
`backend/app/core/task_contract.py`; the API uses its local `app` package and the
worker uses its existing `backend.app` package. Queue: `hdl_execution`. JSON tasks:

- `execute_hdl_submission(submission_id)`
- `validate_challenge_task(challenge_id, admin_user_id)`

All arguments are UUID strings. The API generates a task UUID, disables automatic
publication retry and ignores Celery result storage; database polling is authoritative.
`REDIS_URL` must identify the same broker/database index for API and worker. Host
example: `redis://localhost:6379/0`. Compose example: `redis://redis:6379/0`.
Compose's optional env file does not translate host-loopback settings automatically.
`TASK_PUBLISH_TIMEOUT_SECONDS=2` (1..5) bounds connect/socket operations. Publication
is offloaded to a thread; these are per-operation limits, not a strict wall-clock
deadline for DNS or every library operation. Cancellation does not kill a sending
thread. No worker result backend is contacted by this API publisher.

## Outcomes

New Submit returns HTTP 201 only after publisher success. Idempotency lookups return
the existing ID/status without publication. This does not imply an existing queued
submission was delivered; inspect its polling error fields.

Failure before entering `send_task` is definitely not published: HTTP 503,
`DISPATCH_FAILED`; a still-queued submission becomes system_error. An exception
after entering send, including connection-context cleanup, is conservatively
`DISPATCH_UNCERTAIN`: HTTP 503, ID for polling; still-queued state retains that error
instead of cancelling a possibly delivered job. Conditional writes do not overwrite
already claimed/terminal jobs. Failed error-state persistence returns HTTP 503
`DISPATCH_STATE_UNKNOWN`. Error responses do not reveal transport exceptions.

Admin validation returns HTTP 202 with challenge ID, task ID and validating status,
not a grading success. Existing authorized challenge-detail/list routes observe its
eventual state. Published or already-pending challenges return HTTP 409 CONFLICT.
Definite failure changes still-pending validation to validation_failed; uncertain
failure leaves it pending and writes a dispatch-error audit event. Worker ordinary
configuration/execution/parser errors finalize validation_failed plus a safe audit
outcome; final state and audit commit together. DB outages cannot guarantee persistence.

No frontend files changed: the current admin view refreshes backend state and uses
the returned pending message. It has no automatic queued-validation polling, so a
later refresh is needed to see completion. No end-to-end authoring claim is made.

## Execution profiles

Worker accepts a mapping, serialized JSON object or SQL null (defaults). Serialized
JSON null, duplicate keys, unknown settings, arrays, booleans and malformed values
fail closed. Integer settings are strict (no boolean/string coercion): timeout_ms
1..5000, memory_mb 16..256, pids_limit 1..64, max_output_bytes 1..65536. CPU is a finite
number/numeric string in 0.1..1. Defaults are 5000, 256, 64, 65536, CPU "1.0".
Output capture uses the smaller of the profile and existing global ceiling.
Unsupported configuration cannot construct the sandbox. This does not change
grader nonce/process evidence or the native workspace/mount architecture.

## Unresolved gates

Database creation/permissions, real Redis delivery and normal API lifespan;
daemon-visible sandbox workspaces/UID/log/cleanup; atomic submission creation and
claims, broker/DB crash windows, idempotency uniqueness, stuck-job recovery, attempts,
XP/quest/badge accounting and JSON normalization; version-bound validation.
There is no outbox or exactly-once guarantee. A crash before publish can leave
queued/validating rows; an uncertain outcome may remain pending indefinitely.
Do not republish automatically or treat mocked/image-import tests as live grading.

Focused checks: backend image `python -B -m pytest tests -p no:cacheprovider`;
worker image with read-only test-file mount `python -B /probe_tests/test_worker_dispatch.py`;
host auth and verdict commands are recorded in the remediation report. No migration
or full Compose startup is required or authorized by those checks.
