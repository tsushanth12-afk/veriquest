# Backend startup and task-publication remediation

Date: 2026-10-01 (Asia/Calcutta). Baseline: main, `7c7d1cd6062fcde09f06078830c1c490eb5b1675`.

## Outcome and evidence boundary

**Passed the scoped disconnected implementation/regression gates.** Actual API image imports `app.main` and constructs OpenAPI without a worker package or Docker socket. Actual worker image imports/registers both canonical tasks and routes them to hdl_execution, without a production source mount. Final backend suite: **35 pytest cases passed**. Actual worker-image suite: **7 unittest methods passed**. Authentication: **17 generated-key methods passed on Windows and separately in the final API image**. Python verdict suite: **9 methods passed**. Real WASM/shared-parser regression: **146 named assertions, 53 TypeScript production WASM evaluation calls, 13 Python-parser real-WASM cases**, exit 0. Six static status-contract checks passed.

These are not real queued grading or full backend readiness. DB/broker transport in handler tests is controlled; no application database was connected, no live Redis service was used, and no normal DB-backed API lifespan started. The image's real Celery publisher was separately exercised against an unavailable broker in a network-disabled container: it correctly classified that failure as definitely unpublished. No successful Redis delivery is claimed.

No migration, Auth account, permission change, full Compose startup, commit, push or deployment occurred. No XP/accounting, frontend or sandbox workspace architecture was changed. Existing authentication/verdict controls and all previous reports were preserved. The backend-security-coder skill informed authenticated identity wiring, strict resource validation and sanitized error outcomes.

## Behavior and changed functions

### Startup and authenticated limits

`backend/app/core/rate_limit.py:RateLimit.__call__` now injects production get_optional_user. User-key limiters require a verified user; they never fall back to a header/IP identity for anonymous requests. Protected handlers retain get_current_user. IP-key limiters can remain anonymous; supplied invalid credentials still fail optional authentication rather than downgrading.

The production submission route was exercised through TestClient with generated ES256 signatures and only JWKS acquisition controlled: ten requests from subject A used A's quota despite changing X-Forwarded-For, X-Real-IP and X-User-ID; the next returned 429; subject B retained a separate quota. Missing/Basic/tampered credentials returned 401. Invalid bodies returned 422 before handler writes, with DB dependency stubbed. This proves production identity wiring/signature checks within the test, not live multi-instance Redis or proxy policy. Existing anonymous forwarded-IP trust/in-memory fallback policies were not redesigned.

### API-owned publisher

New `backend/app/core/task_publisher.py:_publish` / `publish_task` creates an API-owned Celery publisher from configured REDIS_URL, with no worker or Docker imports. New dependency-free `task_contract.py` supplies the canonical names and queue to API publisher, worker routing and worker decorators. It is included within the backend build context and also in the existing worker backend package closure.

- execute_hdl_submission: one submission UUID argument.
- validate_challenge_task: challenge UUID and administrator UUID arguments.
- Explicit queue hdl_execution, serializer JSON, generated task UUID, ignore_result true.
- Connection preflight with zero retry; connection/socket timeouts use TASK_PUBLISH_TIMEOUT_SECONDS (default 2, supported 1..5).
- Celery publication/connection retry disabled, send retry false, Redis retry_on_timeout false. Installed Kombu source was inspected: it supplies its own connection pool; installed Redis AbstractConnection defaults to zero retries in this configuration, despite Redis client's different standalone default. This is source evidence for the resolved libraries, not a broker fault-injection delivery guarantee.
- Synchronous publication runs in Starlette's threadpool, verified by a focused thread-identity test. Per-operation limits do not establish a strict total wall-clock DNS deadline. No wait_for falsely cancels a still-running send thread.

Failure before send_task is **definitely unpublished**. Any exception once send_task begins, including transport-context cleanup, is **uncertain**; no automatic resend. Only safe PublicationError text is propagated, not connection strings or raw transport exceptions. The connection context owns transport cleanup; local Celery app pool close is best-effort and cannot erase the classified outcome.

`Settings.validate_broker` restricts the configured transport to explicit redis/rediss endpoints; JWT configuration and signature rules remain unchanged. Transport TLS/deployment certification is not part of these local checks.

