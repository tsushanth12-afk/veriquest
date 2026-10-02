# Isolated PostgreSQL database-hardening rehearsal

Saved 2026-10-01, 18:27 IST. Scope: the explicitly authorized isolated rehearsal,
not application to veriquest-local-test. **Isolated rehearsal passed after two
native migration corrections. The real Supabase database gate remains blocked.**

## Repository/environment recheck and preservation

Repository: C:\Users\tsush\Desktop\veriquest. Branch main; HEAD and read-only
remote refs/heads/main both **7c7d1cd6062fcde09f06078830c1c490eb5b1675**.
Origin identity is github.com/tsushanth12-afk/veriquest.git; parsed URL contained
no embedded credentials. No applicable AGENTS.md was found in the repository
or checked ancestors. Checkpoint, runbook, runner, migrations, permission matrix,
tests, current API/admin/worker/accounting SQL and remediation context were reviewed.

Initial Git state: no staged files, 19 tracked modifications, 25 untracked files.
Existing pending dispatch/database preparation and handoff reports were preserved.
Before/after SHA256 checks covered 57 distinct files (64 path entries, including
duplicates). Only the six existing files intentionally changed below differed.
Historical 001/002/003, PAUSE_CHECKPOINT.md and all prior handoff reports remained
byte-for-byte unchanged. This report does not rewrite their historical evidence.

Current Docker context: desktop-linux; Linux engine 29.8.0. Host project venv:
Python 3.12.14. Existing image declares no Config.Volumes and provides PG17.11.
The disposable folder and supabase/config.toml exist, but Docker ps -a returned
**zero containers before this task's rehearsal and zero after cleanup**.
Local Auth health did not respond successfully. This differs from the saved
checkpoint's ten running Supabase containers; no cause is established here.

The production runner preflight was executed before and after the rehearsal,
both exit **1**: "Disposable target verification failed; no fallback allowed."
It failed in verify_target, before database SQL. Therefore current database
contents/counts/permissions cannot be confirmed. No credentials were acquired,
no alternate database was selected, and Supabase was not started/recreated.
Existing services/configuration were not changed. The engine being healthy is
not evidence of an available production/test Supabase database.

## Isolation and native evidence

Final run container: **vq-db-rehearsal-da0e675e899b4291990e93609233f9ff**.
Already-present inspected image, pinned by immutable ID:
sha256:0450166354dc9c1d25f0322ac8b580774d4fb0184d2b087f6e4fe9499c66cf53.
No image was pulled, built, removed or changed.

Docker inspect was consumed privately and emitted only a safe projection before
initdb and after all role tests. Both inspections asserted:

- NetworkMode none; only the none network; no IPv4/IPv6 address.
- No PortBindings and no published port entries.
- Read-only root; user postgres; CapDrop ALL; no-new-privileges:true.
- Memory 268435456 bytes; PIDs limit 64.
- Image-declared volumes absent; Mounts []; /tmp is explicitly tmpfs
  rw,noexec,nosuid,size=160m,mode=1777. No bind, Docker socket or persistent volume.
- All PG data/socket/log files are under this temporary /tmp; initdb creates a
  new cluster, not the image's Supabase data directory.
- SHOW listen_addresses returned empty; only /tmp Unix-socket transport is used.

These are **executed Docker inspection/SQL checks**, not conclusions drawn just
from run arguments. The rehearsal never calls production verify_target/psql,
uses no DSN, API key, host database address, published port or existing volume.
Its PostgreSQL connections are docker exec psql -h /tmp -d postgres to this
exact uniquely named container. Network isolation prevents external DB access.

Platform stubs: auth.users with id/email/raw_user_meta_data, controlled auth.uid()
reading a test subject GUC, anon/authenticated/service_role, empty vault and
extensions schema with uuid-ossp. A synthetic supabase_admin owns the Auth table.
Observed broad creator defaults are modeled for supabase_admin. These do **not**
recreate Supabase Auth constraints, identities, GoTrue, event triggers, defaults
of every platform principal, PostgREST or GraphQL.

