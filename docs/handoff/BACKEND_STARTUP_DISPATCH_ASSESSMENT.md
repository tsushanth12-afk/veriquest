# Backend startup and API-to-worker dispatch assessment

Date: 2026-10-01, Asia/Calcutta. Scope: current packaged API startup, submission/admin dispatch, available regressions, and a **review-only** disposable-database gate plan.

## Outcome

**Needs changes before live backend dispatch validation.** The actual `backend/Dockerfile` image built successfully. Its unmodified `app.main` import and default Uvicorn command both exited **1**, before application lifespan or HTTP startup, because `RateLimit.__call__` declares an ordinary request parameter of type `Optional[AuthenticatedUser]` rather than an injected dependency. FastAPI rejects that type during submission-route registration.

The built API image also demonstrably has no `worker` package. Current Submit silently ignores that import failure after creating a queued database row. Admin validation attempts synchronous worker/Docker execution in the API instead of publishing the existing validation task. These are separate defects: fixing startup alone will not fix dispatch.

No database/Redis connection, account creation, migration, permission change, complete Compose startup, grading container execution, implementation edit, commit, push or deployment occurred. Only this assessment document was created. Authentication remains a valid earlier scoped milestone, not evidence that the whole application starts.

## Repository and reviewed context

- Project: `C:\Users\tsush\Desktop\veriquest`.
- Branch: `main`.
- HEAD: `7c7d1cd6062fcde09f06078830c1c490eb5b1675`, `Support strict Supabase JWT authentication and verify live integration`.
- Origin: `https://github.com/tsushanth12-afk/veriquest.git`.
- Fresh `git ls-remote origin refs/heads/main` returned the same hash, exit 0. Authentication checkpoint is on remote main.
- Initial staged, unstaged and untracked lists: all empty. No tracked diff before this report.
- No applicable `AGENTS.md` found in repository searches excluding dependencies/Git/venv, or checked ancestors through `C:\`.
- Read the complete comprehensive audit and authentication remediation/live reports; current source overrides their older environment and source claims. Read current Dockerfiles, Compose, dependency files, configuration, startup/database hooks, rate limiter, authentication dependency interfaces, submission service/routes/schemas, admin routes, Celery/task/sandbox/parser implementation, backend tests, migrations, relevant README/CI instructions and focused-test source.
- Audit-context-building skill was inspected for source tracing; its required companion reference files are absent. Direct tracing and isolated execution were used instead. This did not block the assessment.

The earlier live authentication report records 40 assertions/22 real TCP HTTP cases using a disposable Supabase account on Windows and Linux. That runner was **not rerun** here: creating accounts is outside this task. Generated-key authentication regressions were rerun in the actual API image below.

## Packaging, configuration and startup

| Component | Verified source behavior | Execution boundary |
| --- | --- | --- |
| API image | Compose context `./backend`; Python 3.12 slim; copies requirements and backend context into `/app`; default `uvicorn app.main:app --host 0.0.0.0 --port 8000` | Actual build passed; import and default startup failed |
| Worker image | Root build context; installs Docker CLI and worker dependencies; copies `worker` and `backend`; `PYTHONPATH=/app`; starts `worker.tasks.hdl_task.celery_app`, queue `hdl_execution` | Dockerfile inspected; worker image not built or started |
| Redis | Compose Redis 7 Alpine, published 6379, persistent named volume; broker and results use the same URL | No Redis service started or contacted |
| Executor | `execution/Dockerfile`, Debian bookworm slim + Icarus; tag `veriquest-icarus:latest`; non-root image user | Not built or executed here |
| Supabase | External to application Compose; no PostgreSQL/Auth service in VeriQuest Compose | Ten existing named local Supabase containers remained running; database state not queried |

Compose provides ordering, not readiness/healthchecks. Backend loads optional root `.env`; worker also gets an explicit Redis service default. Backend settings default Redis to loopback, whereas worker Celery defaults to the `redis` service. Both need an explicitly reviewed common broker endpoint. Database defaults are host-loopback addresses, inappropriate for a container trying to reach the existing host Supabase port. A later container database transport needs independent reachability validation and privately supplied credentials; no actual connection string is printed here.

JWT issuer remains exactly `http://127.0.0.1:54321/auth/v1`; local allow-list is ES256, audience authenticated, tolerance 30 seconds. Container JWKS transport is separately configurable. Previous live tests proved `host.docker.internal:54321` for JWKS, not PostgreSQL connectivity or application permissions. Do not substitute a container transport hostname into the expected issuer.