### Submission publication and persisted failure

`submissions/router.py:submit_solution` replaces swallowed worker import with awaited named publication. New submissions return 201 queued only after publisher success. Existing idempotency lookup results never republish, whether queued, running, accepted or failed.

`service.py:record_publication_failure` conditionally updates only a still-queued row using existing schema:

| Outcome | HTTP error | Persisted state when still queued |
| --- | --- | --- |
| Definitely not published | 503 DISPATCH_FAILED | system_error, completed_at, safe public diagnostic |
| Send outcome unknown | 503 DISPATCH_UNCERTAIN | queued, error_code/public_message identifying uncertainty; no fabricated cancellation |
| Could not save error state | 503 DISPATCH_STATE_UNKNOWN | Persistence explicitly unknown |

Responses contain the user's submission ID in a safe error message for polling; they do not claim progress/XP success. Conditional updates avoid overwriting a worker that already claimed or finalized an ambiguous send. If such a worker progressed, the polling row may already be running/terminal rather than retain the dispatch diagnostic.

Initial submission/attempt writes, idempotency uniqueness and DB/broker crash windows remain unchanged. In particular, an infrastructure failure can still have the preexisting attempt increment: **this milestone does not fix accounting**. A duplicate's 201 response references existing state, not a new publication guarantee; polling error fields remain important.

### Admin queued validation and ordinary failure finalization

`admin/router.py:validate_challenge` preserves existing administrator authorization and required auth. It checks published/pending state and nonblank evaluator text; published or already-validating challenges return **409 CONFLICT**. A conditional transaction marks nonpublished/nonpending state validating, clears validated_at and writes a validation-request audit. A racing state change that fails this claim returns conflict. It releases the DB connection before task publication.

Successful publication returns **202**, challenge_id, task_id, status validating and a message that no validation verdict exists yet. No API Docker execution remains. Definite publication failure conditionally marks validation_failed and writes dispatch-error audit; uncertainty leaves validating and records that outcome. Failed error-state recording returns 503 DISPATCH_STATE_UNKNOWN. No raw exception text is disclosed.

`worker/tasks/hdl_task.py:_validate_challenge` / `validate_challenge_task` runs only for a currently pending nonpublished challenge. Missing/malformed evaluator/profile, sandbox exception or parser exception becomes validation_failed with safe execution_error audit. Genuine parser wrong/system/configuration results also fail validation. Only production accepted can mark validated. State update and audit finalize together in a transaction and are conditional on pending/nonpublished state. Ordinary execution exceptions no longer leave validating merely because the task wrapper exited with an exception.

Database pool acquisition/finalization/close failures remain task failures and cannot guarantee a persisted terminal state. Process death, delayed delivery and concurrent edits/revalidations still require version-bound lifecycle/recovery. Checking pending state is not a revision token or exactly-once claim. Existing signed-role admin shortcut in verify_admin was preserved, not newly proven equivalent to current DB role checks.

Source inspection of unchanged AdminView shows it refreshes actual backend state and uses the returned message, rather than forcing validated. It has no automatic queued-validation polling; a later refresh is needed for completion. No browser authoring workflow or frontend change was performed.

### Execution profiles and retained grader boundaries

New `worker/execution/profile.py:parse_execution_profile` accepts actual asyncpg-shaped serialized JSON objects, dicts or SQL null/defaults. Rejects malformed/nonobject JSON, duplicate keys, unknown settings, booleans/string coercion for integer fields, unsupported values and resource-ceiling increases. Serialized JSON null is rejected rather than silently becoming defaults.

Supported bounds: timeout_ms 1..5000, memory_mb 16..256, pids_limit 1..64, max_output_bytes 1..65536; finite numeric/numeric-string CPU 0.1..1. Defaults remain 5000/256/64/65536/CPU "1.0". JSON text is bounded to 4096 characters. Invalid submission configuration saves evaluator_not_configured / INVALID_EXECUTION_PROFILE before constructing a sandbox. Badge rule_config JSON handling is explicitly outside this milestone.