Actual API/worker sessions connect with -U vq_api / -U vq_worker. Both
session_user and current_user were asserted, without operator SET ROLE.
Client proxy LOGIN roles inherit only authenticated or anon; controlled subject
claims represent students A/B. They are real restricted SQL identities, not
verified Auth users. The cluster's isolated socket uses trust authentication;
generated bootstrap passwords/SCRAM verifiers stay private in memory/stdin.
**SQL authorization is verified here; SCRAM/TCP login is not.**

## Actual commands and outcomes

All host commands ran at the repository root. PowerShell executable variable:

```powershell
$D = 'C:\Users\tsush\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe'
```

| Command / executed check | Exit / observed outcome |
| --- | --- |
| git branch --show-current; git rev-parse HEAD; git status --short --untracked-files=all | 0 individually; baseline/current lists below |
| git remote get-url origin, captured and parsed privately | 0; expected public repository, no credential values output |
| git ls-remote origin refs/heads/main | 0; remote matches local HEAD |
| rg --files -g AGENTS.md excluding dependencies; checked ancestor paths | rg 1, no matches; no applicable instruction file found |
| $D context show; $D version --format '{{.Server.Os}} {{.Server.Version}}' | 0; desktop-linux, linux 29.8.0 |
| $D image inspect public.ecr.aws/supabase/postgres:17.11.0.002 --format '{{json .Config.Volumes}}' | 0; null |
| $D ps -a --format '{{.ID}} {{.Names}} {{.Status}}' | 0; no containers before/after, except task containers during their runs |
| .venv/Scripts/python.exe -B --version | 0; Python 3.12.14 |
| .venv/Scripts/python.exe -B tools/database_gate.py --docker $D --mode preflight | 1 before, 1 after; verified-target gate failed, no SQL/fallback |
| Invoke-WebRequest http://127.0.0.1:54321/auth/v1/health -TimeoutSec 3 | No successful HTTP response; caught failure, diagnostics withheld |
| .venv/Scripts/python.exe -B tools/database_rehearsal.py --docker $D --authorize-isolated-rehearsal | Seven actual executions, recorded separately below |
| .venv/Scripts/python.exe -B tests/test_database_gate.py | Initial retained 10 methods passed; after additions 14 passed, final 0.053s, exit 0 |
| node tests/status_contract_consistency.test.mjs | Exit 0, 6/6 static checks, not permission/integration proof |
| In-memory ast.parse of runner/gate/new operations/test_gate and load_plan | Exit 0; four source files and updated pinned manifest valid; 002 deferred |
| git diff --check | Exit 0; existing LF/CRLF warnings only |
| SHA256 before/after comparison | 57 distinct files; six intended existing files changed, all other baseline files unchanged |
| Limited credential-pattern scan of seven task files | Exit 0; no PEM-private-key/GitHub/AWS/JWT-literal candidates; not exhaustive credential certification |
| $D rm -f exact-task-container; $D inspect exact-task-container | Remove 0; inspect 1 with explicit No such object/container for each task resource; final independent check below |

Runner subprocess command templates actually executed:

```text
docker image inspect public.ecr.aws/supabase/postgres:17.11.0.002
docker run -d --pull never --name <unique-vq-db-rehearsal-name>
  --network none --read-only --cap-drop=ALL
  --security-opt=no-new-privileges:true --memory=256m --pids-limit=64
  --user postgres --tmpfs /tmp:rw,noexec,nosuid,size=160m,mode=1777
  --entrypoint sleep <inspected-image-sha256> infinity
docker inspect <exact-task-name>
docker exec -u postgres <exact-task-name> sh -c
  'initdb -D /tmp/rehearsal --auth-local=trust --auth-host=reject >/dev/null &&
   pg_ctl -D /tmp/rehearsal -o "-k /tmp -c listen_addresses= -c unix_socket_directories=/tmp"
   -l /tmp/server.log -w start >/dev/null'
docker exec -i -u postgres <exact-task-name> psql -h /tmp -X -q -A -t
  -v ON_ERROR_STOP=1 -v VERBOSITY=verbose -U <tested-role> -d postgres
docker rm -f <exact-task-name>
docker inspect <exact-task-name>
```

