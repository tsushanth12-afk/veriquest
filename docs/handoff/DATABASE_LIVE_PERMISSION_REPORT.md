# Live database permission gate — disposable local Supabase

Date: 2026-10-01 (Asia/Calcutta). Scope: the expressly authorized local database permission/identity gate, not queue delivery, native grading, accounting certification, or production readiness.

## Outcome

**The final real gate passed: 1,237 assertions, 92 recorded HTTP cases, exit 0.** Both students used actual public Supabase signup and password sign-in; the administrator was created through local Auth administration and granted administrator authority in the database. The actual current API image ran the production application, verifier, restricted database pool, limiter, publisher, and full lifespan without dependency overrides.

Migrations **001 → 003 → 004 → 005 are now committed in the disposable database**. Seed 002 remains deferred and absent from the ledger. The owner/API/worker roles and application schema are retained. All disposable accounts and application fixture rows are gone, independently verified by read-only counts. Existing Supabase remains running. Nothing was staged, committed, pushed, reset, or deployed.

There were failed attempts, recorded below. In particular, one expanded live run timed out and left fixtures; its exact fixtures were subsequently recovered and removed. A later identical gate passed. The timeout's root cause is unresolved; this report does not erase that failure or certify interruption-safe cleanup.

## Target and immediate pre-write checks

Repository: C:\Users\tsush\Desktop\veriquest. Branch: main. HEAD before and after: **7c7d1cd6062fcde09f06078830c1c490eb5b1675**. The previously verified repository is tsushanth12-afk/veriquest; no remote writes were performed.

Before snapshot and again immediately before bootstrap, the unchanged production runner returned exit 0 with:

```json
{"mode":"preflight","state":"fresh","role_count":0,"application_table_count":0,"auth_user_count":0,"writes":false}
```

The manifest and canonical-LF migration/policy hashes passed `load_plan()`. Target verification and final Docker inspection established:

- Exact project label: veriquest-local-test; exact workdir label: C:\Users\tsush\Desktop\veriquest-local-test.
- Named DB, REST, Kong, and Auth containers all running with those labels.
- DB: supabase_db_veriquest-local-test, host port 54322 → container 5432.
- API gateway: supabase_kong_veriquest-local-test, host port 54321 → container 8000.
- REST 3000 and Auth 9999 have no direct host port mappings.
- Exposed PostgREST schemas: public and graphql_public, not private.
- Local Auth health 200 and JWKS 200; one key with alg ES256, kty EC, crv P-256, use sig, key_ops [verify]. No key IDs, account identities, or key material are included here.
- Expected issuer remained exactly http://127.0.0.1:54321/auth/v1; container JWKS transport used http://host.docker.internal:54321/auth/v1/.well-known/jwks.json.

Only the verified local target was used. The driver pins the snapshot's actual container ID, image ID, and manifest before bootstrap/live phases. No hosted fallback exists.

## Private recovery and credentials

New opt-in driver: [tools/database_live_gate.py](C:/Users/tsush/Desktop/veriquest/tools/database_live_gate.py).

Recovery directory, outside Git and both build contexts:

```text
C:\Users\tsush\AppData\Local\VeriQuest\recovery\live-ee7fe07f5535490f89728348b707c83d
```

Retained files:

- snapshot.dpapi: Windows CurrentUser DPAPI-encrypted custom-format pg_dump plus global-role SQL, target/image identity, manifest, and initial state.
- runtime-credentials.dpapi: separately generated, distinct API and worker credentials, encrypted with CurrentUser DPAPI.
- timeout-fixture-recovery.dpapi: encrypted exact-resource inventory used to recover the failed live run. It contains private resource identifiers and must not be printed or committed.

The leaf directory has protected inheritance and exactly current-user/SYSTEM full-control DACL entries. Native Windows DACL inspection verified this, including again after testing. Artifact files inherit that restricted directory ACL. DPAPI decrypt/readability and credential distinction were rechecked without printing values.

Snapshot verification:

| Evidence | Actual result |
| --- | --- |
| PostgreSQL dump / restore tools | Both 17.11 |
| Custom-format dump bytes | 395,781 |
| Encrypted snapshot artifact bytes | 539,102 |
| Dump SHA256 | 97a3519d910e462478f1e676ba7234d15b2da9c1c02dc8e4b6174e55d04b3d92 |
| Archive header | PGDMP verified |
| pg_restore --list | Readable; 650 TOC entries |
| pg_restore --file=- | All archive blocks rendered/read privately without SQL execution |
| Saved encryption/decryption/hash roundtrip | Passed |
| Global role prerequisites | Captured privately |
| Actual restore rehearsal | **Not performed** |

