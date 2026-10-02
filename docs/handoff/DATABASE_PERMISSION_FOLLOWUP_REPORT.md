# Database permission follow-up: populated ownership and recoverable harness

Date: 2026-10-01, Asia/Calcutta. Disposable target only: veriquest-local-test.
This report supplements, and does not overwrite, DATABASE_LIVE_PERMISSION_REPORT.md.

## Outcome and scope

**Implemented and locally verified.** Three complete strengthened live runs each passed **1,314 assertions and 137 recorded HTTP cases**, using actual Supabase Auth, PostgREST, the current API image, production authentication, restricted SQL pools, and the full API lifespan. No dependency overrides or mocked permission success were used.

The missing populated XP/badge/streak ownership coverage is now exercised in both directions. Pre-write encrypted exact-resource intent and idempotent recovery were implemented. Four controlled process exits tested three interruption points, including two populated-fixture crashes. A deliberately blocked recovery demonstrated rejection of an unrelated cross-run reference with **every application row unchanged**.

The historical timeout was **not reproduced and remains unresolved**. Smaller controlled lock/statement cutoffs proved bounded handling, not that historical timeout's cause.

No reset, seed 002, migrations, checksum/ACL changes, queues, grading services, deployment, staging, commit, or push occurred. The only application role assignments were disposable administrator test data, not PostgreSQL GRANTs. All temporary accounts/fixtures/services and API images were removed; Supabase, schema, restricted roles, and private artifacts remain.

## Initial and final target verification

Repository: C:\Users\tsush\Desktop\veriquest. Branch main; unchanged HEAD:
7c7d1cd6062fcde09f06078830c1c490eb5b1675.
Read-only remote parsing confirmed github.com / tsushanth12-afk/veriquest, without embedded credentials.

Initial production preflight exited 0:

```json
{"mode":"preflight","state":"complete","role_count":3,"application_table_count":14,"auth_user_count":0,"writes":false}
```

Before every live/recovery phase, the driver reverified the named local DB/REST project/workdir labels, port 54322, exposed schemas, exact DB container identity and snapshot identity, manifest, complete applied ledger, and full runner permission assertions in READ ONLY transactions. The gateway credentials were obtained privately from the verified local gateway; its health was checked. No alternate DSN, hosted target, administrator runtime fallback, bootstrap, or apply mode was used.

Applied versions remain 001, 003, 004, 005; 002 remains deferred and unrecorded. The migration files, policy specification, and manifest were byte-for-byte preserved. In particular:

- 004: 416a96975a680b6be2909496cc2acae4ed711926cb7e4e21dc376055347d38bd
- 005: 998ec791149fbba706f85161b398db298b5fcf44e93f265fe75175413d780af6

Final independent preflight/SQL assertions succeeded: ledger 4, roles 3, application tables 14, Auth users 0. All 14 application tables have zero fixture rows.

## Populated ownership evidence

[tests/database_permission_live.py](C:/Users/tsush/Desktop/veriquest/tests/database_permission_live.py), `live_inside()`, now uses the fixture operator to commit distinct permission fixtures for A and B:

- XP transaction amounts 17 and 29, reason permission_fixture, with distinct predeclared IDs.
- Different badge definitions and award IDs for each student.
- Different streak record IDs/dates and activity counts 1 and 2.
- Corresponding profile XP/streak values set explicitly by the fixture operator for API projection checks.

These are **permission fixtures**, not genuine graded awards or evidence that ledger/profile accounting is correct. Production award/streak/quest functions still run in rollback-only capability fixtures before these records are populated. Initial signup zero-progress assertions remain.

Both students signed up through real public Auth and signed in with actual password tokens; C used supported local Auth administration and received a trusted DB administrator fixture grant. Passwords/tokens stayed in memory; runtime credentials stayed in the existing DPAPI mechanism.

For each of XP transactions, badge awards, and streak records:

| Check | Actual response / assertion |
| --- | --- |
| A lists both fixture IDs | 200, exactly A's own expected record and values |
| B lists both fixture IDs | 200, exactly B's own expected record and values |
| A explicitly filters B's ID | 200, empty |
| B explicitly filters A's ID | 200, empty |
| Anonymous filters populated IDs | 401, SQLSTATE 42501 |
| A/B insert, update, delete attempts | 403, SQLSTATE 42501 |
| Anonymous insert, update, delete attempts | 401, SQLSTATE 42501 |
| After each forbidden mutation | Exact authoritative-state fingerprint unchanged |