`backend/app/main.py:lifespan` calls `db/session.py:init_db`, which creates an asyncpg pool (minimum 2, maximum 10, command timeout 30 seconds). No schema migration, seed, account creation or task publication is part of startup. There is no explicit pool-connect timeout configured at this call site. After startup, `close_db` is called following the lifespan yield; it is not protected by an enclosing finally in this hook.

The first reproduced failure occurs earlier: `main.py` imports `submissions.router`; its decorator resolves `limit_submission`; `rate_limit.py:RateLimit.__call__` has `user: Optional[AuthenticatedUser] = None`. FastAPI raises `FastAPIError: Invalid args for response field`, identifying that parameter type. The existing correctly injected optional authentication in challenge routes is not this problem. Changing a route response model would not wire the limiter's missing identity dependency.

`/health` is only a liveness response, not a dispatch check. `/ready` performs DB SELECT 1 and a synchronous Redis ping, returns HTTP 200 even when degraded, and bases overall status on DB alone. It does not verify schema, worker queue or execution image. No HTTP endpoint was reached in the unchanged API probe; neither health nor readiness is claimed successful.

Backend build context inventory contained 32 files, zero `.env`/venv/cache/dependency files, and zero candidates in a limited private-key/GitHub-token/AWS-ID/JWT-literal scan. No values were printed. There is no repository `.dockerignore`; root-context worker builds therefore need their own context-exclusion review before a future build, especially with the ignored project venv present. No exhaustive secret guarantee is implied.

## Submission flow and failure handling

This is a **source trace of the actual production functions**, not an executed HTTP submission. Full startup is blocked and the database remains deliberately untouched.

1. `backend/app/submissions/router.py:submit_solution`, POST `/api/v1/submissions`, nominal HTTP 201: validates `SubmissionCreate`, uses production required authentication, DB dependency and submission limiter. Body has `challenge_id`, `submitted_code`, optional `idempotency_key`. Challenge ID is a string, later cast to UUID in SQL; malformed UUID handling is not a dedicated validation path.
2. `service.py:create_submission`: checks a per-user idempotency key; checks a published challenge; checks UTF-8 code size; inserts `queued`; separately increments user/challenge attempts. No encompassing transaction. Returns ID/status and `is_duplicate`.
3. `submit_solution`: imports `worker.tasks.hdl_task.execute_hdl_submission`, then calls `.delay(submission_id)`. `except ImportError: pass` still returns the ID/status. Built-image `find_spec('worker')` returned false. **Conditional on reaching this handler and completing DB writes, packaged submissions return apparent queue success without publication.** This consequence is source verified, not reproduced with live DB writes.
4. If an import succeeds in a differently packaged environment but broker publication raises another exception, it escapes to the generic HTTP 500 handler. The previously committed queued row/attempt increment is not compensated. No outbox, publication receipt state or stale-queued recovery exists. A client can therefore receive an error while a queued row remains; uncertain broker outcomes also need later reconciliation.
5. Even an idempotency hit is redispatched: router ignores `is_duplicate`. The database idempotency index is not unique. These race/atomicity defects remain a separate milestone.
6. `worker/tasks/hdl_task.py`: Celery app loads `worker.celeryconfig`; decorators register exactly `execute_hdl_submission` and `validate_challenge_task`. Routes map both to `hdl_execution`; worker command consumes that queue. Registration/routing was observed using the API image **plus a supplemental read-only worker source mount**. This is not proof of the actual worker image, publication, broker delivery or worker execution.
7. `execute_hdl_submission` wraps `asyncio.run(_execute_hdl_submission(...))`, max retries 1, retry countdown 5. `_execute_hdl_submission` creates its own asyncpg pool from environment; pool creation is before its inner try. It selects a queued row, updates compiling without an atomic claim, reads `private.challenge_secrets`, checks missing/empty hidden bench, builds `DockerSandbox`, sets running and executes synchronously.
8. Worker assumes `execution_profile` supports `.get`. API read routes explicitly decode JSON strings, but worker pool setup configures no JSON codecs. Installed asyncpg 0.31.0 source (`pgproto/codecs/json.pyx`, `context.pyx`) shows JSONB text decoding and default `is_decoding_json()` false. This strengthens VQ-SUS-01 to a concrete default-codec incompatibility in source: a normal JSONB string will not support `.get`. **Actual database-returned values were not queried.** Normalize/validate object versus serialized JSON and reject malformed configuration before constructing the sandbox. Badge `rule_config` has the same later assumption in `xp.py:check_badge_awards`.
9. `DockerSandbox.execute` prepares the trusted bench and restricts student source before execution; parser requires adapter-owned process exits, complete capture and trusted summary. Docker-unavailable fallback cannot fabricate accepted. Existing verdict controls must remain intact.
10. `parse_evaluation_result` yields canonical status/counts/diagnostics. Worker saves terminal result before the later accepted gamification transaction. Poll/history constrain rows to the authenticated user. Accepted can become visible with unfinalized XP; later gamification error can rewrite it to system_error.