A restore requires this Windows user's usable DPAPI profile, retained encrypted files, compatible PostgreSQL restore tooling, and a separately reviewed isolated restore procedure including role prerequisites. The archive is a database/role recovery artifact, not a backup of every Supabase service setting, secret store, or storage object. Do not reset or automatically restore the running project. Readable archive blocks are not proof that a full restore succeeds.

The owner remains NOLOGIN and therefore has no newly issued login password. API and worker receive distinct secure random credentials; their SCRAM provisioning uses the existing runner. Existing platform operator/API credentials were acquired privately from the exact verified local containers. Passwords, DSNs, tokens, and API keys never appeared in command arguments, tracked files, terminal reports, or Docker environment arguments. The test container received its capsule through captured binary stdin; its production API pool used vq_api, not the fixture operator. The harness necessarily held fixture-operator credentials in memory for authorized test setup/cleanup; it is not a model for production secret distribution.

## Application and migration tracking

The private driver invokes the **unchanged production runner main/CLI** with its documented modes and authorization flag, using a distinct captured stdin wrapper to satisfy Windows getpass without putting secrets in argv. It does not replace runner assertions or invent production-runner flags.

Actual runner outcomes:

1. bootstrap --authorize-local-write: exit 0, success; distinct vq_api/vq_worker LOGIN roles and vq_owner NOLOGIN role.
2. apply --authorize-local-write: exit 0; one transactional application in reviewed order.
3. preflight: exit 0, complete; 3 roles, 14 application tables, 0 Auth users.
4. Identical apply replay: exit 0, tracked asserted no-op; no seed or ledger duplication.

Ledger observed after testing:

| Version | Canonical SHA256 |
| --- | --- |
| 001 | 3360912fc8398b7cb49f1354085e3aa659281e01111ea691aa61c08408a363b3 |
| 003 | fb3744453ddef0bea586a91b664a5cac39ca942f51aba6ed8feb0d3c9f95a2f4 |
| 004 | 416a96975a680b6be2909496cc2acae4ed711926cb7e4e21dc376055347d38bd |
| 005 | 998ec791149fbba706f85161b398db298b5fcf44e93f265fe75175413d780af6 |

Policy SHA256: 6e165e69753f9832104777ea280f25488188b72cf1ef6b1cda33cbfdce9b1e35.

Production structural assertions ran before COMMIT and again in a final READ ONLY transaction: role flags/memberships, owner object identity, ACL/RLS policy identities, every allowed/forbidden column privilege, denied table capabilities, defaults, private helper ownership/EXECUTE/search_path configuration, ledger, and actual Auth trigger. This includes 2,680 column comparisons and 59 policy identities; these catalog comparisons are distinguished from executed SQL below.

Separate inspection confirmed temporary owner Auth USAGE, Auth TRIGGER, REFERENCES(auth.users.id), database CREATE, and public CREATE privileges all removed. Application ownership remains vq_owner; Auth table ownership was not transferred. Owner membership is retained only for the reviewed platform migration operator.

No SQL file or applied checksum was changed during this live task. Historical migrations and reports were preserved byte-for-byte. Future migration defects require reviewed forward corrections, never editing the committed versions or ledger.

## Real HTTP and SQL evidence

Final harness: [tests/database_permission_live.py](C:/Users/tsush/Desktop/veriquest/tests/database_permission_live.py), `live_inside()` and `main()`.

### Recorded HTTP outcomes

The 92 recorded cases are grouped here; health checks, hidden-schema request, and cleanup administration calls are additional requests/assertions, not included in that case-array total.