This section adds **15 read cases** and **27 denied mutation cases**, with state checks after every mutation. Each table was known to contain both students' rows; no isolation conclusion relies on an empty table.

Production API checks added:

- GET /api/v1/profile for A and B: 200, exact own subject, own XP/streak values, and only own badge.
- A request carrying B's user_id query, and vice versa, still returns the signed-in identity's projection.
- Anonymous profile request: 401.

The existing API does not expose dedicated raw XP-transaction or streak-history endpoints. Exact raw-row ownership was verified through PostgREST; API coverage verifies its existing profile/badge/stat projection. No new product endpoint was invented.

Existing live coverage also remained passing: zero-progress signup and hostile metadata handling, safe/mixed profile boundaries, other-user submission/progress isolation, public curriculum filtering, student staff denials, database-backed administrator grant/revocation, actual restricted API/worker TCP pools, ON CONFLICT/RETURNING/row locks, hidden schema denial, and real unavailable-broker submission **503 / DISPATCH_FAILED**. These checks still do not prove successful queue delivery or native grading.

Final complete HTTP case array totals 137. The 92 previous recorded cases remain, supplemented by 42 populated PostgREST cases and 3 API cases. Health/private-schema/cleanup requests are additional assertions outside that array.

## Timeout investigation and bounded SQL

Source examined: the prior report's TimeoutError after 1,196 assertions; current `runtime_checks()`, fixture operator helper and cleanup; production pool creation/close and submission/award SQL. The old failure did not record the precise statement, SQLSTATE, or blocking session. Its failed fixture cleanup was already documented and recovered in the previous milestone.

A bounded private PostgreSQL log-tail inspection and aggregate activity query returned:

- Statement-timeout entries: 1; lock-timeout entries: 1.
- Idle-transaction timeout entries: 0; deadlock entries: 0.
- Current lock wait count 0, recorded deadlock counter 0, backend count 13.

This observation was after the first new controlled timeout probes. Those entries cannot be attributed to the historical failure, and the counts are not proof that no past network/scheduling/lock issue occurred. Raw logs, query text, parameters, and identities were not printed.

New production harness helpers in
[tools/database_live_resources.py](C:/Users/tsush/Desktop/veriquest/tools/database_live_resources.py):

- `TimedConnection.call()`: aggregates safe fixed role/method/operation/table labels, count, total/max duration and SQLSTATE/type. Never records SQL text, parameters, exception messages, emails or returned rows.
- `TimedPool.acquire()`: delegates to the actual asyncpg pool, setting only session statement_timeout=10s, lock_timeout=1500ms and idle_in_transaction_session_timeout=10s on acquired harness connections.
- Fixture/recovery operator connections have the same SQL bounds; connect stays 5s, existing client command bound stays 15s, close is bounded to 5s.
- Harness runtime pool close is bounded to 10s and terminates that pool on failed close.
- The actual HTTP application's pool implementation/defaults and dependencies are unchanged. These wrappers instrument direct production-service SQL through real connections, not fake results.
- No ALTER ROLE/database setting, larger timeout, disabled limiter or write-retry loop was introduced.

Controlled native probes:

1. The operator held A's profile row FOR UPDATE. A restricted API connection used a 250ms local lock cutoff. Its update raised **55P03**, rolled back, left bio unchanged, and subsequent valid SQL succeeded.
2. A restricted connection used a 150ms local statement cutoff against pg_sleep(2). It raised **57014**, rolled back, and SELECT 1 succeeded afterward.

Latest guarded complete run measured approximately **253.43ms lock cutoff** and **152.10ms statement cutoff**. It recorded 1,402 timed direct SQL calls, including 1,072 runtime column-ACL comparisons; these counts are not business-workflow counts. Maximum observed operator connect was 48.27ms. The slowest timed SQL was the intentionally blocked update, 253.38ms; the intentionally canceled sleep measured 152.05ms. Expected 42501/55P03/57014 entries in telemetry are negative-test evidence, not unexpected failures.

An earlier complete strengthened run measured 255.37ms / 152.12ms, and another measured 255.10ms / 151.91ms. No unintended TimeoutError occurred in this follow-up. Potential prior lock/network/scheduling causes remain hypotheses, not a reproduced diagnosis.

## Durable private intent and recovery design

[tools/database_live_gate.py](C:/Users/tsush/Desktop/veriquest/tools/database_live_gate.py):
`live()`, `secure_directory()`, `journal_path()`, existing `sealed_write()`.

Before starting any writer:

1. Validate snapshot/target/manifest and installed permission state.
2. Reverify protected current-user/SYSTEM directory ACL.
3. Generate an exact immutable resource plan.
4. Encrypt with Windows CurrentUser DPAPI; exclusive-create, flush/fsync, decrypt/readback and validate the saved plan.
5. Only then launch/inspect the no-port/no-socket read-only container and release the private stdin capsule.

Plans include exact Auth emails plus per-run metadata marker, exact API challenge slugs including the expected-denied creation, predeclared UUIDs for quests/badges/XP/awards/streaks, original writer container identity, DB container identity and migration manifest. Journal filenames are independent of account-name nonces. No password, DSN, key or token is needed in an intent journal. Credentials retain the existing encrypted private file.

This closes the known **server creation → missing generated ID persistence** gap: account/challenge IDs need not be appended after creation. Recovery resolves their exact predeclared natural keys and verifies markers, including when the process never retains the creation response's ID. Resources whose UUIDs are client-controlled are declared before insertion. Live replay refuses existing keys/IDs; recovery is a separate explicit mode.

`resolve()` and `cleanup()` use parameterized equality/ANY lookups, not LIKE/prefix deletion. Recovery refuses while the original writer container exists. It verifies trusted fixture operator identity, locks only exact parent rows, and rejects outside references before deleting anything. One bounded FK-ordered transaction removes audit/XP/submission dependencies, challenges, quests and badge definitions. Only afterward does supported Auth administration delete the exact resolved accounts, verifying 404 absence. Profile-linked rows cascade according to the installed schema.

SQL cleanup is transactional; Auth administration is necessarily a separate phase. Repeating recovery can finish partial Auth deletion and resolves already-absent resources as no-op. Failures retain intent and safe diagnostics rather than silently retrying writes. Journals and safe result receipts are never automatically erased.

Final private verification found **8 readable target/manifest-valid journals and 15 readable encrypted receipts**, with restricted ACL reverified. Supplemental exact-link intent and preservation fingerprints are encrypted too. Snapshot, runtime credentials and older private artifacts were retained.

Windows app redirection resolved the actual directory to:

```text
C:\Users\tsush\AppData\Local\Packages\OpenAI.Codex_2p2nqsd0c76g0\LocalCache\Local\VeriQuest\recovery\live-ee7fe07f5535490f89728348b707c83d
```

The shorter AppData\Local\VeriQuest alias worked in this Codex session. Resume through the same verified private mechanism. A different launcher/user/profile may resolve LOCALAPPDATA differently or lack DPAPI access; stop on that mismatch rather than copying/decrypting artifacts into the repository.

## Controlled interruption and idempotence evidence

Each interruption calls **os._exit(86)**, bypassing Python finally and account/fixture cleanup. The original API/container process terminates; recovery runs separately from the sealed journal.

| Tested point | Verified condition | Recovery result |
| --- | --- | --- |
| signup_response | Real signup 200; exit before extracting/retaining its generated account ID | 1 account resolved; DELETE 200 / GET 404; exit 0 |
| challenge_response | Real API creation 201; exit before retaining its generated challenge ID | 3 accounts + 1 challenge resolved; all Auth deletions 200/404; exit 0 |
| populated_fixtures, first run | 3 Auth accounts, 3 challenges, 2 XP rows, 2 badge awards, 2 streak rows, 4 badge definitions including separate sentinel verified by read-only counts | Exact interrupted resources removed; sentinel retained; exit 0 |
| populated_fixtures, final guarded run | Same populated fixture stage; final recovery implementation | Outside-reference refusal tested, then exact recovery succeeded; separate quest retained |

Recorded assertions/cases before intentional exits: signup 1/1; challenge 22/9; each populated interruption 1,201/56. These partial counts are **not passing complete permission runs**. Inner harness/driver reported 86; the PowerShell execution wrapper reported nonzero 1, as expected.

A first journal was replayed after cleanup **while a different interrupted run still had 3 accounts and 1 challenge**. Replay resolved zero accounts/challenges and removed nothing from that other run or its sentinel; independent counts confirmed preservation. This directly exercises idempotence and cross-run scope, not merely an empty database.

### Unrelated-reference guard, actual SQL

During final source review, cleanup gained `reject_external_references()` and exact parent FOR UPDATE locks to avoid unchecked FK cascades. A separate control journal predeclared an unrelated quest; an encrypted supplemental intent predeclared an exact junction ID linking that quest to the interrupted run's challenge.

Actual recovery then:

- Exited 1 with **UnrelatedFixtureReference**, before deletion/Auth administration.
- Rolled back its transaction and released locks.
- Preserved **all application rows across all 14 tables**, verified against private before/after row fingerprints, not just counts.
- After removal of only the exact task-created blocking junction, succeeded for the interrupted journal while preserving the unrelated quest.
- The separate control journal then removed its own quest; final counts were zero.

No grant was broadened, no migration altered, and no database reset was used to make this test pass.

### Preservation and untested crash windows

An independently journaled sentinel badge remained after each original interruption recovery and the second complete live run. Additional private baselines proved:

- 54 pre-existing Auth audit rows unchanged.
- Auth migration-history rows unchanged.
- All PostgreSQL role flags unchanged.
- Full current application ownership/ACL/RLS/helper/trigger/ledger assertions remained valid.
- A separate run's resources and a separate quest were not swept away.

Normal Auth events appended platform audit records. Final Auth audit count was **112**; these platform logs were deliberately **not purged**. Zero Auth accounts and zero application fixtures do not mean zero platform audit history.

Tested durability is process-exit/fsync/readback behavior, not power-loss certification. Still untested:

- A crash inside journal file creation/fsync; unit tests verify persistence failure prevents dispatch, not hardware durability.
- Docker/host death, disk failure, DPAPI profile loss or receipt-write failure.
- Unknown in-flight Auth/API requests before a response: stopping the writer does not guarantee cancellation of an upstream request. Immutable intent permits exact later discovery, but observed absence is not distributed quiescence.
- Crash during the fixture transaction/COMMIT acknowledgement or between individual Auth deletions.
- Concurrent recovery controllers or unrelated concurrent writers, especially non-FK polymorphic audit references.
- Every individual insert/intermediate fixture point; the tested full-fixture and two generated-ID windows are narrower than exhaustive fault injection.

Keep journals for uncertain outcomes and reverify before separately authorized recovery. Do not label a pending request settled or discard intent merely because one query returned no row.

## Commands and executed regressions

Commands used existing dependencies. No system-wide installation. Nonsecret variables below abbreviate actual arguments:

```powershell
$databaseGateDocker = 'C:\Users\tsush\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe'
$privateRecovery = 'C:\Users\tsush\AppData\Local\VeriQuest\recovery\live-ee7fe07f5535490f89728348b707c83d'
```

| Actual command / operation | Exit / actual result |
| --- | --- |
| .venv/Scripts/python.exe -B tools/database_gate.py --docker $databaseGateDocker --mode preflight | 0; complete, 3 roles, 14 tables, Auth 0 |
| Docker build --quiet -t vq-db-followup-api-20261001 backend | 0, twice; actual current backend context |
| Driver --phase live --private-directory $privateRecovery --image vq-db-followup-api-20261001 --authorize-live-database-gate, same --docker | 3 complete runs, all 0 / 1,314 assertions / 137 cases |
| Same driver with --interrupt-point signup_response | Expected inner 86 / outer nonzero 1 |
| Same driver with --interrupt-point challenge_response | Expected inner 86 / outer nonzero 1 |
| Same driver with --interrupt-point populated_fixtures | Twice, expected inner 86 / outer nonzero 1 |
| Driver --phase recover --journal <one exact private journal> with same authorization/image/target args | 7 successful recovery/replay invocations, exit 0; includes separate control cleanup |
| Recovery with deliberately linked outside quest | Expected 1 / UnrelatedFixtureReference; no rows changed |
| Exact sentinel/control/link setup, fingerprints and junction removal through private stdin SQL | 0; encrypted intent before fixture writes |
| Independent READ ONLY counts, full assertions and preservation checks | All 0 |
| .venv/Scripts/python.exe -B tests/test_database_live_resources.py | Initially 6 passed; final 7 passed, exit 0 |
| .venv/Scripts/python.exe -B tests/test_database_live_driver.py in authorized CurrentUser environment | 6 passed, exit 0, rerun |
| .venv/Scripts/python.exe -B tests/test_database_gate.py | 14 passed, exit 0, rerun |
| .venv/Scripts/python.exe -B tests/test_auth_compatibility.py | 17 generated-key tests passed, exit 0 |
| Actual API image python -B -m pytest -p no:cacheprovider -q tests | 52 passed, exit 0; 2 existing deprecation warnings |
| AST parsing, literal credential-pattern scan, baseline hash comparison | Passed |
| git diff --check | 0; existing LF/CRLF informational warnings |
| Docker image rm vq-db-followup-api-20261001 | 0 after each validation batch |

The image unit probe used --rm, --network none, read-only filesystem, dropped capabilities, no-new-privileges and tmpfs. It proves unit behavior, not live permissions.