All SQL, including generated credential verifiers, used captured binary stdin,
not command arguments/files. No bootstrap credential or SQL result containing
private evaluator fixture content was printed. Runner JSON records fixed case
labels, role, actual exit code and SQLSTATE, not row contents or raw secrets.

### Failed attempts, corrections and reruns

Every attempt used a separate container and removed it; no failed state was reused.

| Attempt / container suffix | Exit | Actual outcome |
| --- | --- | --- |
| 1 / c46b4a7a17ba444e9a9ea043f4a2af56 | 1 | Native 42601, progress CASE syntax error before intended failure point. Removal 0; first cleanup checker falsely reported absent=false due diagnostic case; later direct inspection proves absent |
| 2 / 873fe149f070420f9865b2fd65386c9d | 1 | Same 42601, private diagnostics localized; corrected case-insensitive absence check passes |
| 3 / 179edc8f1aa84f73b0da4ceb2e57dac2 | 1 | Same failure localized to guard_api_progress CASE; no rollback success counted |
| 4 / e5303a73e16e4e7e892c9826c58ae47c | 1 | After CASE fix, native 42501: must be owner of relation users when replacing Auth trigger |
| 5 / c3ae65466c4c4a59a9b3aca5685c731a | 1 | After Auth attachment fix, native rollback/apply/replay/checksum gates passed; stopped at operation-harness loading (file not yet added), withheld non-SQL exception; no role-operation coverage counted |
| 6 / 8c7fd7cdc0f14a0cb7a87779b362eb8f | 0 | First complete suite: 254 assertions / 251 SQL cases, cleanup and isolation passed |
| 7 / da0e675e899b4291990e93609233f9ff | 0 | Final expanded suite: **276 assertions / 273 SQL invocations**, zero failed assertions, cleanup and isolation passed |

Counts include setup, before/after digests and repeated statements. They are
**not 273 independent business tests**; prior runs are not added to final coverage.
Final SQL invocation distribution: postgres 1, supabase_admin 138, vq_api 34,
vq_worker 42, student-A proxy 43, student-B proxy 3, anon proxy 12.
72 intentionally unsuccessful SQL invocations were correctly asserted:
63 SQLSTATE 42501, 3 bounds failures 23514, 6 P0001
(two transaction gates and four guarded API writes). Those expected psql exits
were 3, not unexpected suite failures. Successful SQL invocations exited 0.
47 rejected writes additionally compared privileged before/after state digests.

## Native assertions beyond catalog inspection

Production apply_sql includes **2680 column-privilege conditions**, 280 forbidden
table-privilege conditions, 14 table ownership/RLS checks and 59 exact policy
command/role identities, plus helper/default/owner/role/trigger/ledger checks.
These are internal conditions, not additional independent test counts.
They executed successfully before the intentional rollback point, fresh commit
and both tracked replay operations. Policy-expression semantics are exercised
by representative native operations below, not exhaustively certified by metadata.