| Surface / operation | Count | Actual status / asserted meaning |
| --- | ---: | --- |
| Auth public signup | 2 | 200; actual students |
| Auth administrator account creation | 1 | 200 |
| Auth password sign-in | 3 | 200 |
| API admin list, trusted DB administrator | 1 | 200 |
| API admin challenge creation | 3 | 201; real returned IDs retained |
| API admin list, student / revoked administrator | 2 | 403 |
| API admin detail, student | 2 | 403 |
| API staff create, edit, validate, publish, unpublish, audit-log access | 6 | 403 |
| PostgREST challenges / prerequisites / quest links, anonymous and all three identities | 12 | 200; only published nonarchived challenges and visible active links |
| PostgREST own profile read | 1 | 200; only own row |
| PostgREST safe own edit / other-user edit | 2 | 200; other-user result empty and unchanged |
| PostgREST protected single/mixed profile updates | 22 | 403, SQLSTATE 42501; unchanged profile fingerprint after each |
| PostgREST oversized display name | 1 | 400, SQLSTATE 23514; unchanged state |
| PostgREST other-user histories/progress/XP/badges/streaks/roles | 6 | 200 with empty result |
| PostgREST queued or forged pregraded submission inserts | 2 | 403, 42501 |
| PostgREST insert/update/delete progress, XP, roles, badges, streaks, audit | 18 | 403, 42501 |
| PostgREST submission result modification / deletion | 2 | 403, 42501 |
| API other-user submission poll | 1 | 404 |
| API own submission poll | 1 | 200 |
| API safe, mixed, protected-only profile payloads | 3 | 200; protected keys filtered, protected-only truthful no-op |
| API submit against unavailable real broker | 1 | 503; DISPATCH_FAILED |

Additional assertions included private Accept-Profile schema request **406**, full API health **200**, exact Auth deletion responses and subsequent **404** checks, and unchanged authoritative-row snapshots following denied writes.

The API's mixed profile behavior is intentionally different from PostgREST: production API filtering applies allowed bio only and reports updated_fields; direct mixed safe/protected SQL through PostgREST is rejected atomically. Neither route changes protected scoring or role authority.

Both public signups executed the installed real Auth trigger: full UUID-reserved usernames, zero XP/attempts/completions/streak, initial level 1, bounded 150-character display input truncated to 100, malformed display metadata becoming Student, and metadata requesting admin/XP ignored. The trusted operator explicitly granted C administrator, then revoked it; the **same real token** changed from admin access 200 to 403. This is current database authority, not a signed-claim shortcut.

### Restricted SQL and production code

- Actual API-image supabase_admin TCP identity was verified with a READ ONLY transaction before account creation. No operator fallback was used.
- Actual vq_api and vq_worker TCP logins passed production `create_runtime_pool()` / `verify_runtime_role()`, including role identity, flags, memberships, ownership, and private-platform access checks.
- 1,072 exact column ACL comparisons were executed through the two restricted TCP pools. These are catalog checks, not 1,072 business workflows.
- Real denied statements included SET ROLE to owner/counterpart/authenticated, public DDL, Auth/vault reads, migration-ledger/helper access, role escalation, immutable username modification, API scoring writes, worker input modification, worker publishing, and private-note reads. Each required InsufficientPrivilegeError and rolled back its transaction.
- Production `create_submission()` executed queued INSERT, real duplicate lookup, and progress ON CONFLICT upsert under vq_api. `record_publication_failure()` performed its narrow failure update. An accepted-row insertion under vq_api was rejected by RLS.
- The worker read official solution/testbench/execution profile and executed compiling updates. Actual production `award_xp()`, `update_streak()`, and `check_quest_completion()` ran inside rollback-only permission fixtures, including the real progress row lock and conflict-upsert statements. Badge ON CONFLICT and append-only audit insertion were exercised too.
- Worker pending-validation UPDATE ... RETURNING succeeded for a validating unpublished draft; attempted alteration of the published fixture produced UPDATE 0. These are lifecycle permission fixtures, not simulator validation.
- Real HTTP submission ignored spoofed user/role fields, retained the authenticated student's identity, reached the real publisher with broker deliberately unavailable, and returned truthful 503/DISPATCH_FAILED. Valid profile/history/admin requests continued after denied operations.
- Final zero scoring after rolled-back worker fixtures was asserted. Accounting algorithms, idempotent award races, reconciliation, and crash safety are not certified by these fixtures.

The actual packaged Python source hashes matched the current backend tree before live writes. The final service bound **127.0.0.1:48603 inside the temporary container**, not a host-facing API port; production lifespan and health startup were observed.

## Failures and smallest corrections