Both worker paths forward validated settings to DockerSandbox. Narrow `sandbox.py` constructor/output change adds a validated max_output_bytes option and uses the smaller of that option and the existing global ceiling. This is necessary to enforce a supplied lower profile limit rather than merely validate then ignore it. Output-capture mock regression now proves a 128-byte profile budget wins over a 256-byte global budget and cannot accept a success record followed by overflow.

No network/capability/read-only/resource isolation was weakened. No workspace volume, ownership, script architecture, nonce generation, HDL capability gate, trusted parser or compilation/simulation evidence rules changed. Existing trusted-result and WASM attack tests passed. Native simulator/daemon log allocation and cleanup safety remain unproven.

## Complete milestone file list

Modified tracked files (13):

- .env.example — common broker transport guidance and publication timeout example.
- backend/app/core/config.py — Redis transport and timeout validation.
- backend/app/core/rate_limit.py — actual authentication dependency wiring.
- backend/app/submissions/router.py — publisher/error/duplicate behavior.
- backend/app/submissions/service.py — conditional publication-failure persistence only; creation/accounting untouched.
- backend/app/admin/router.py — queued validation, conflicts and failure handling.
- backend/tests/conftest.py — real current Settings/AuthenticatedUser fixtures; simulated admins require mocked role query, not is_admin argument.
- backend/tests/test_schemas.py — remove obsolete import and assert current configured level/title outputs, no XP algorithm change.
- backend/tests/test_security.py — actual profile-handler checks with controlled DB; obsolete worker parser APIs replaced by existing production verdict suite rather than fake compatibility exports.
- tests/test_verdict_integrity.py — new constructor-field mock initialization and stricter lower profile capture assertion.
- worker/celeryconfig.py — shared lightweight task contract, otherwise unchanged routing/retry/execution configuration.
- worker/tasks/hdl_task.py — profile parsing, conditional ordinary validation finalization, canonical task decorators.
- worker/execution/sandbox.py — profile-specific output limit only (five added lines).

New milestone files (9 including this report):

- .dockerignore
- backend/.dockerignore
- backend/app/core/task_contract.py
- backend/app/core/task_publisher.py
- backend/tests/test_dispatch.py
- worker/execution/profile.py
- tests/test_worker_dispatch.py
- docs/BACKEND_TASK_PUBLICATION.md
- docs/handoff/BACKEND_STARTUP_DISPATCH_REMEDIATION_REPORT.md

Preexisting untracked docs/handoff/BACKEND_STARTUP_DISPATCH_ASSESSMENT.md preserved byte-for-byte: SHA256 `c98a1d0dd2f8572f40c7ef781bd5fb11be2200a1f513f122e58c2d5cbac6432b`. Other prior reports unchanged. No generated artifacts/dependency files are intended Git changes.

## Actual commands and results

Repository cwd: `C:\Users\tsush\Desktop\veriquest`. `$D` denotes `C:\Users\tsush\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe`. API tag: vq-dispatch-api-20261001; worker tag: vq-dispatch-worker-20261001.

All Docker runs used --rm, unique vq-dispatch-* names, --network none, --read-only, --cap-drop ALL, --security-opt no-new-privileges:true. Main test/API probes added --memory 384m (worker 256m), --pids-limit 64 and --tmpfs /tmp:rw,noexec,nosuid,size=16m. No host ports, application secret env-files, DB/queue/source mounts or Docker socket supplied. Only focused test files were mounted read-only where shown.