| Native exercise | Actual asserted outcome |
| --- | --- |
| bootstrap_sql + apply_sql with rehearsal_failure=True | Must reach exact P0001 / Intentional isolated rehearsal rollback after full assertions; 42601/42501 earlier failures do not qualify |
| New connection after injected failure | Zero application tables; private schema/profile/ledger absent; Auth trigger absent; temporary owner Auth/TRIGGER/REFERENCES/create rights absent |
| Fresh actual 001 -> 003 -> 004 -> 005 application | One transaction commits, four exact migration ledger rows; seed 002 never executed/recorded |
| Identical tracked reapplication | No-op: schema OIDs/definitions/functions/triggers/policies/column ACLs/defaults and all application/ledger rows retain digest |
| Changed expected 001 checksum against installed ledger | Exact P0001 / Partial or changed ledger; original schema/ledger/data digest unchanged |
| Replay after five stub identities and permission fixtures | Same no-op assertions pass with populated tables; no identity/stat overwrite |
| Stub Auth INSERT trigger | UUID-derived distinct usernames despite colliding requested usernames; metadata role/xp ignored; five zero-score level-1 profiles + literal student roles |
| Stub display metadata | Trimmed string, malformed display with full_name fallback, non-object default Student, truncation to 100 |
| Signup helper reexecution via temporary stub UPDATE trigger | Existing scored profile and operator admin grant unchanged; temporary replay trigger removed |
| Client own SELECT and safe UPDATE RETURNING | Own profile only; safe display/bio/avatar edit works; real updated_at trigger advances timestamp |
| Other-user profile UPDATE RETURNING | Returns zero rows; other profile display state unchanged |
| Mixed client writes | Safe bio plus each protected XP/level/streak/solved/attempt/username/id write denied; full profile digest unchanged |
| Display/bio/avatar bounds | 101/2001/2049 lengths rejected, digest unchanged |
| Client profile ON CONFLICT / role promotion | Denied without mutation |
| Catalog / prerequisite / quest link RLS | Only two nonarchived published challenges, one visible prerequisite pair, two visible quest links; draft/archive relationships hidden |
| Private evaluator and badge rule reads | Client/anon denied; worker reads only granted evaluator columns, not notes |
| Production API create_submission SQL | Queued input INSERT and idempotency SELECT work; initial and conflicting progress upsert increment attempts to 2 |
| API guarded protected upserts | Completed INSERT/upsert or forged completion UPDATE fails P0001; progress state unchanged |
| API forged accepted results | INSERT/UPDATE denied by RLS; mixed result-count/XP mutation denied by ACL; state unchanged |
| API profile XP/ledger/roles | Forbidden changes fail; protected state unchanged |
| Production worker input JOIN/stage/evaluator/result SQL | Actual SELECT, compiling/running/result writes succeed under vq_worker; input mutation/evaluator edit/publication denied |
| Production award_xp SQL | DO NOTHING upsert, SELECT status FOR UPDATE inside BEGIN/ROLLBACK, ledger insert/aggregate and completion evidence writes succeed |
| Worker profile expression update | Representative dynamic difficulty-column shape succeeds; accounting algorithm itself not executed |
| Production API retry after completed progress | Attempts increments to 3; status/completed_at/best_submission_id remain authoritative |
| Worker wrong-answer attempt SQL | Actual insert/conflict update both succeed; attempts=2; production profile-attempt update succeeds |
| Production streak/quest/badge SQL | Streak conflicting upsert reaches count 2; GREATEST profile write works; quest SELECT/ledger INSERT and badge SELECT/conflict DO NOTHING work; one badge award row |
| Client history/XP/progress/streak/badge/role SELECT | Own rows only; student B cannot read A's XP; submitted_code column unavailable |
| Client pregraded submissions/XP/completion/award/streak | Actual forbidden statements and award upsert rejected; corresponding state digests unchanged |
| record_publication_failure production SQL | Unclaimed queued B job becomes system_error/DISPATCH_FAILED; same query cannot overwrite finalized A result |
| create_challenge production SQL | Draft INSERT RETURNING real DB-generated ID; subsequent private/audit writes use that returned ID |
| Admin/worker validation SQL | API claim RETURNING id, worker pending->validated RETURNING, worker audit append, API validated publication succeed |
| Forged admin validation/publication | Protected mixed title+state updates fail P0001 and leave challenge digest unchanged |
| Secret invalidation trigger | API private bench edit actually invokes owner helper, resets published challenge to unpublished draft |
| Worker validation on draft | Zero-row RETURNING, challenge state unchanged |
| Worker validation failure | Pending->validation_failed RETURNING works, validated_at becomes null |
| Runtime/client ledger/function/owner/TRUNCATE/DELETE | Denied as real roles, with unchanged-state assertions for mutation attempts |
| Runtime public DDL/Auth reads/role creation | Denied; no forbidden object/role exists |

Static production queries are extracted with AST by
[production_query/prepared](C:/Users/tsush/Desktop/veriquest/tests/database_rehearsal_operations.py),
not replaced with permissive mock SQL. Query parameters use PREPARE/EXECUTE
against native PostgreSQL. This exercises statement permissions, not asyncpg
serialization, Python transaction orchestration, HTTP handlers or live dispatch.