1. **Snapshot attempts 1/2:** exit 1 before bootstrap/application. Windows ACL parsing/verification failed (JSONDecodeError, then GateError). The new private driver was corrected to verify the DACL with native Windows APIs. A third attempt passed archive/encryption/ACL checks before any DB write. Only the two known empty failed-attempt directories were later removed.
2. **Live attempt 1:** exit 1 after 1,205 successful assertions. An unfiltered PostgREST authoritative PATCH returned 400, not expected 403; the failing expectation was Client authoritative update denied. The original response body was not recorded, so a particular platform-extension error is **not verified**. No acceptance was inferred from that failure. Independent cleanup counts confirmed zero accounts/fixtures.
3. **Harness correction:** targeted authoritative PATCHes now include the fixture owner's WHERE filter and assert **403 plus 42501**, rather than accepting any error. Only sanitized error codes are recorded; no messages/rows/credentials. This removes unfiltered-update safeguards as a confounder without changing application grants.
4. **Live attempt 2:** exit 0, 1,237 assertions passed, using Auth administrator-created test identities. This did not itself prove public signup.
5. **Coverage correction:** two students now use the actual public signup endpoint; Docker inspection gates releasing the secret capsule/account writes, and safe startup/pool/isolation evidence is returned.
6. **Live attempt 3:** exit 1 after 1,196 assertions, TimeoutError in the SQL portion; no SQLSTATE was recorded. Accounts and API container were removed, but fixtures_removed=false. Counts showed only 3 challenges, 2 prerequisites, 3 secrets, 2 quests, 6 quest links, and 1 badge remaining. Exact challenge run suffix/fixture titles, quest fixture titles/counts, matching badge name/count, and absence of Auth users were privately verified against the earlier empty baseline. The exact resource inventory was DPAPI-sealed; exact-ID challenge → quest → badge deletion removed that residue, without resets or broad prefix deletion. Subsequent all-table counts were zero.
7. **Safe diagnostics correction:** the harness now records a nonsecret SQL-step label and SQLSTATE if present. This does not increase timeout limits, change grants, or hide failures.
8. **Final live attempt 4:** exit 0, **1,237 assertions and 92 recorded HTTP cases**, public signup included; all cleanup flags true. The prior timeout did not recur. Its original cause remains unresolved.

No database permission defect required a forward migration. No already-applied SQL, migration manifest, backend/auth implementation, or XP algorithm was changed by these corrections.

## Commands and checks

Nonsecret abbreviations for the commands below:

```powershell
$databaseGateDocker = 'C:\Users\tsush\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe'
$privateRecovery = 'C:\Users\tsush\AppData\Local\VeriQuest\recovery\live-ee7fe07f5535490f89728348b707c83d'
```

| Actual command / operation | Exit and result |
| --- | --- |
| .venv/Scripts/python.exe -B tools/database_gate.py --docker $databaseGateDocker --mode preflight | 0; fresh before writes; complete afterward |
| Docker build --quiet -t vq-db-live-api-20261001 backend | 0 |
| Private driver --phase snapshot --authorize-live-database-gate (same explicit --docker) | Attempts 1/2: 1; attempt 3: 0 |
| Private actual-image operator TCP probe, binary stdin, READ ONLY | 0; identity verified; temporary container removed |
| Private driver --phase apply --private-directory $privateRecovery --authorize-live-database-gate | 0; production bootstrap/apply/preflight/replay each 0 |
| Private driver --phase live --private-directory $privateRecovery --image vq-db-live-api-20261001 --authorize-live-database-gate | Attempts 1–4: 1, 0, 1, 0 |
| Production runner underlying write CLI | bootstrap/apply --authorize-local-write; unchanged prompts/assertions |
| Live harness underlying CLI | --live --authorize-local-test-writes --docker $databaseGateDocker --image vq-db-live-api-20261001 |
| Exact timeout-fixture recovery, verified target and private ID inventory, then read-only zero counts | 0 |
| .venv/Scripts/python.exe -B tests/test_database_gate.py | 0; 14 passed, rerun after harness corrections |
| .venv/Scripts/python.exe -B tests/test_database_live_driver.py, elevated CurrentUser environment | 0; 4 passed |
| .venv/Scripts/python.exe -B tests/test_auth_compatibility.py | 0; 17 generated-key regressions passed |
| Docker API-image pytest command with obsolete test filenames | 1; missing tests/test_auth.py, no tests collected |
| Docker API-image python -B -m pytest -p no:cacheprovider -q tests | 0; 52 passed, 2 deprecation warnings |
| AST parse of all three task-edited Python files | 0 |
| Final UTF-8 literal credential-pattern scan and Git count assertions | 0; no findings; 19 tracked modified, 30 individual untracked, 0 staged |
| git diff --check | 0; LF/CRLF informational warnings only |
| Final READ ONLY full runner assertions, ledger/counts, health/JWKS, target/artifact recheck | 0 |
| Read-only firewall profile/connection queries in sandbox | 1; access denied |
| Elevated read-only firewall queries | 0 |
| Exact empty-directory cleanup | 0; 2 empty directories removed |
| Docker image rm vq-db-live-api-20261001 | 0; task tag/image removed |