| Command/check | Exit and actual result |
| --- | --- |
| Git status/HEAD/instruction/source/report reads | Main at baseline; initial only preexisting assessment untracked; no AGENTS found |
| `$D build --progress plain -t vq-dispatch-api-20261001 backend` | 0; actual backend build |
| `$D build --progress plain -f worker/Dockerfile -t vq-dispatch-worker-20261001 .` | 0; actual worker build after exclusions reviewed |
| `$D build --quiet -t vq-dispatch-api-20261001 backend`, worker equivalent after corrections/contract centralization | 0 each; final API image `sha256:228021a76b37bf3f15afc6e0325249e503a1f781f1b55dfe9d1937707eef45d8`; final worker `sha256:0ce314e0d14fe751b1ecf93ee12879e7fdb5678c4d0d80382c52223a8a4e62e3` |
| `$D run <isolation flags> vq-dispatch-api-20261001 python -B -m pytest tests -p no:cacheprovider` | Initial 1: 31 passed/1 failed; after correction 0: 35 passed; final image rerun **0: 35 passed**, 0.81s |
| `$D run <isolation flags> --mount type=bind,source=<repo>/tests/test_worker_dispatch.py,target=/probe_tests/test_worker_dispatch.py,readonly vq-dispatch-worker-20261001 python -B /probe_tests/test_worker_dispatch.py` | **0: 7 methods**, final 0.035s; only test file mounted, implementation from actual image |
| `.venv/Scripts/python.exe -B -m unittest discover -s tests -p test_auth_compatibility.py -v` | **0: 17 methods**, 0.209s; generated keys/controlled JWKS, no real account |
| `$D run <isolation flags> -e PYTHONPATH=/app --mount type=bind,source=<repo>/tests/test_auth_compatibility.py,target=/probe_tests/test_auth_compatibility.py,readonly vq-dispatch-api-20261001 python -B -m unittest discover -s /probe_tests -p test_auth_compatibility.py -v` | **0: 17 methods**, 0.247s, final API implementation |
| `.venv/Scripts/python.exe -B tests/test_verdict_integrity.py` | Initial 1: 3 failing subcases/1 error caused by obsolete mock initialization; corrected **0: 9 methods**, 0.186s |
| `node --experimental-strip-types tests/verdict_integrity.test.mjs --python C:\Users\tsush\Desktop\veriquest\.venv\Scripts\python.exe` | **0: 146 named assertions / 53 production WASM calls / 13 Python bridge real-WASM cases**; Docker option NOT run |
| `node tests/status_contract_consistency.test.mjs` | **0: 6/6** static checks |
| `$D run <isolation flags> vq-dispatch-api-20261001 python -B -c <final import/OpenAPI/unavailable broker assertions>` | **0**; no worker package/socket; expected route in OpenAPI; no env/venv; real disconnected publisher raises definite failure |
| `$D run <isolation flags> vq-dispatch-worker-20261001 python -B -c <final registration/routing/exclusion assertions>` | **0**; canonical names/queue; no socket/env/venv/node_modules/caches/backend tests |
| Installed Kombu/Redis source inspection in isolated API image | 0; finite transport timeouts and default connection-level zero retry confirmed for resolved versions |
| `python -B -m pip check` in both final images | 0 each, no broken requirements |
| Host in-memory AST parse of backend/worker/new worker test | 0; 43 files |
| `git diff --check` repeatedly, including final | 0; LF/CRLF informational warnings only |
| Limited scan of changed/new files before report for PEM private keys/GitHub tokens/AWS IDs/JWT literals | 0 candidates in 22 files including preserved assessment; values not printed; not exhaustive secret certification |

Initial backend test failure was the test's missing DB dependency stub: FastAPI resolves dependencies even with invalid request bodies; no external connection occurred. Corrected only the test isolation. Initial verdict failures were mocks created through __new__ without the new constructor field; corrected fixtures and strengthened profile-bound assertion, rather than adding permissive production fallbacks. One patch attempt was rejected for duplicate operations on the same test file; no partial edit from that rejected patch, corrected patches followed.

Backend test coverage includes production handlers through TestClient, verified limiter identity/quota, publisher contract/args/phase failures/thread offload, actual submission service writes against controlled connection methods, duplicate nonpublication, DB error-recording failures, admin role query/queued state/conflicts/claim race/publication errors and OpenAPI. Broker send/connection objects are mocked for phase/success tests; those assertions do not prove Redis receipt. Worker tests call production async/task wrappers and parser, with controlled asyncpg-shaped rows and sandbox results. They assert malformed profiles never instantiate sandbox, ordinary errors finalize failed audit, changed state skips execution and DB failure remains a task error. Transaction method mocks do not prove real PostgreSQL rollback/concurrency behavior.

