# Database permission and identity remediation — prepared, not applied

Date: 2026-10-01, Asia/Calcutta. Repository `C:\Users\tsush\Desktop\veriquest`.
Branch main; HEAD remains `7c7d1cd6062fcde09f06078830c1c490eb5b1675`.
Origin verified as github.com/tsushanth12-afk/veriquest, without printing credentials.

## Outcome and evidence boundary

Implemented the requested source/configuration hardening and separately opt-in
verification tools. **Disconnected implementation gates passed; live database
permission safety is NOT verified.** Actual API image: **52 pytest cases passed**.
Actual worker image: **7 unittest methods passed**. Production runner: **10 methods
passed**. Authentication regressions: **17 methods passed on Windows and separately
in the final API image**. Python verdict regressions: **9 methods passed**. Static
status-contract checks: **6/6 passed**. Do not add repeated suite runs or subcases
together as a unique coverage count.

The final runner's actual **read-only** preflight succeeded against the independently
verified disposable project: fresh state, **0 application tables, 0 application
roles, 0 Auth users**. Bootstrap/apply, isolated PostgreSQL rehearsal and real
permission harness **were not run**, because this task prohibits provisioning or
changing the running database. No accounts, roles, grants, schema, application
rows, seeds, Supabase settings, migrations, commits, pushes or deployments changed.
No application stack/queue/worker daemon was started. Existing ten local Supabase
containers remained running.

The backend-security-coder skill guided explicit privileges, trusted DB authority
and sanitized error boundaries. No AGENTS.md was found in the previously checked
repository/ancestors; the assessment/instructions and current source were reviewed.
Existing handoff reports and historical migrations remain byte-for-byte unchanged.

## Files/functions changed by this milestone

Modified existing files (including two already-untracked dispatch tests):

- `.env.example`: intentionally blank private DSN inputs; no administrative SQL example/default.
- `docker-compose.yml`: API_DATABASE_URL -> API process DATABASE_URL;
  WORKER_DATABASE_URL -> worker process DATABASE_URL; separate optional ignored
  `.env.api.local`/`.env.worker.local`; no wholesale root env injection. Common Redis mapping.
- `backend/app/core/config.py:Settings`: required SecretStr database_url,
  validate_database, input-hidden errors; unknown shared dotenv fields ignored.
- `backend/app/db/session.py:init_db/close_db`: explicit vq_api verified pool,
  finite connect timeout and safe initialization/cleanup errors.
- `backend/app/admin/router.py:verify_admin`: always queries current user_roles
  for verified UUID; signed role=admin is not authority. Missing grant -> 403
  through handlers; lookup failure -> safe 503 SYSTEM_ERROR.
- `backend/app/main.py:sanitized_request_failures/generic_error_handler`: safe
  unexpected HTTP 500, without rethrowing pre-response driver exceptions to
  Uvicorn's raw ASGI exception logger. Normal AppError handlers retain truthful errors.
- `backend/app/profile/router.py:update_profile`: display type/length checks;
  nonexistent profile -> 404, not fake updated. Protected-only no-op and mixed
  allowlist behavior preserved; protected fields never sent to SQL.
- `worker/tasks/hdl_task.py:_execute_hdl_submission/_validate_challenge` and wrapper:
  required vq_worker pool, no postgres fallback, safe task/connection/cleanup errors.
  No accounting, dispatch algorithm, grader protocol or workspace redesign.
- `backend/tests/conftest.py`, `backend/tests/test_dispatch.py`,
  `tests/test_worker_dispatch.py`, `tests/test_auth_compatibility.py`,
  `tests/auth_live_runtime/service.py`: deliberate unused dummy DB configuration
  or mocks targeting the new production pool boundary. Auth-only service never
  connects that dummy database endpoint.

New files (13, including this report):