The unit-container command used --rm, --network none, --read-only, --cap-drop ALL, no-new-privileges, /tmp tmpfs and no DB transport; it proves unit behavior only. The original obsolete-filename failure is not omitted from the record.

The first driver-unit invocation in the restricted sandbox reported 1 error because DPAPI could not access the actual user's cryptographic profile. It was in a combined PowerShell invocation whose subsequent successful auth suite made the shell return 0; this was **not counted as a passing driver test**. A separate elevated invocation then passed all 4 driver tests, including real in-memory DPAPI roundtrip/tamper rejection. The driver transport/target-refusal tests use controlled mocks and do not prove database permissions.

An initial counts-only probe also failed due PowerShell quoting before it reached the database (exit 1); it was replaced with a captured stdin Python script and succeeded. No automatic target switching or database repair occurred.

The first final report/source scan encountered Windows' default cp1252 decoding on the UTF-8 report; its combined shell command returned 0 because the following diff check passed. That incomplete scan was not counted as successful. An independent UTF-8 scan then exited 0 with no literal credential-pattern findings and verified the Git counts. Pattern scanning supplements, rather than replaces, source review.

API image ID tested: sha256:da46112e61d007782c6c95093c9cabc0a95f6bf9f4b18ec60baf10ebd3b66e91. It was built before live tests and source-hash verified by the harness. The temporary tag/image was removed afterward without pruning shared images/cache.

Image dependency versions: Python 3.12.14; asyncpg 0.31.0; FastAPI 0.142.2; httpx 0.28.1; uvicorn 0.54.0; python-jose 3.5.0; cryptography 50.0.2; pytest 9.1.1; Celery 5.6.3; redis 8.1.0. Existing dependencies only; no system installation.

## Isolation, LAN exposure, and cleanup

Final **actual Docker inspect** evidence before test account writes:

```json
{"running":true,"port_bindings":{},"readonly_rootfs":true,"cap_drop":["ALL"],"security_opt":["no-new-privileges:true"],"memory":402653184,"pids_limit":64,"network_mode":"bridge","no_socket_mount":true,"bind_mounts_readonly":true}
```

There was no host API port published at all. Loopback-only internal API binding is directly recorded above. Bridge network access was needed for Auth/PostgREST/PostgreSQL transport; this live container was **not network-none**, unlike the isolated rehearsal/unit probes.

**Existing LAN exposure remains unresolved and material:**

- Gateway 54321 and PostgreSQL 54322 bind 0.0.0.0 and ::, not just loopback.
- Windows firewall profiles were enabled; defaults reported NotConfigured, not affirmative effective blocking.
- Active network was Public. Two enabled inbound Docker-backend allow rules applied to Public with LocalAddress Any, RemoteAddress Any, LocalPort Any, respectively TCP/UDP.
- These observations do not prove remote reachability, but they do not support a claim of LAN containment. No external-host reachability probe was performed, and no firewall or Supabase settings were changed. Keep this disposable environment off untrusted networks until separately reviewed containment.

Final cleanup evidence:

- Final harness: api_stopped=true, fixtures_removed=true, all three account deletion/absence checks true.
- Independent READ ONLY counts: Auth users **0**; all **14 application tables 0 rows** (including profiles, roles, challenges, hidden secrets, progress, submissions, XP, quests, badges, audit).
- Ledger retains exactly four applied versions; restricted roles retained.
- Docker ps showed no vq-db-live-* container; operator, unit, version, and live probe containers absent. Existing 10 project Supabase containers remain running.
- Temporary API image removed, no queue/grading services started.
- Two known empty failed-snapshot directories removed nonrecursively after exact path/empty checks; encrypted recovery directory retained.
- Final private artifacts decrypt/read correctly, directory ACL reverified, snapshot target/image/manifest and full archive readability rechecked.
- No task-created HTTP host service remains.

Cleanup on the timed-out attempt was **not initially successful**; the subsequent exact-resource recovery and final independent counts establish current cleanup, not guaranteed automatic cleanup under future failures. Interruption-safe private resource journaling remains a harness improvement to review separately.