Source functions exercised include create_submission/record_publication_failure
in [submission service](C:/Users/tsush/Desktop/veriquest/backend/app/submissions/service.py),
create_challenge/validate_challenge/publish_challenge in
[admin router](C:/Users/tsush/Desktop/veriquest/backend/app/admin/router.py),
_execute_hdl_submission/_validate_challenge in
[worker task](C:/Users/tsush/Desktop/veriquest/worker/tasks/hdl_task.py),
and award_xp/update_streak/check_quest_completion/check_badge_awards SQL in
[gamification](C:/Users/tsush/Desktop/veriquest/backend/app/gamification/xp.py).

## Corrections and current-task changed files

The backend-security-coder skill guided real-role denial and unchanged-state
checks, fail-closed error assertions and secret-safe evidence. It did not authorize
changes to the existing Supabase database.

| Changed/new file | Small scoped correction |
| --- | --- |
| [004_permission_gate.sql](C:/Users/tsush/Desktop/veriquest/supabase/migrations/004_permission_gate.sql), private.guard_api_progress | Parenthesized CASE in IS DISTINCT FROM; actual PG42601 reproduced then eliminated; no grant broadening |
| [005_profile_identity_gate.sql](C:/Users/tsush/Desktop/veriquest/supabase/migrations/005_profile_identity_gate.sql), Auth attachment | RESET ROLE to trusted supabase_admin only for DROP/CREATE Auth trigger, assert both session/current operator, restore LOCAL vq_owner; no Auth ownership transfer/runtime escalation |
| [database_migrations.json](C:/Users/tsush/Desktop/veriquest/tools/database_migrations.json) | Re-pinned only corrected 004/005 canonical-LF hashes |
| [database_rehearsal.py](C:/Users/tsush/Desktop/veriquest/tools/database_rehearsal.py), main/SQLProbe/isolation_evidence/state_snapshot_sql | Actual inspect isolation, refuse persistent image volumes, pin local image ID, exact error reasons, actual-role sessions, unchanged-state/replay assertions and verified cleanup |
| [database_rehearsal_operations.py](C:/Users/tsush/Desktop/veriquest/tests/database_rehearsal_operations.py), new run_operations/production_query/prepared | Native operation fixtures and production-source SQL extraction; never used against existing Supabase |
| [test_database_gate.py](C:/Users/tsush/Desktop/veriquest/tests/test_database_gate.py) | Four additional production-runner/isolation/transport/failure-boundary tests; 14 methods total |
| [DATABASE_PERMISSION_GATE.md](C:/Users/tsush/Desktop/veriquest/docs/DATABASE_PERMISSION_GATE.md) | Clarifies isolated authorization vs later snapshot/application; executable coverage/role/socket limitation/trigger operator correction |
| This new report | Actual evidence and unresolved gates |

Production database_gate.py and permission matrix are unchanged. All application
Python source, runtime settings, Docker/Compose packaging, historical migrations
and earlier handoff reports are unchanged by this task. No XP algorithm, job
atomicity, grader protocol or UI behavior was altered.

Final pinned hashes:

```text
001 3360912fc8398b7cb49f1354085e3aa659281e01111ea691aa61c08408a363b3
003 fb3744453ddef0bea586a91b664a5cac39ca942f51aba6ed8feb0d3c9f95a2f4
004 416a96975a680b6be2909496cc2acae4ed711926cb7e4e21dc376055347d38bd
005 998ec791149fbba706f85161b398db298b5fcf44e93f265fe75175413d780af6
```

Historical 002 remains unchanged and deferred, not an executed validation fixture.

## Cleanup and limitations carried forward

All seven exact containers listed above were removed with rm -f. Independent
final Docker inspect for every name returned 1 and explicit absence, including
the first run's cleanup-checker false negative. Final cleanup check exited 0.
Final run remove_exit=0, inspect_exit=1, exact_container_absent=true.
No task container, network, persistent volume, service or image remains from the
rehearsal. No host test service or background worker was started. No existing
Supabase resource was stopped or deleted; none was present in this engine at
the initial inspection. Do not describe this as leaving a verified running
Supabase stack: its availability is currently unresolved.