Most inner execution/database failures are swallowed after attempting to save `WORKER_ERROR`; therefore the outer Celery retry does not see them. Errors while saving the failure are also swallowed. A worker killed after compiling/running leaves a nonqueued row that queued-only redelivery ignores. Late ACKs, reject-on-worker-loss, soft 30/hard 60 second limits do not independently repair that lifecycle. Attempt double-counting, terminal finalization, idempotency, crash recovery and XP/quest reconciliation remain unfixed.

## Admin validation is a separate dispatch defect

`backend/app/admin/router.py:validate_challenge` verifies administrator access and reads solution/bench, marks validating, then imports `worker.execution.sandbox`/parser and runs them **synchronously inside the async API handler while holding a DB connection**. It does not publish `validate_challenge_task`. It does not read/apply stored execution_profile. API image excludes worker and API Compose does not mount a Docker socket. Simply copying worker code into the API is neither a queue fix nor sufficient native execution plumbing.

Exceptions become validation_failed plus HTTP 422, potentially with raw exception text in the message/audit detail. The earlier frontend fix does not change this backend behavior. Database-backed admin lookup remains in `verify_admin` for ordinary authenticated-role users; its existing `user.role == 'admin'` early return should be included in future authorization tests, not treated as proof that every request performs a current role query.

The registered worker validation task exists but has no production API publisher. It reads private data, runs the official solution, updates validated/validation_failed and audit log; it has the same JSON assumption, workspace boundary and lacks comprehensive exception-to-failure finalization. Its execution was not exercised.

Migration 001 forbids published=true with a nonpublished validation_status. Current revalidation sets validating without clearing publication; published revalidation can violate that constraint before execution. Queuing validation must define a safe interim behavior (e.g. reject revalidation of published challenges pending the revision milestone) rather than manufacture success or leave stuck validating. Revision binding, concurrent edit/publish races and complete authoring lifecycle remain later work.

## Sandbox boundary retained, native execution still gated

`worker/execution/sandbox.py:_execute_docker` creates a private temporary directory inside the worker, writes source/bench/shell and asks the host Docker daemon to bind that same absolute pathname. Compose shares only the Docker socket, not a workspace path. Worker image runs as root; fresh temporary directory permissions and forced executor UID/GID 1000 are not reconciled. The host daemon cannot be assumed to see the worker filesystem. This is still VQ-AUD-03, source verified, not a live mount/permission reproduction here.