- `backend/app/core/database_config.py:validate_database_url`.
- `backend/app/db/runtime.py:verify_runtime_role/create_runtime_pool/close_runtime_pool`.
- `backend/tests/test_database_authority.py`.
- `supabase/migrations/004_permission_gate.sql`.
- `supabase/migrations/005_profile_identity_gate.sql`.
- `tools/database_policy.json` — exact reviewed column matrix.
- `tools/database_migrations.json` — canonical-LF SQL/policy hashes and deferred 002.
- `tools/database_gate.py` — local plan/preflight, separate private bootstrap,
  atomic apply, role/structural/ACL assertions.
- `tools/database_rehearsal.py` — opt-in isolated transaction/checksum rehearsal.
- `tests/test_database_gate.py` — production runner/code-generator/guard tests.
- `tests/database_permission_live.py` — opt-in actual Auth/PostgREST/API/SQL harness.
- `docs/DATABASE_PERMISSION_GATE.md` — reviewed runbook/recovery and commands.
- This report.

## Ownership, ACL/RLS and function model (source verified)

Historical 001/002/003 are untouched. The only supported initial structural sequence
is **001 -> 003 -> 004 -> 005, atomically**; 002 remains a deferred demo fixture,
not a validated execution or tracked migration. Existing untracked/historical
deployments are deliberately refused, not automatically adopted or modified.

Owner vq_owner: NOLOGIN/NOINHERIT, owns all fourteen application tables, private
schema, five helpers and owner-only private.schema_migrations. No superuser,
BYPASSRLS, role/DB creation or replication attribute. The owner intentionally is
not FORCE-RLS constrained inside the narrowly coded trusted signup/invalidation
functions. Only supabase_admin has owner membership; API/worker/authenticator/
clients cannot assume it. Platform public/Auth/vault ownership is not transferred.

Runtime vq_api/vq_worker: separate LOGIN passwords, NOINHERIT, no elevated flags,
memberships, application ownership, Auth/vault schema access or public/private
CREATE. Production startup inspects actual connected flags/memberships/ownership
and platform-schema access; username checks alone are not treated as sufficient.

004 explicitly revokes **table AND column** SELECT/INSERT/UPDATE/REFERENCES and
other table powers on the named application set, removes **every legacy policy**,
enables RLS, then installs 59 command-specific explicit-role policies and column
grants. No DELETE/TRUNCATE/REFERENCES/TRIGGER/MAINTAIN/grant-option application
rights are granted to clients or runtimes. No UUID-schema sequence rights needed.
Application service_role direct table rights are also removed; it is not a runtime.

| Principal | Reads | Writes / enforced limits |
| --- | --- | --- |
| anon | Published nonarchived challenge public fields, active quest/badge definitions, visible prerequisite/quest links | None |
| authenticated | Same catalog; only own profile/safe submission history/progress/XP/streak/awards/role fields | Own display_name/bio/avatar_url only, USING + WITH CHECK; no authoritative insertion/deletion |
| vq_api | Current API union: profiles/rank, public challenge lifecycle, progress/history, selected XP, badges/awards, role authority/audits; required private authoring columns | Queued input insertion with no grading evidence/awards; narrow queued/system_error failure updates; display edits; source-required attempt upsert guarded against invented completion; draft metadata/secret authoring/lifecycle and append audits. No XP/profile scoring/role/result-count writes |
| vq_worker | Input/status, necessary evaluator fields (not notes/vector config), scoring/profile/progress/ledger/streak/quest/badge definitions | Result/stage/XP fields, current accounting writes/locks/upserts, append awards/audits; pending unpublished -> validated/validation_failed only. No submitted input/identity, publish, curriculum/secret editing, role/Auth/vault/audit-history access |

Exact columns are in database_policy.json and explicit migration GRANTs. Current
SELECT/WHERE/RETURNING/expression/upsert/row-lock requirements were traced through
challenge/profile/leaderboard/submission/admin SQL and worker/gamification SQL.
No production query was rewritten to evade permissions. Runtime policies use
deliberate static service authority, not absent JWT claim settings. One API pool
still includes administrator private authoring capabilities: HTTP authorization
remains essential, and separate admin-pool isolation is future defense in depth.