**Remaining untested requirements / gates:**

1. Restore/check the intended existing local Supabase environment under separate
   authorization; current verify_target and Auth health cannot pass. Its actual
   current schema, Auth users, platform grants/defaults, event triggers and exposed
   API schemas have not been freshly queried.
2. Recoverable snapshot and actual local bootstrap/application remain unexecuted.
   Real supabase_admin transport/ownership, platform default ACL interactions and
   Auth event-trigger compatibility need the real reviewed gate. Do not apply
   based only on this stub rehearsal, reset, fabricate tracking or run seed 002.
3. Real Supabase signup/sign-in/identity constraints, GoTrue-trigger execution,
   metadata edge cases not exercised above, username/identity behavior with real
   Auth, account deletion/FKs and preexisting-user backfill/collisions remain live
   requirements. This runner intentionally refuses untracked/existing-user upgrade.
4. Real PostgREST A/B/admin calls, schema-cache reload timing, profile edit/upsert/
   returning semantics, protected/mixed write errors, ownership boundaries, private
   schema/RPC access and actual DB-admin grant/revocation must run in the prepared
   live harness with separately authorized disposable identities. Client proxy
   SQL/GUC claims are not evidence of verified JWT authority or PostgREST behavior.
5. Real vq_api/vq_worker SCRAM/TCP logins, network reachability, strict pool identity
   verification and full backend lifespan/actual asyncpg calls remain untested.
   HTTP submission/admin authorization and admin revocation were not rerun here;
   prior unit/auth evidence retains its earlier limits.
6. Native FOR UPDATE was successfully executed, but competing-lock contention,
   simultaneous submissions/awards, deadlock behavior, accounting reconciliation,
   quest duplicate rewards, badge JSON codecs and crash/idempotency recovery were
   not exercised. Dynamic profile SQL is a representative shape, not a complete
   production Python award algorithm run.
7. No Redis/Celery successful publication or real queued HDL job, native sandbox
   workspace/UID/mount execution, or revision-bound validation/publication safety
   is established. Fixture accepted/validated/published values are permission
   fixtures, not simulator verdict evidence.
8. Policy command/role/ACL checks and representative operation cases do not
   exhaust every expression, role assumption, platform function, optional schema,
   GraphQL/view/security-definer bypass surface, future migration or adversarial
   SQL combination. No deployed/hosted/LAN/TLS permission safety is claimed.
9. Rehearsal cleanup is verified; recovery/cleanup after forced harness interruption,
   operator process death or real database migration failure/backup restore remains
   a separate operational test. Separate bootstrap roles intentionally persist
   across the injected migration rollback inside the temporary cluster, then
   disappear with that cluster; no production roles were created.

The next step is **not an automatic migration**: resolve/verify the missing
disposable environment and arrange the separately approved snapshot, exact
bootstrap/application and real permission harness from the runbook. This task
stops here after the isolated rehearsal report. Production readiness is unresolved.

## Final Git state

No staging, commit, push, reset, deployment, Supabase account creation, seed002 or
existing-database write occurred. HEAD/branch unchanged. Tracked diff remains
19 files / 297 insertions / 257 deletions (earlier milestones).
Staged none; tracked unstaged 19; untracked 27 after this report.

Tracked unstaged:

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

Untracked, including preserved earlier work:

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
docs/handoff/DATABASE_ISOLATED_REHEARSAL_REPORT.md
docs/handoff/DATABASE_PERMISSION_GATE_ASSESSMENT.md
docs/handoff/DATABASE_PERMISSION_REMEDIATION_REPORT.md
docs/handoff/PAUSE_CHECKPOINT.md
supabase/migrations/004_permission_gate.sql
supabase/migrations/005_profile_identity_gate.sql
tests/database_permission_live.py
tests/database_rehearsal_operations.py
tests/test_database_gate.py
tests/test_worker_dispatch.py
tools/database_gate.py
tools/database_migrations.json
tools/database_policy.json
tools/database_rehearsal.py
worker/execution/profile.py
```