Preserve network disabled, dropped capabilities, no-new-privileges, read-only root, memory/CPU/PID limits, bounded output and watchdog. `/workspace` is a writable bind mount, not tmpfs. Generated `run.sh` lives in the per-job workspace; no repository `execution/run.sh` exists or is required by the Dockerfile. Shell simulation timeout is fixed to five seconds while outer watchdog is configured separately. Worker only passes timeout/memory/CPU from execution_profile; profile pids/output settings are not forwarded, and output bound reads environment. Cleanup exceptions are silently swallowed. Real native workspace, process, output/log and cleanup validation is a separate required gate.

## Executed evidence and reproducibility

Docker executable: `C:\Users\tsush\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe` (called as `$D` below). Docker reported Linux engine 29.8.0. Image tag `$I` was `vq-backend-assessment-20261001-probe:latest`; image manifest-list SHA256 `1b5766caec3c2df1720d7a2cb326ff2b230df7c4aad2126594dac16e6663d0a1`.

Every probe container used a unique `vq-backend-assessment-*` name, `--rm --network none --read-only --cap-drop ALL --security-opt no-new-privileges:true`. Main import/startup/test probes additionally used `--memory 256m --pids-limit 64 --tmpfs /tmp:rw,noexec,nosuid,size=16m`. No host ports, secrets, env-file, database mount or Docker socket were supplied. Supplemental sources were mounted read-only only where explicitly noted.

| Command/check | Actual exit/result | What it proves |
| --- | --- | --- |
| Git branch/HEAD/status/origin, `git ls-remote origin refs/heads/main` | 0; main/clean, local and remote hash match | Checkpoint identity/state |
| `$D version --format '{{.Server.Os}} {{.Server.Version}}'` | 0; linux 29.8.0 | Current daemon availability |
| `$D build --progress plain -t vq-backend-assessment-20261001-probe backend` | 0 | Actual API image builds; dependencies installed only into image |
| `$D run <isolation flags> $I python -B -c <versions, find_spec, import app.main>` | **1** | `worker_available False`; app import raises FastAPIError at submission decorator |
| `$D run <isolation flags> $I` (unchanged default CMD) | **1** | Actual Uvicorn startup fails during import; lifespan/HTTP not reached |
| `$D run <isolation flags> $I python -B -m pytest tests -p no:cacheprovider` | **2** | 2 collected items, 2 collection errors; no full-suite pass |
| `$D run <isolation flags> $I python -B -m pytest tests/test_rate_limits.py -p no:cacheprovider` | **0; 2 passed** | Production in-memory limiter quota/window helpers; not auth dependency wiring or live Redis |
| `$D run <isolation flags> -e PYTHONPATH=/app --mount type=bind,source=<repo>/tests/test_auth_compatibility.py,target=/probe_tests/test_auth_compatibility.py,readonly $I python -B -m unittest discover -s /probe_tests -p test_auth_compatibility.py -v` | **0; 17 methods passed**, 0.231s | Actual image authentication implementation + generated in-memory keys and controlled JWKS transport; no real Auth login here |
| `$D run <isolation flags> --mount type=bind,source=<repo>/worker,target=/app/worker,readonly $I python -B -c <task registry/routes/socket probe>` | 0; both canonical tasks/routing matched; socket absent | Supplemental package import/registration only; no worker service or publication |
| Same supplemental worker mount, `python -B -m pytest tests/test_security.py -p no:cacheprovider` | **2**, one collection error | Obsolete `normalize_evaluator_output` import still fails when package is provided |
| Isolated `python -B -c <invoke conftest fixtures via __wrapped__, inspect levels>` | 0 as a diagnostic that catches/reports errors | Settings fixture ValidationError; both user fixtures TypeError; actual levels differ from obsolete expectations |
| Isolated installed asyncpg JSON codec source probes | 0 | Default text codec/source evidence only, not a real database round trip |
| `$D run <isolation flags> $I python -B -m pip check` | 0; no broken requirements | Built-image dependency consistency |
| `.venv/Scripts/python.exe -B tests/test_verdict_integrity.py` | **0; 9 methods passed**, 0.205s | Production Python preflight/parser and mocked Docker adapter; not real native simulation |
| `node tests/status_contract_consistency.test.mjs` | **0; 6/6** | Static status/source contract; not applied migration evidence |
| `git diff --check` before report | 0 | Tracked diff whitespace check |
| `$D ps -a --filter name=vq-backend-assessment --format '{{.Names}} {{.Status}}'` | 0; empty | No task probe containers remain |
| `$D ps --filter name=veriquest-local-test --format '{{.Names}} {{.Status}}'` | 0; ten existing containers running | Supabase retained, Vector/Logflare absent |
| `$D image rm vq-backend-assessment-20261001-probe` | 0; tagged image deleted | Scoped image cleanup; shared cache/base images not pruned |