Resolved image versions: Python 3.12.14, FastAPI 0.142.2/Uvicorn 0.54.0 in API, asyncpg 0.31.0, Celery 5.6.3, Kombu 5.6.2, Redis Python 8.1.0, Docker Python 7.2.0, Pydantic 2.13.5/settings 2.15.0; API pytest 9.1.1/pytest-asyncio 1.4.0, python-jose 3.5.0/cryptography 50.0.2/HTTPX 0.28.1. Worker image installed its declared dependencies only; no pytest added there. Lower-bounded requirements remain unlocked. Known Starlette HTTPX and leaderboard regex deprecation warnings were not treated as failures or repaired outside scope.

## Build exclusions, diff review and cleanup

Root .dockerignore allowlists worker/backend package closure, excludes backend tests plus env/secrets/venv/cache/log/key/credential artifacts. Backend-specific ignore allowlists runtime, manifest/Dockerfile and deliberate focused tests, excludes sensitive/generated files. Builds transferred small source contexts, not the root venv/node_modules. Final-image filesystem assertions verified relevant exclusions. Existing Dockerfiles/Compose/requirements were not modified. Future novel secret filenames still require review; exclusions are not a substitute for credential handling.

Reviewed complete tracked diff plus every new source/test/config/design file. No authentication verifier, trusted parser/protocol, migrations, profile handler implementation, gamification algorithm, frontend, lockfile or workspace architecture changed. Five-line sandbox addition enforces a smaller output budget without weakening any isolation flag. There are no new hardcoded credentials; preexisting safe example/default values were not used to access external services. Prior assessment hash verified unchanged.

Cleanup succeeded:

- All --rm probe containers absent in task-prefix inventory.
- Both final task image tags removed, exit 0. Four known earlier build IDs independently checked and already absent after rebuild/retag; no force/prune of unrelated resources.
- Both image dependency checks exited 0 before removal.
- Ten existing veriquest-local-test Supabase containers remained running; Vector/Logflare absent.
- No listener/worker daemon/Redis service/full Compose stack was started. In-process test clients closed; WASM worker process test completed.
- Shared Docker cache/base layers may remain. Existing ignored project venv retained; no global Python/system dependency installation.

## Acceptance and remaining gates

Satisfied locally: registration/OpenAPI; required authentication retained and verified limiter identity; API-owned bounded off-loop publisher; canonical shared task contract; truthful definite/uncertain/persistence-unknown HTTP states; duplicate nonpublication; queued admin validation with published/pending conflicts; ordinary worker validation failure finalization; strict profile normalization/resource ceilings; repaired full backend collection; actual API and worker image probes; retained auth/verdict regressions; scoped cleanup.

Explicitly blocked/not exercised:

1. **Database migration/grants/RLS/student-admin permission gate.** No DB connection or migration; mocked SQL does not prove constraints, ACLs, profile triggers or transactions. User-reported unapplied migration state not independently queried here.
2. **Actual API lifespan and real Redis delivery.** OpenAPI/import is not DB-backed Uvicorn HTTP startup. Normal lifespan intentionally not run because it connects the application DB. No real worker/broker receipt or queued grader result.
3. **Native sandbox shared workspace/UID/output/log/cleanup gate.** Existing host-daemon mount and ownership defects remain. Lower capture limit was exercised with mocked transport, not native containers.
4. **Atomic job lifecycle/crash recovery/attempts/XP accounting.** No outbox, unique idempotency guarantee, atomic claim/recovery, or accepted-plus-accounting finalization. Queued/validating can remain stuck after crashes/uncertain sends/DB outages. Initial attempt increments and badge JSON assumptions remain.
5. **Revision-safe authoring.** Guards prevent incompatible published revalidation, not stale results across concurrent edits/delayed tasks. Pending state has no durable task/revision binding. UI refresh/polling and real staff workflow remain separate validation.

Next task: review the database gate and least-privilege corrections against the disposable environment under separate authorization, before applying migrations or creating profiles/accounts. Then exercise normal API startup and one actual Redis task receipt; native grading success additionally requires the workspace milestone. Do not call the current milestone production ready or exactly-once.

## Final Git state

Branch/HEAD remain baseline main. **Nothing staged, committed or pushed.** Thirteen tracked files modified; nine new milestone files untracked, plus the one preserved preexisting untracked assessment. All previous handoff reports remain intact. This report and design documentation are part of the intended milestone, not runtime artifacts.