## Source changes and repository preservation

This task changed/created only:

- [tools/database_live_gate.py](C:/Users/tsush/Desktop/veriquest/tools/database_live_gate.py): new private recovery/bootstrap/live driver, DPAPI, ACL/archive/target checks, secret-free command transport.
- [tests/database_permission_live.py](C:/Users/tsush/Desktop/veriquest/tests/database_permission_live.py): scoped authoritative PATCHes and exact SQLSTATE assertions; real public student signup; sanitized status/step diagnostics; actual Docker-inspection gating; safe startup and runtime-pool evidence.
- [tests/test_database_live_driver.py](C:/Users/tsush/Desktop/veriquest/tests/test_database_live_driver.py): four focused production-helper regression checks.
- [this report](C:/Users/tsush/Desktop/veriquest/docs/handoff/DATABASE_LIVE_PERMISSION_REPORT.md).

SHA256 comparison against the task-start pending-file/report snapshot found only the intentionally edited live harness changed among those existing files. Prior implementation changes, reports, manifest/policy and all migration files were preserved. The backend-security-coder skill guided private credential handling, fail-closed target checks, actual restricted-role evidence, and exact cleanup.

Current Git state: main at the unchanged HEAD above; **nothing staged**. There are 19 previously modified tracked files and 30 individual untracked files, including this report and prior milestone work. No secret/recovery file, .venv, cache, or generated dependency was added to Git status.

Tracked unstaged files (all pre-existing work, not edited by this task):

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

Individual untracked files:

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
docs/handoff/DATABASE_LIVE_PERMISSION_REPORT.md
docs/handoff/DATABASE_PERMISSION_GATE_ASSESSMENT.md
docs/handoff/DATABASE_PERMISSION_REMEDIATION_REPORT.md
docs/handoff/PAUSE_CHECKPOINT.md
supabase/migrations/004_permission_gate.sql
supabase/migrations/005_profile_identity_gate.sql
tests/database_permission_live.py
tests/database_rehearsal_operations.py
tests/test_database_gate.py
tests/test_database_live_driver.py
tests/test_worker_dispatch.py
tools/database_gate.py
tools/database_live_gate.py
tools/database_migrations.json
tools/database_policy.json
tools/database_rehearsal.py
worker/execution/profile.py
```

Review of new/edited source found no literal live credentials, DSNs with passwords, tokens, or private artifact payloads. The new driver unit file's repeated-letter values are explicitly synthetic regression inputs. All credential-bearing artifacts are outside the repository/build contexts and encrypted.

## Remaining limits / stop point

Verified by real execution: local transactional installation/replay/ledger, effective catalog ACL/RLS/helper/trigger state, real public signup identity provisioning, real ES256-backed API requests, restricted TCP production pools, representative allowed/forbidden SQL and unchanged-state assertions, current admin grant/revocation, truthful unavailable-broker failure, and current cleanup.

Not established:

- Restoring this snapshot into a real Supabase clone; archive readability is narrower evidence.
- Root cause of the single SQL timeout; deterministic replay/interruption-safe fixture journaling.
- Redis/Celery delivery, a real queued worker, native simulator/container grading or workspace mounts.
- Accounting correctness, concurrent awards/reconciliation, atomic/outbox publication, crash recovery.
- Full successful administrator simulator validation/publication workflow; fixture publication was explicit test setup.
- Existing-user backfill/collisions or historical/untracked-deployment upgrades; this target was empty.
- GraphQL permission equivalence, hosted Supabase, deployed behavior, production configuration/readiness.
- Populated cross-user XP/badge/streak reads: their worker writes were rolled back, so the live other-user empty-result checks on those tables are weaker than the populated submission/progress/profile ownership checks. Catalog policies were asserted, but populated-row HTTP ownership needs separate coverage.
- External LAN containment.
- Production process-wide secret isolation: this authorized fixture harness held privileged setup credentials; production API/worker must receive only their own runtime credentials.
- App permission isolation if an authorized API SQL session is itself compromised: the API role deliberately includes current administrator authoring capabilities; it is not per-request database RLS isolation.

The historical preparation runbook/reports still contain dated “not applied / not run” statements. **This report supersedes those statements for this disposable target only**, without rewriting historical evidence.

Stop here as requested. Do not run seed 002, recreate accounts, start queues/grading, or advance to another milestone automatically.