Inline Python diagnostics were passed in PowerShell variables/command text, not saved as implementation/test files. Exact entrypoints and supplied mounts above distinguish unchanged-image probes from supplementary source probes. One initial fixture diagnostic command suffered PowerShell/native quoting damage (`SyntaxError: unterminated string literal`, container exit 1); a multiline in-memory script rerun produced the recorded fixture results. A read attempted a nonexistent migration folder/run-script path before locating actual migration/generated-shell sources; corrected reads followed. These failed diagnostics are not counted as tests. Wrapper PowerShell commands printed each child's exit; a wrapper exit 0 does not turn child exits 1/2 into successful checks.

Build resolved Python 3.12.14, FastAPI 0.142.2, Uvicorn 0.54.0, asyncpg 0.31.0, Celery 5.6.3, Redis Python 8.1.0, Docker Python 7.2.0, pytest 9.1.1, pytest-asyncio 1.4.0, python-jose 3.5.0, cryptography 50.0.2. Pydantic 2.13.5/settings 2.15.0 and HTTPX 0.28.1 appeared in build output. Requirements are lower-bounded, not locked; results apply to these resolved versions. Starlette TestClient emitted the previously known HTTPX deprecation warning, not a test failure.

### Backend test defects

- `backend/tests/test_schemas.py` imports nonexistent `LEVEL_THRESHOLDS`; expected titles `Novice Wireman`/`Silicon Architect` and level 10 at 10000 conflict with actual `(1, HDL Novice)`, `(2, Gate Builder)` at 500 and `(11, Silicon Master)` at 10000.
- `test_security.py` imports obsolete `normalize_evaluator_output`/`EvaluatorResult`, not current `parse_evaluation_result`. Its profile check locally filters a dict rather than invoking the PATCH handler; even repaired, that alone would not verify direct DB permissions.
- `conftest.py:mock_settings` passes five unsupported fields: supabase_anon_key, supabase_service_role_key, supabase_jwt_secret, backend_cors_origins, environment. Direct invocation produced ValidationError. Student/admin fixtures supply unsupported `is_admin`; both produced TypeError. Neither fixture establishes database administrator authority.
- Only two backend limiter tests can currently run independently. There are no usable live API-to-broker-to-worker-to-database regression tests in this backend suite. CI's current PYTHONPATH/import expectations need repair against canonical package locations, not fake compatibility symbols in production.

## Database gate plan — not executed

This plan requires separate authorization before migrations, test identities, grants or local data are changed. The user-reported absence of VeriQuest migrations is retained as **reported**, not independently queried. No database connection was made.