Images actually built/tested (same backend source hashes verified before live writes):
- sha256:005365d3c89da219cd52f95e60fad76af6f6b7e4c073dba2519d2c249a6e2e44
- sha256:000f7116cef2005b4d8c8662cd1a0b7dcede1146eef68d5cf7ba00b6de246343

No unexpected assertion failure or collection/dependency blocker occurred in this follow-up. Intentional aborts, deliberate SQL cutoffs, and the expected guarded-recovery refusal are reported separately, not suppressed or counted as complete successes.

Unit/helper tests import actual driver/resource helpers and exit nonzero on failed expectations. Controlled transports/AsyncMock tests check intent ordering, persistence failure, marker/collision/refusal behavior and telemetry redaction; they do not prove live SQL behavior. Actual CurrentUser DPAPI roundtrip/tamper checks ran on Windows. Real HTTP/SQL and interruption outcomes above are separate native integration evidence.

## Cleanup, network and remaining gates

Final independent verification:

- Auth users 0.
- All 14 application tables 0 rows, including sentinel/control/link fixtures.
- Ledger 4, restricted roles retained, permission assertions passed.
- No vq-db-live-* or vq-db-followup-* test container.
- Both temporary API image tags/images removed; no shared-image pruning.
- Existing 10 Supabase project containers remain running.
- Private recovery artifacts/journals/receipts retained and readable; restricted ACL reverified.
- Existing platform audit data retained as described above.

Every live/recovery container was actually inspected before releasing credentials/writes: read-only filesystem and source binds, no Docker socket, no published ports, ALL capabilities dropped, no-new-privileges, 384MiB and pids limit 64. The real API bound to 127.0.0.1 inside its temporary container, with ephemeral ports. Bridge transport was necessary for Supabase; these were not network-none live containers.

Existing gateway 54321 and PostgreSQL 54322 still bind **0.0.0.0 and ::**. No firewall/network settings were changed. The prior report's broad Public-profile Docker inbound allow-rule evidence remains unresolved LAN containment, not proof of remote safety.

Still outside this gate: real snapshot restoration, successful Redis/Celery delivery, native worker grading/workspaces, accounting correctness/concurrency/reconciliation, revision lifecycle, hosted/deployed behavior and production readiness. Permission fixture values and rollback-only award SQL do not establish any of those.

## Files and repository state

Changed existing files:

- [tests/database_permission_live.py](C:/Users/tsush/Desktop/veriquest/tests/database_permission_live.py): `live_inside()`, `recovery_inside()`, `main()`; populated ownership, bounded native instrumentation, crash hooks, journal-gated setup, shared cleanup.
- [tools/database_live_gate.py](C:/Users/tsush/Desktop/veriquest/tools/database_live_gate.py): `live()`, `secure_directory()`, `journal_path()`, CLI recover/interruption flags; durable encrypted pre-write plans and receipts.
- [tests/test_database_live_driver.py](C:/Users/tsush/Desktop/veriquest/tests/test_database_live_driver.py): journal-before-dispatch and failed-persistence regression checks.
- [docs/DATABASE_PERMISSION_GATE.md](C:/Users/tsush/Desktop/veriquest/docs/DATABASE_PERMISSION_GATE.md): accurate applied state and documented journal/recovery procedure and limitations.

New files:

- [tools/database_live_resources.py](C:/Users/tsush/Desktop/veriquest/tools/database_live_resources.py): plan validation, timing/bounds, exact lookup/recovery, parent locks and external-reference refusal.
- [tests/test_database_live_resources.py](C:/Users/tsush/Desktop/veriquest/tests/test_database_live_resources.py): 7 focused helper regressions.
- [this report](C:/Users/tsush/Desktop/veriquest/docs/handoff/DATABASE_PERMISSION_FOLLOWUP_REPORT.md).

The backend-security-coder skill guided secure intent persistence, fail-closed marker/target checks, scoped cleanup and credential-free diagnostics.

A 71-path task-start SHA256 baseline found only the four intended existing files above changed. Prior implementation, all handoff reports including the live report, all migrations and manifest/policy were preserved. No backend/frontend/worker grading or XP implementation was modified.

Git remains main at the HEAD above: **0 staged, 19 pre-existing tracked modifications, 33 individual untracked files** including prior work and this task. No .venv, cache, secret, private journal, recovery artifact or generated dependency was added to Git status. Nothing committed or pushed.

Stop after this report. The populated ownership gap and tested post-creation ID-loss recovery points are now closed; historical timeout attribution and broader crash/distributed recovery guarantees remain explicitly unresolved.