Five helpers have trusted owner, empty search_path, qualified relation/built-in
references and no client/runtime EXECUTE. handle_new_user and secret invalidation
are SECURITY DEFINER; timestamp and API challenge/progress guards are invoker.
The latter must see the true runtime current_user, not owner authority. Guarded
API INSERT/upserts cannot invent student completion or native validated status.
Secret invalidation executes as owner, permitting its existing required draft
transition without exposing a client helper. Revision-safe authoring remains unfixed.

005 generates username `vq_user_` + the full 32-character UUID, ignores requested
username/role/scoring metadata, inserts zero scoring/level 1 and literal student
role. Display string is trimmed/truncated to 100; empty/malformed -> Student,
with string full_name as fallback only if display_name is not a string. Existing
UUID profiles/stats/roles are not overwritten. Reserved-prefix constraint uses
literal left(username,8), not LIKE underscores; nonnegative solved/attempt counts
and nullable display bounds are added. No silent rename/backfill exists.

References consulted for source design: PostgreSQL [CREATE TRIGGER](https://www.postgresql.org/docs/17/sql-createtrigger.html)
requires creation-time trigger/function privileges; [CREATE TABLE](https://www.postgresql.org/docs/17/sql-createtable.html)
requires REFERENCES for FK installation. These documentation checks are not native execution evidence.

## Runner, configuration and credential handling

database_gate defaults to plan (Docker metadata + pinned checksums only). Preflight
queries use explicit READ ONLY/ROLLBACK, bounded statements and structure/counts
only. It verifies exact local project/workdir/container labels, mapped 54322 and
public/graphql_public exposure. No configurable hosted URL/fallback exists.
Unexpected namespaces, partial/unknown schema/ledger/checksums, existing Auth users
without reviewed provisioning, missing UUID prerequisite or upgrade collisions
fail closed. Actual final preflight verified fresh 0/0/0 without writes.

Bootstrap is separately opt-in and privately prompts distinct 32..128 printable
nonspace ASCII passwords. Only generated SCRAM verifiers (also sensitive) enter
SQL through binary stdin; raw diagnostics are captured/withheld. Logging settings
are reduced before password DDL. No password is embedded in tracked SQL or argv.
Existing roles are refused, not rotated. Separate bootstrap roles can remain after
a later failed schema transaction; that is not partial migration success.

Apply serializes with advisory transaction lock, rechecks ledger/state inside the
transaction, temporarily grants owner schema/DB creation and Auth USAGE/TRIGGER/
REFERENCES(id), sets owner and controlled legacy search_path, executes reviewed
001/003/004/005, creates/checks ledger, revokes temporary Auth/create powers, and
asserts before COMMIT. Assertions check role/membership boundary, every reviewed
column grant and forbidden operation, object/RLS/ledger ownership, exact policy
role/command identities, private helper security/search_path/EXECUTE, owner defaults,
client schema denial and installed signup trigger. They are source-prepared,
**not tested in PostgreSQL yet**. Policy-expression/function-body semantic testing
still depends on the later live/rehearsal gates, not merely ledger equality.

Settings require an explicit limited-role URI, reject administrative usernames,
missing password, malformed/unsupported schemes and override query settings;
only one reviewed sslmode value is permitted. SecretStr hides normal representation,
and validation errors hide inputs. Actual connection uses five-second connect and
30-second command timeouts. Pool initialization/cleanup and worker errors suppress
raw driver context. The HTTP failure boundary prevents pre-response ASGI rethrows;
it is not a certification of arbitrary future streaming/background handlers.

Compose maps two private inputs to respective DATABASE_URL and no longer injects
one root env file with both passwords into both services. Separate optional ignored
env files retain nonsecret Auth/execution configuration. Container issuer remains
exactly `http://127.0.0.1:54321/auth/v1`; JWKS/PG transport hostnames differ.
Passwords necessarily exist in runtime process memory/environment: do not publish
Compose config/process inspection or log Settings/driver raw objects. The empty
example is deliberately non-runnable until private provisioning. Host-run processes
also require separate DATABASE_URL values; old postgres fallback deployments break
closed and must be explicitly configured.

## Actual commands and results

All commands from repository root. `$D` below is the existing executable:
`C:\Users\tsush\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe`.
`$A=vq-db-permission-api-20261001`, `$W=vq-db-permission-worker-20261001`.

All image test/import containers used --rm, unique vq-db-permission-* names,
--network none, --read-only, --cap-drop ALL, --security-opt no-new-privileges:true,
memory 128..384m/PIDs 32..64; main tests also used /tmp rw,noexec,nosuid,16m.
No secret env file, host port, Docker socket, application DB or queue was supplied.
Only deliberately unused unit-only dummy DSNs and individual test mounts appeared
in command arguments. Image dependency installation was confined to normal declared
Docker build steps; no host/global dependency installation occurred.

| Executed command/check | Exit and observed result |
| --- | --- |
| Git HEAD/branch/status/origin and complete tracked diff review; source/report reads | 0; main at baseline, expected origin, no staged files |
| `$D build --quiet -t $A backend`; `$D build --quiet -f worker/Dockerfile -t $W .` | 0 each; actual API/worker built; rebuilt after HTTP boundary tests |
| Final API image | sha256:87d7321249fc3d2f06c4ccdf7901e12616dd9c3e335ae57bbe8fb6ed502b738f |
| Final worker image | sha256:4a04129afa8ec74f2f5c46fe9960259e2aaeb915bfb3a56863d69a7720fce9a6 |
| `$D run <isolation> $A python -B -m pytest tests -p no:cacheprovider` | 0: initial 50 passed; final **52 passed**, 1.14s; 17 DB-authority/config cases + 35 retained backend cases |
| `$D run <isolation> --mount <test_worker_dispatch.py read-only at /probe_tests/test_worker_dispatch.py> $W python -B /probe_tests/test_worker_dispatch.py` | 0: **7 methods**, final 0.045s |
| `.venv/Scripts/python.exe -B tests/test_database_gate.py` | Initial 1, runner syntax error; corrected before SQL access. Final **0: 10 methods**, 0.073s |
| `.venv/Scripts/python.exe -B -m unittest discover -s tests -p test_auth_compatibility.py -v` | 0: **17 methods**, 0.292s |
| `$D run <isolation> -e PYTHONPATH=/app --mount <test_auth_compatibility.py read-only in /probe_tests> $A python -B -m unittest discover -s /probe_tests -p test_auth_compatibility.py -v` | Final 0: **17 methods**, 0.270s |
| `.venv/Scripts/python.exe -B tests/test_verdict_integrity.py` | 0: **9 methods**, 0.277s; mocked Docker transport/real parser, not native simulator proof |
| `node tests/status_contract_consistency.test.mjs` | 0: **6/6 static checks** |
| `tools/database_gate.py --docker $D --mode plan` | 0: sequence 001/003/004/005, deferred 002, writes false |
| `tools/database_gate.py --docker $D --mode preflight` via project venv | 0 before and after final changes: fresh, roles/tables/Auth users each 0, writes false |
| `tests/database_permission_live.py` without opt-in; `tools/database_rehearsal.py --docker $D` without opt-in | Windows command wrapper observed nonzero 1; production main returns 2, asserted by unit test; no subprocess/write invoked |
| Final actual API import/OpenAPI/disconnected pool probe, python -B -c | 0: API route registered, no worker/socket/env files; real unavailable connection raises sanitized RuntimeError with suppressed context |
| Final missing DATABASE_URL import probe, python -B -c | 0: expected production ValidationError detected; no fallback or DB attempt |
| Final worker import/registration/config/exclusion probe, python -B -c | 0: both canonical tasks registered; vq_worker config accepted; no socket/backend tests/env/venv |
| `python -B -m pip check` in both final images | 0 each: no broken requirements |
| Compose --env-file .env.example config --format json, captured privately with distinct dummy input URIs | 0: correct per-service mapping, no opposite SQL input injected; no service started |
| Existing PG image network-none tool probe: command -v initdb/pg_ctl/psql; psql --version | 0: all present, PostgreSQL 17.11; **no initdb/server/SQL execution** |
| In-memory AST parse | 0: **52 backend/worker/tool/focused-test Python files**; final new-tool/harness parse also passed |
| Complete pending-file credential/generated-path scan | 0: 42 files before report; final scan 43 including report, zero PEM/GitHub/AWS/JWT-literal candidates and no unintended dependency/cache/secret paths; values never printed; not exhaustive secret certification |
| SHA256 preservation | 0: 26 earlier pending/report files not intentionally edited unchanged; 17 checks across existing reports/historical migrations unchanged (one duplicate historical check) |
| git diff --check | 0; LF/CRLF warnings only |
| `$D image rm $A $W` | 0: both final temporary tags/images removed |
| Removal attempt for two superseded initial-build IDs | 1: both already absent; no force/prune used, no outstanding resource inferred |
| `$D ps -a --filter name=vq-db-permission`; existing project ps | 0: no probe containers; ten existing Supabase containers remain running |

Resolved image dependencies: Python 3.12.14; API FastAPI 0.142.2, asyncpg 0.31.0,
pydantic-settings 2.15.0, python-jose 3.5.0, cryptography 50.0.2; worker Celery
5.6.3/asyncpg 0.31.0/settings 2.15.0. pytest 9.1.1/asyncio plugin 1.4.0.
Existing Starlette TestClient/HTTPX and leaderboard regex deprecation warnings
remain; requirements are still lower-bounded, not locked.

## Coverage, prepared live checks and limitations

New authority tests call actual signed-token verifier/auth dependencies/admin HTTP
handlers with controlled JWKS/DB. The same valid signed role=admin token receives
403 without a grant, 200 with a grant, 403 after revocation and 503 on DB outage.
They also call production Settings/URI validator/pool role verifier/session cleanup/
profile handler and HTTP failure boundary. Mocks do not prove PostgreSQL RLS or
transaction rollback. Production runner generators are called, not a copied test
implementation; pytest/unittest assertions fail nonzero.

Live harness is opt-in and checks current reviewed source hashes inside the actual
API image before writes. It uses real Auth A/B/C sign-in, actual PostgREST and full
production API lifespan over container-loopback TCP HTTP, actual restricted SQL
logins, no dependency overrides/socket, an operator-provisioned C grant, unchanged
values after denials and explicit cleanup. Protected/mixed/profile identity, other-
user records, catalog links, hidden data, roles/progress/result mutation, real API
submission ownership, unavailable-broker failure, runtime SELECT/upserts/RETURNING/
locks/award/streak/quest/badge/audit writes and migration ledger checks are prepared.
Worker award/publication/validation transitions are rollback/permission fixtures,
**not actual grader validation or accounting correctness**. Supabase-admin TCP uses
the local password only as a candidate and verifies actual privileged identity
before creating resources; failure stops, not a postgres/runtime fallback.

The isolated rehearsal has no network/ports/persistent database; uses minimal Auth
stubs and production SQL generation to test rollback before commit, apply/replay and
checksum mismatch. Only executable availability/opt-in refusal was executed here.
Real Supabase Auth event triggers, actual RLS/upsert/trigger privileges, SQL syntax,
runtime logins, schema-cache timing and the write-capable harnesses remain unverified.
These are authorization-gated, not missing Python/Docker prerequisites. Host venv
lacks asyncpg/pytest/Celery; real declared image dependencies executed backend tests.
No mocked success substitutes for the blocked live gate.

Source review corrections made before handoff: literal reserved prefix; temporary
FK REFERENCES(id) for owner installation; separate Compose env files; rejection of
unknown namespace state; helper security-mode/default/schema assertions; and HTTP
failure boundary preventing raw ASGI error rethrows. No privileged write probe was
used to discover or claim these fixes.

Remaining release gates: accounting/quest duplicate rewards and badge JSON codec;
submission atomicity/idempotency/outbox/crash recovery; Docker workspace/UID/mount
execution; revision-bound validation/publication. PUBLIC TEMP and unrelated platform
function privileges are not globally rewritten. TLS/host-port LAN containment,
GraphQL, hosted/deployed permission behavior and future streaming/background logging
need their own checks. A compromised service can still exercise its deliberate
all-user service capabilities; ACLs do not prove safe algorithms or arbitrary SQL.

## Exact next task and recovery

**Next nonmutating command:** from repository root,

```powershell
.venv/Scripts/python.exe -B tools/database_gate.py --docker 'C:\Users\tsush\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe' --mode preflight
```

Next authorized engineering gate: review this diff/manifest, authorize recoverable
local snapshot and isolated rehearsal first; run the command in DATABASE_PERMISSION_GATE.md.
Only after rehearsal passes, separately authorize bootstrap/apply against the exact
disposable project and three real test identities/fixture writes; rebuild the current
API image and run database_permission_live.py with both explicit live flags.
Stop on every failure. Do not reset, fabricate tracking, auto-backfill, rotate roles
or run fixture 002. Failed schema transaction leaves no permissive committed schema;
bootstrap roles may remain. Interrupted live cleanup requires private exact-ID/FK
recovery review, not broad deletion by prefix. Existing Supabase must remain running.

## Final Git state and scope

Everything remains unstaged, uncommitted and unpushed. Final tracked diff against
HEAD: **19 files, 297 insertions, 257 deletions**; includes earlier dispatch changes,
not this milestone alone. **24 individual untracked files** including this report.
No generated dependency/cache/local-secret files are intended changes.

Tracked unstaged files:

```text
.env.example
backend/app/admin/router.py
backend/app/core/config.py
backend/app/core/rate_limit.py
backend/app/db/session.py
backend/app/main.py
backend/app/profile/router.py
backend/app/submissions/router.py
backend/app/submissions/service.py
backend/tests/conftest.py
backend/tests/test_schemas.py
backend/tests/test_security.py
docker-compose.yml
tests/auth_live_runtime/service.py
tests/test_auth_compatibility.py
tests/test_verdict_integrity.py
worker/celeryconfig.py
worker/execution/sandbox.py
worker/tasks/hdl_task.py
```

Untracked files, including preserved prior milestone work:

```text
.dockerignore
backend/.dockerignore
backend/app/core/database_config.py
backend/app/core/task_contract.py
backend/app/core/task_publisher.py
backend/app/db/runtime.py
backend/tests/test_database_authority.py
backend/tests/test_dispatch.py
docs/BACKEND_TASK_PUBLICATION.md
docs/DATABASE_PERMISSION_GATE.md
docs/handoff/BACKEND_STARTUP_DISPATCH_ASSESSMENT.md
docs/handoff/BACKEND_STARTUP_DISPATCH_REMEDIATION_REPORT.md
docs/handoff/DATABASE_PERMISSION_GATE_ASSESSMENT.md
docs/handoff/DATABASE_PERMISSION_REMEDIATION_REPORT.md
supabase/migrations/004_permission_gate.sql
supabase/migrations/005_profile_identity_gate.sql
tests/database_permission_live.py
tests/test_database_gate.py
tests/test_worker_dispatch.py
tools/database_gate.py
tools/database_migrations.json
tools/database_policy.json
tools/database_rehearsal.py
worker/execution/profile.py
```

Earlier dispatch/rate-limit/sandbox/profile-parsing modifications are preserved;
the new current-role/pool changes compose with them. No XP algorithm, worker
workspace architecture, scoring protocol or revision authoring implementation changed.
Historical reports retain their original findings/evidence limits rather than being
rewritten to claim this unexecuted database gate passed.