1. **Target and recovery gate:** privately verify the disposable `veriquest-local-test` project and host port 54322, never a hosted endpoint. Inventory existing schema/migration history/default grants/exposed schemas and Auth users read-only under explicit database-access authorization. Snapshot the disposable database or agree on a recoverable reset boundary. Do not reset existing services or apply scripts blindly.
2. **Prerequisites:** running Supabase supplies auth.users/auth.uid(), supported UUID extension, and administrative DDL capability. Separate privately configured API/worker DB roles from untrusted authenticated/anon roles; both services need reviewed privileges, worker needs private evaluator reads. A Supabase service API credential is not a substitute for asyncpg SQL privileges. Establish host/container PostgreSQL reachability independently.
3. **Ordered scripts:** `001_initial_schema.sql` creates tables/private schema/functions/triggers/RLS; `002_seed_demo_challenge.sql` inserts/upserts demo metadata and private evaluator; `003_status_contract.sql` replaces submission CHECK to include evaluator_not_configured. 003 structurally depends on 001; 002 requires public challenges/private secrets from 001. README lists only 001/002 and is incomplete. 001 is not an idempotent replay migration; migration runner must track application. Use stop-on-error and an explicitly reviewed transaction strategy rather than autocommitting a partial schema.
4. **No automatic application:** current API startup only creates a pool; Dockerfiles/Compose/Celery contain no migration or seed command. This VeriQuest `supabase` folder contains migrations but no CLI config/seed runner. Do not copy them into the separately running CLI project or invoke reset/start as an unreviewed shortcut. Seed 002 explicitly marks demo published/validated and sets timestamps **without execution**; this is seed data, not proof of native validation. A replay that changes secrets can trigger invalidation after its metadata upsert.
5. **Permission gate before scoring tests:** migration 001 contains no explicit GRANT/REVOKE and no RLS on private.challenge_secrets or challenge_prerequisites. Actual default ACLs/private exposure must be inspected, not inferred from schema names. `profiles_update_own` constrains ownership, not XP/level/streak/solved/attempt columns; `submissions_insert_own` constrains owner, not pregraded status/counts/XP. Do not claim VQ-AUD-01 fixed by API allowlists or apply permissive schema then expose it to real users. Review a least-privilege permission correction separately; verify student denial of protected writes/pregraded inserts/private reads/role grants/other users' submissions and safe allowed profile edits. RLS does not constrain a bypass-RLS administrative SQL connection the same way as Auth PostgREST.
6. **Identity/profile gate:** `handle_new_user` SECURITY DEFINER trigger runs after new auth.users insert, takes username/display name from metadata or email local-part, and inserts a UUID-linked profile. It has no explicit search_path hardening and username uniqueness can reject collisions. It does not backfill preexisting Auth users or automatically insert a student role row. Use unique disposable identities **after** schema setup or authorize explicit test-profile backfill; confirm matching Auth subject/profile ID. Admin test identity needs a separately authorized trusted user_roles admin row, not client metadata/is_admin flags. Audit log also requires a valid profile FK.
7. **Gate assertions:** confirm all three migration versions and canonical CHECK, profile trigger behavior, secrets edit invalidation, real JSONB returned types, server SQL privileges, and student/admin visibility through actual API/PostgREST. Include two disposable users and one explicitly authorized admin only when authorized. Verify ordinary student JWT role cannot substitute for a database admin grant. Do not infer safe grants from mock tests.
8. **Live job prerequisites:** corrected startup/publisher/worker configuration, local isolated Redis broker/worker, reviewed schema/permissions/test student profile, published compatible bench, private worker access, executor image and corrected daemon-visible workspace ownership. Then submit one ordinary **wrong** solution first to observe HTTP publication, worker receipt, process execution, polling and durable result without challenge XP; correct accepted/scoring checks follow accounting review. A worker receipt/system_error can be a transport checkpoint but is **not** completed native grading validation. Clean only authorized test rows/accounts/services; retain the running Supabase environment.

## Smallest next implementation milestone

**Make the API import/start and publish canonical worker tasks truthfully, without importing execution code.** Do not add the Docker socket to the API or weaken the verdict protocol to pass tests.

Affected files: `backend/app/core/rate_limit.py`; a small API-owned Celery publisher/config module included by the existing backend build context; `backend/app/submissions/router.py` and narrowly scoped submission failure persistence in `service.py`; `backend/app/admin/router.py`; `worker/celeryconfig.py`/`worker/tasks/hdl_task.py` for matching names/config normalization and truthful validation failure handling; focused backend tests/fixtures and startup/dispatch harness. Compose/env documentation changes only if needed to make explicit broker/database/JWKS transport consistent. Keep shared configuration build-context placement deliberate; importing a root-only shared package would recreate the packaging defect.

Intended behavior and acceptance:

- Production `app.main` import and OpenAPI construction succeed in the actual API image with no worker package/socket. Authenticated submission/admin rate limiters inject the verified identity and key by user, with tests proving distinct identities and header changes cannot replace identity. Do not bypass the limiter in production to achieve startup.
- API publishes explicit task names/IDs to `hdl_execution` using JSON arguments through an API-owned Celery client, without importing Docker/worker execution. Keep synchronous broker calls off the async event loop and bound retries/connection waits.
- Submission only reports successful queueing after the publisher succeeds. Definite publish failure gives structured infrastructure error and truthfully persists a failure/recovery state instead of silent queued success. Uncertain publication and crash windows must be documented; do not claim a two-step DB/broker write is atomic. Do not redispatch an already terminal idempotent response. Full exactly-once semantics/outbox/reaper remains the atomicity milestone.
- Admin validation dispatches to the worker, returns a truthful queued/validating response with challenge identity, and can be observed via existing authorized detail polling. Broker/execution failure cannot leave validating indefinitely or report validated. Preserve admin authorization. Account for published-state CHECK without inventing revision success; revision-aware lifecycle remains later work.
- Worker normalizes and validates execution-profile JSON from dict/string/null inputs and fails closed on malformed types/configuration; preserve existing security bounds. Test with asyncpg-shaped rows, not only dict fixtures. Broader badge/XP changes remain separate.
- Repair obsolete backend tests/fixtures against real production interfaces; full collection must succeed and failed assertions must exit nonzero. Cover built-image import, limiter identity dependency, named publisher routing/args, unavailable broker, API handler failure state, duplicates, queued admin validation, worker registration, profile JSON normalization and worker failure persistence. Clearly label mocked transports/DB versus real Redis/worker integration.
- Live acceptance additionally requires normal API lifespan and HTTP startup against the separately authorized disposable DB, real Redis publication and real worker receipt. One job must progress to the expected persisted result after the workspace gate; mocked task publication or a registration-only import is insufficient.

**Separate required follow-ups:** database permission gate (VQ-AUD-01); daemon-visible workspace/UID/output/cleanup fix (VQ-AUD-03); atomic claim/creation/idempotency/finalization/recovery and consistent attempts (VQ-AUD-06/07); XP/quest ledger reconciliation (VQ-AUD-05); revision-bound authoring (VQ-AUD-09). These remain release blockers, not implicitly included or declared solved by startup/dispatch work.

Exact next step: authorize and implement the focused startup/publisher milestone above, initially using disconnected built-image and controlled transport/database regressions. Separately approve the reviewed disposable migration/permission gate before live API/database/queued grading work. No further infrastructure installation is shown necessary for the isolated API-image checks; real queued grading still requires the listed service/schema/workspace prerequisites.

## Cleanup and final state

All named probe containers used --rm and were absent in final inventory. The one task-created backend image was removed successfully. No listeners or persistent services were created. Existing ten Supabase containers remained running; no global prune was used. Shared Docker build cache/base/dependency layers may remain. Host dependencies, prior reports, tests and implementation are unchanged.

Final intended Git state: branch/HEAD unchanged; no staged or tracked modifications; only `docs/handoff/BACKEND_STARTUP_DISPATCH_ASSESSMENT.md` untracked. No implementation changes, commit or push. Full backend HTTP startup, live dispatch, database permissions/migration execution, native sandbox and production readiness are **not verified**.
