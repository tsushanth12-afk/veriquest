# Queued native grading — resumed 1-XP gate

Completed: 2026-10-09, Asia/Calcutta; runs began 2026-10-08.
Branch main; unchanged HEAD `49b51f94cddb3848719212975f46169986d9efaa`.
The original blocked attempt is retained unchanged below as historical evidence.
The user explicitly authorized 1-XP fixtures; zero-reward support was NOT added.

## Resumed outcome

**Final corrected gate PASSED, exit 0: 290 assertions, 19 recorded API HTTP cases,
six actual Redis publications, six worker receipts and six real native executors.**
These assertions include environment, isolation, evidence and cleanup checks, not
290 grading jobs. Three failed harness attempts and one exact recovery are retained
below. Repeated builds/tests do not multiply unique coverage.

Real production Auth, API lifespan/pool/limiter/publisher, Redis, Celery consumer,
restricted worker SQL, Docker sandbox, Icarus, verdict parser and accounting ran.
Correct HDL remained accepted with 1 XP; ordinary wrong and forged markers/counters
were wrong_answer; syntax was compilation_error; infinite simulation was timeout.
A subsequent ordinary job passed, with no repeated challenge XP award.

**Accounting correctness is NOT certified.** Actual six distinct submissions left
profile total_attempts=5 and summed challenge progress attempts=10. This follows
the current separate API/worker updates and accepted-repeat early return; it is
recorded as a discrepancy, not hidden or repaired. No accounting exception blocked
terminal success in the final run. No bonus definitions were present.

No migrations, applied checksums, constraints, grants, production configuration,
grading/accounting algorithms, worker claim/retry/recovery architecture, firewall,
Supabase settings, commit, push or deployment changed. Temporary fixture publication
was authorized setup, not evidence of successful administrator validation.

## Reverification and scope

Read PAUSE_CHECKPOINT, both native reports, the historical blocked report, delivery
report/database runbook, existing delivery/native/private recovery harnesses, and
actual submission/publisher/runtime/auth/config, worker/Celery, sandbox/workspace/
runner/verdict and accounting code. No applicable AGENTS.md was found.
Initial pending work was only this untracked historical report; it was preserved.
Branch/HEAD/origin and read-only remote parity matched the baseline repository.

Production read-only preflight passed before writes: complete ledger, three reviewed
roles, fourteen application tables, zero Auth users. Private provenance/full READ
ONLY ownership/ACL/RLS/helper/trigger assertions passed before builds and again
immediately before each run's first Auth/fixture write. Exact DB/REST/Auth/gateway
project/workdir, retained volume and creation time, host PG 54322/API 54321, manifest
001/003/004/005 and deferred 002, snapshot/image/archive integrity, private directory
ACL/DPAPI and distinct retained runtime credentials were verified using the existing
reviewed mechanism. Historical snapshot pins/credentials were never rewritten;
restart attestations are separate encrypted append-only artifacts.

Docker remained desktop-linux / Linux 29.8.0. Supabase was already running: nine
running containers and the preexisting exited edge_runtime. No restart/repair.
Auth health/JWKS returned 200; one ES256/EC/P-256 key and exact declared issuer
`http://127.0.0.1:54321/auth/v1` were verified. Real signin tokens then passed
production signature verification through authenticated API operations; decoded
claims alone were not treated as proof. Container JWKS/PG used host.docker.internal
transport without changing issuer identity.

Each full attempt created only two students and two catalog-derived AND fixtures,
one normal 5000ms profile and one 1000ms timeout profile, each xp_reward=1. Both
students had zero-progress signup profiles and no administrator role. Unused keys
reserved by the existing three-account/four-slug plan were never provisioned.
Across four corrected-attempt iterations eight disposable students were created
and all removed; do not describe this as only two accounts ever created.

Queued coverage here is AND-derived fixtures with these two valid profiles. All
four catalog native solutions previously passed the separate direct native gate;
this task does not claim four-catalog queued coverage from that prior evidence.

## Reproducible opt-in harness and trust boundaries

New files/functions:

- `tools/queued_native_grading.py`: QueuedGate.execute/new_intent/service/probe,
  start_broker_monitor/message/native_evidence/workspace_probe/cleanup; exact
  intent validation and Redis monitor metadata parsing.
- `tests/queued_native_probe.py:run`: separate short-lived authorized fixture
  operator, actual limited-pool checks, READ ONLY accounting snapshots and shared
  exact-key/FK-ordered/Auth-admin recovery. NOT the API/worker runtime service.
- `tests/queued_native_observer.py`: passive Python profile/trace callbacks in the
  disposable worker and production Workspace verification/recovery probe. No
  reassigned production functions, dependency overrides, fake receipts, fabricated
  exits/verdicts or replacement accounting. Callback errors lose evidence and fail
  host assertions; original calls/results/exceptions remain production behavior.
- `tests/test_queued_native_grading.py`: nine focused helper/protocol/security
  regression methods. These controlled tests are distinct from the live gate.

Current actual API/worker/executor Dockerfiles were built with unique journaled
tags. All 29 packaged API app files and 40 packaged worker/backend source files
matched current canonical-LF hashes; the actual baked vq-run hash matched source.
Production source was packaged, not replaced with host source mounts. Seed 002 was
only read-only TEXT for the existing parser regression, never executed as SQL.

Exclusive-create/fsync/DPAPI/readback seals exact account emails/markers, slugs,
idempotency keys, container/network/volume/check names and tags before provisioning.
API receives only vq_api DSN; worker only vq_worker. Both actual TCP logins and
production pool/role guards passed. Operator DSN and supported Auth-admin key are
given only to the separate fixture/recovery probe. Credentials reach process-local
environments by captured binary stdin after container inspection, not Docker Env,
argv, labels, plaintext files or tracked configuration. Passwords/tokens remain in
memory. Dynamic submitted source/bench payloads are not reported or saved to Git;
the harness contains only static test construction and uses the existing catalog.

Actual inspected isolation:

- API: no socket/volume, read-only root, ALL capabilities dropped, no-new-privileges,
  512MiB/one CPU/64 PIDs, bounded tmpfs/logs; final port **127.0.0.1:59840 -> 8000**.
- Redis: unique bridge, no host port, uid/gid 65534, disabled persistence, bounded
  tmpfs /data, read-only root/capability/resource restrictions. Actual version 7.4.11.
- Worker: actual default Celery command, concurrency=1, no host port, read-only root,
  512MiB/one CPU/64 PIDs; CHOWN/FOWNER/DAC_OVERRIDE only above cap_drop ALL for the
  reviewed file-ownership model. Docker socket remains privileged infrastructure
  authority, not proof that a compromised worker is isolated from the daemon.
- Task workspace: exact local-driver `type=tmpfs`, `device=tmpfs`,
  `o=size=134217728,mode=0700`; actual production statvfs/mount verification passed.
  Current four-outstanding-job/500ms admission rules were unchanged. This sequential
  gate did not repeat admission saturation. Plain volumes remain rejected and were
  not replaced; tmpfs recovery remains volatile.
- Every executor: user 1000:1000, network none, read-only root, ALL capabilities
  dropped/no additions, no-new-privileges, no binds/socket/ports, daemon log driver
  none, memory=swap ceiling 64MiB, 0.25 CPU/64 PIDs, /tmp 64MiB noexec/nosuid/nodev,
  per-file 64MiB ceiling, only exact generated RO input/RW output volume subpaths.

Only Redis/API/worker joined the unique test bridge. It permits required host Auth/
PG reachability and is not an outbound-denial sandbox. Executors use network none.
No complete Compose stack was started. Supabase's existing LAN exposure remains.

## Actual final HTTP, native and persistence evidence

All six initial POSTs returned HTTP 201 with a real queued submission ID. Owner
GETs returned 200 after actual task completion/acknowledgement; the second student
received 404 NOT_FOUND for every exact submission. No endpoint dependency override.

| Case | Owner verdict / error | Real compile / simulation / container exits | Capture / award |
| --- | --- | --- | --- |
| Correct | accepted / null; 4/4 | 0 / 0 / 0 | complete, 312 bytes, 1 XP |
| Wrong | wrong_answer / WRONG_ANSWER; 2/4 | 0 / 0 / 0 | complete, 316 bytes, 0 XP |
| Syntax | compilation_error / COMPILATION_ERROR | 2 / absent / 2 | 57 bytes, no trusted record, 0 XP |
| Forged marker/counters | wrong_answer / WRONG_ANSWER; 2/4 | 0 / 0 / 0 | complete, 372 bytes, 0 XP |
| Infinite simulation | timeout / TIMEOUT | 0 / absent / 137 | incomplete, timed_out=true, 0 XP |
| Ordinary recovery/new key | accepted / null; 4/4 | 0 / 0 / 0 | complete, 312 bytes, 0 additional XP |

The forgery was real student HDL emitting ACCEPTED/total/passed/failed text. Passive
observation asserted it reached stdout; production parser still used the one
independently nonce-bound wrong summary. No token was injected or guessed.
Timeout reached native compilation/simulation and actual kill, not scanner rejection.
Timeout was chosen instead of overflow; this is not another queued overflow test.
Every allocated job independently reported exact executor/workspace/record absence
after cleanup. No capture or RPC diagnostic truncation. No synthetic success path.

### Real correlation, not logs alone

The final broker observer subscribed successfully before requests and watched
actual Redis LPUSH hdl_execution envelopes, without popping/injecting messages.
The existing production harness Kombu parser checked task name, UUID, arguments
and routing key. It observed exactly six publications and no publication for the
sequential duplicate. Raw unrelated Redis metadata was not retained or printed.

The actual Celery consumer received each captured task ID once in this controlled
run and emitted completion; queue/unacked drained. This is not exactly-once safety.
Independent daemon events recorded six exact executor IDs and create/start/die/
destroy for each, plus real timeout kill. Native evidence included the real adapter's
shell-owned stage exits, bounded output completeness, trusted-record cardinality,
actual pre-start Docker settings and exact postexecution cleanup. Durable SQL/HTTP
rows were independently checked. Thirty-one bounded daemon events and twenty safe
native/accounting observations were retained, with no observer overflow.

| Case | Actual task ID | Actual submission ID | Executor ID (display prefix only) |
| --- | --- | --- | --- |
| Correct | 5e867886-98d7-413b-911b-2d2680563397 | 1535e032-6de6-4560-b132-580130708269 | 9796469ba78d |
| Wrong | c257114e-fae6-4cda-9ad5-0173fad320cb | 9c1e9078-54f3-4dc2-a909-6ebe20416f4c | f48dbeaca341 |
| Syntax | 1e3c346b-2a75-408f-aa03-66cae0b3dd5c | 60b93097-9ac4-4be7-ab27-b52ae0b9f7a9 | d3a6fc699ca2 |
| Forgery | 68431b3a-d269-478b-b094-0370709e5162 | d80df483-a427-4c97-a6b6-4fabee2b408d | 7df00916fb17 |
| Timeout | f4c55871-d47f-44fc-8db8-5451b23c4049 | a8cd8ebf-aedc-466f-b433-9d1cc732d8f8 | e9c85c573840 |
| Recovery | 03078a7b-9bd0-4344-afb9-3b8e06f33802 | ad9181c8-93db-4e8d-ad62-05410e6860f4 | 1756791fa90e |

Full IDs/job records are in encrypted receipts; display prefixes were never cleanup
selectors. Six exact terminal SQL rows had started/completed/worker evidence and
matching HTTP counters/awards. Native execution is not inferred solely from logs.

Per-RPC maximum observed elapsed ms: create 142.393, inspect-before-start 27.179,
attach 99.488, start 288.920, wait 16.518, kill 143.037, remove 54.743. SDK request
deadlines remain 10000ms; wait is 3000ms; joins 2000ms. Output wait used the remaining
5000/1000ms execution deadline, not a fresh additional budget. Trace end offsets
were 852.934/820.801/722.950/783.934/1504.399/786.014ms respectively; these are
diagnostic span endpoints, not HTTP latency or persisted runtime_ms.
All six result failure_phase/type were null and RPC error arrays empty. The intended
simulation timeout is not a Docker transport ReadTimeout. The historical unexplained
SDK ReadTimeout was not reproduced and remains unresolved. Profiling adds overhead;
this gate is not a production throughput/tail-latency benchmark.

## Idempotency and accounting actually observed

Sequential duplicate POST: HTTP 201, same accepted submission ID. Actual LPUSH
count and executor-create count did not increase; queue/unacked remained empty;
independent SQL state snapshot (submissions, profiles, progress, ledger, streaks,
badges) remained equal. This is a sequential check, not concurrent idempotency or
an unlimited-delay/exactly-once guarantee.

No production award/streak/quest/badge function was replaced or suppressed. Passive
call observation saw all four for both accepted native executions; their actual
effects were read before cleanup:

- Student A: xp=1, level=1, total_solved=1, easy_solved=1, medium/hard=0;
  profile total_attempts=5; current/longest streak=1.
- Normal fixture progress: completed, attempts=8. Timeout fixture: in_progress,
  attempts=2. Exactly six distinct submissions, excluding the duplicate POST.
- One XP ledger row: amount=1, reason=challenge_completion, linked to the initial
  correct submission/normal fixture. No zero-value row, duplicate challenge reward
  or quest bonus. Initial accepted award=1; the later accepted new-key award=0.
- One streak row with activity_type=submission, activity_count=2. Duplicate key
  added nothing; the genuinely new accepted job ran update_streak again even though
  award_xp returned already_awarded. Badge awards/quest and badge definitions=0.
- Student B remained xp/solved/attempts/streak=0, level=1, with empty progress,
  ledger, streak and awards. No student identity/email is reported.

Observed attempt mismatch matches current source: create_submission increments
progress on every new insert; the worker adds another progress increment for wrong/
compilation/timeout. award_xp increments profile attempts only for first completion,
while completed-challenge early return skips that profile update on a new accepted
submission. Hence progress 8+2=10, profile 5, submissions 6. This is not a correctness
assertion and was not altered. XP reconciliation with bonuses, badge JSON paths,
concurrent awards and transactional terminal/accounting boundaries are unverified.

## Commands, failed attempts and corrections

From repository root, using D/private R aliases from the historical section:

```powershell
.venv/Scripts/python.exe -B tools/database_gate.py --docker $D --mode preflight
.venv/Scripts/python.exe -B tools/queued_native_grading.py --docker $D --private-directory $R --authorize-local-queued-native
# Recover ONE exact run only after reviewing its private intent:
.venv/Scripts/python.exe -B tools/queued_native_grading.py --docker $D --private-directory $R --authorize-local-queued-native --recover-journal '<exact queued-native-intent path>'
```

The actual final driver ran 229 recorded Docker commands. Expected nonzero
not-found inspections are distinguished from failures; not all commands exited 0.
Build commands were actual `build --quiet -t <unique-api-tag> backend`, worker
`build --quiet -f worker/Dockerfile -t <unique-worker-tag> .` and executor
`build --quiet -t <unique-executor-tag> execution`. Safe argv/exit ledgers and detailed
observations/results remain encrypted outside Git, not copied as raw output here.

| Resumed attempt / private intent ID | Actual result |
| --- | --- |
| fce2a6d125594e14ae4067251dc9e527 | Exit 1, 79 assertions. Real correct POST201 and task queued; worker never started grading. Harness expected unprefixed capabilities, while Docker reported CAP_CHOWN/CAP_FOWNER/CAP_DAC_OVERRIDE. Initial cleanup removed the workspace but stopped on unrecognized `no such volume`; exact services/fixtures retained in journal. |
| Same intent, explicit recovery | Exit 0, 44 assertions. One queued/unacked=1/0 message discarded only with its owned broker; no grading retry. Exact two accounts/two challenges removed, all application/Auth rows zero. |
| c5e1d38521d4405f90262c316c5e2f7a | Exit 1, 146 assertions. Correct native accepted/1 XP, owner denial and duplicate-state check passed. Next POST201 failed LLEN snapshot assumption: a paused consumer's already-issued BRPOP can consume a message. Daemon observed two native jobs in total, including an executor during shutdown; only the first has retained complete verdict evidence. Do not label the incomplete wrong case a passed assertion. Exact cleanup succeeded. |
| 97f6f203b5f840369381fd6f73f6f0af | Exit 1, 107 assertions. Real correct publication captured, but monitor attempted JSON decoding of unrelated Redis binary metadata and set overflow. No worker/native execution. Pending owned broker and exact accounts/fixtures cleaned. |
| c57dc62eb93440108495053d7cbff258 | Final exit 0: 290 assertions / 19 HTTP cases / six publications, receipts, inspected executors and durable results; full exact cleanup. |

An exact journal-reserved unstarted, no-socket/no-credential diagnostic container
confirmed Docker's CAP_ names and was removed without consuming a task. Corrections
were test/harness only: capability-name normalization without adding capabilities;
exact absent-volume recognition without treating transport outages as absence;
actual acknowledged Redis MONITOR instead of paused-worker LLEN snapshots; decode
only canonical queue LPUSH before unrelated binary values. Focused regressions
cover these. No production job was automatically retried, no execution deadline
was raised, and no Docker/Supabase restart was used to obtain a passing result.

Final image observations: Python 3.12.15, asyncpg 0.32.0, Celery 5.6.3, Kombu 5.6.2,
Redis Python 8.1.0, Docker SDK 7.2.0, Pydantic 2.14.0/settings 2.15.0; API FastAPI
0.143.0, Uvicorn 0.54.0, python-jose 3.5.0, cryptography 50.0.2, HTTPX 0.28.1,
pytest 9.1.1. Actual executor runner hash was checked; prior image Icarus version
evidence remains separate. Dependencies/base tags remain unlocked observations,
not reproducible pinning or vulnerability certification.

## Focused verification and cleanup

| Check actually executed | Result / limits |
| --- | --- |
| Final actual API image pytest, network none/no services | Exit 0, 52 passed; two existing deprecation warnings; controlled fixtures, not live business proof |
| Actual worker dispatch/parser regressions | Exit 0, 8 / 9 methods; controlled DB/sandbox transport, separate from live native gate |
| New queued harness helper regressions | Final exit 0, 9 methods; production helper calls, controlled transport/intent fixtures, nonzero assertions |
| Host parser / database runner / generated-key Auth | Exit 0, 9 / 14 / 17 methods; no live account test substituted |
| Host diagnostics / delivery / exact-resource / CurrentUser DPAPI driver | Exit 0, 3 / 8 / 7 / 6 methods |
| App and node TypeScript noEmit | Both exit 0 |
| Static status contract | Exit 0, 6 checks |
| Independent all-four-journal cleanup inspection and READ ONLY database assertions | Exit 0; every exact resource absent; complete schema/permissions retained |
| Final AST / limited literal-secret / new-file whitespace / Git checks | Exit 0; four Python files parsed, five pending files scanned with zero candidates, no tracked/staged changes |
| Historical blocked-section checksum | Final exit 0; retained section SHA256 4f0bbc64e1f675c6a1b2519b051a77f4f9548f3908268795b14537601a9b29d6 unchanged |

No unrelated/full grading attack suite was repeated. Existing WASM and four-catalog
direct native evidence remains in the earlier reports, not new queued proof.
The initial read-only history comparison used Windows' default text encoding and
failed its heading lookup (exit 1). Explicit UTF-8 comparison passed without any
change to the historical section; this was a reporting-check error, not data loss
or a grading result.

Cleanup quiesced the API publisher then actual worker, both exit 0 in the final
run. Queued/unacked=0/0 was inspected after quiescence. Production Workspace recovery
verified no retained job/record (recovered=0) and exact executor absence; the stopped
worker was removed before deleting its exact bounded volume. Shared recovery then
removed owned broker/services before FK-ordered fixtures and supported Auth deletion.
Both final account DELETEs returned 200, followed by GET404. No prefix sweep/prune.

Independent verification afterward inspected every exact service/check container,
workspace/network/image tag from all four sealed intents: absent, including failed
attempt residue. All fourteen application tables/Auth users/identities=0, ledger and
full permissions intact; Auth audit history retained at **168** (initial 136).
Ten original Supabase container IDs/names/states, three volumes, four networks and
thirteen original image tags matched initial inventory. Only task-pulled unused
Redis dependency tags were removed; shared build caches were not pruned. No task-owned
Docker observer/launcher processes remain. Private snapshots/credentials, intents,
receipts and append-only provenance attestations remain protected outside Git.

Current intended pending files: the updated untracked report plus four new
harness/test files listed above, none staged. Existing tracked implementation,
PAUSE_CHECKPOINT, migrations/manifests and other reports are unchanged. No commit/push.
Docker/backend-security skills informed private intent, passive evidence, privilege
separation and exact recovery; they did not authorize a production-readiness claim.

## Remaining gates and next task

This sequential tested path is locally verified; it does NOT establish queued
concurrency, atomic worker claims/outbox/publication, concurrent idempotency,
exactly-once delivery, crash reconciliation, scoring/accounting correctness,
revision-safe admin publication, native coverage of arbitrary future templates,
snapshot restoration, LAN containment or production readiness. Power/remount tmpfs
recovery and historical SQL/SDK ReadTimeout causes remain unresolved. Supabase's
preexisting exited edge service and exposed LAN bindings were left unchanged.

Next separately scoped engineering task: review attempt-accounting consistency and
terminal-result/accounting transaction boundaries using these observed counts.
Define authoritative attempt semantics for new, duplicate and already-completed
submissions and test them before any algorithm/migration change. Alternatively
review/checkpoint this harness/report if requested. Do not start either automatically.
Stop after this report; all current changes remain uncommitted/unpushed.

---

## Historical blocked attempt — preserved below

# Queued native grading gate — blocked before fixture writes

Date: 2026-10-08, Asia/Calcutta. Disposable local environment only.
Repository: `C:\Users\tsush\Desktop\veriquest`, branch `main`.
Unchanged HEAD/remote main: `49b51f94cddb3848719212975f46169986d9efaa`.

## Outcome

**BLOCKED. End-to-end queued native grading was NOT executed.** The requested
zero-challenge-XP fixtures conflict with the actual retained database constraints.
The existing production acceptance accounting also unconditionally inserts the
challenge reward into a ledger that forbids zero amounts. Changing those constraints
or the accounting algorithm was expressly outside authorization.

Stopped dependent builds/resource provisioning/Auth signup/fixture/submission tests
before any application writes. No positive-reward substitute, temporary constraint
disablement, grant broadening, administrative runtime credential, fake grader result,
accounting bypass, migration, reset/restore, grading retry, timeout increase, commit,
push, deployment or firewall change was used to obtain a pass.

No temporary Redis/API/worker/executor, workspace volume or network was created.
There are no new HTTP submission/native verdicts or task/executor correlations.
Prior native and Redis/Celery delivery evidence remains valid historical evidence,
but their composition into successful queued grading remains unverified.

## Required reading and Git/environment recheck

Read the checkpoint, both native reports, Redis/Celery delivery report, database
runbook, private driver/resources/runner, current delivery/native harnesses,
API submission handler/service/config/startup, actual worker tasks/Celery settings,
production sandbox/workspace/diagnostics/profile/verdict and gamification code.
No applicable AGENTS.md was found in the repository or checked ancestors.
Current source and observed database metadata are authoritative.

Initial Git tree was clean. Branch main and both requested repository context and
origin were verified; read-only `git ls-remote origin refs/heads/main` returned the
baseline hash. No tracked source/report/checkpoint changes remain from this task.
Historical reports and applied migration files/manifests were preserved.

Docker context was `desktop-linux`, Linux engine 29.8.0. The exact existing local
Supabase stack was already available: ten containers, nine running and edge_runtime
already exited, matching the native reliability report's observation. No startup
or repair was necessary/performed. Do not interpret this as a full service-health
certificate; edge_runtime was left untouched.

## Verified preflight and private provenance

Executed the production runner's read-only preflight first:

```powershell
$D = 'C:\Users\tsush\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe'
.venv/Scripts/python.exe -B tools/database_gate.py --docker $D --mode preflight
```

Exit 0, actual result:

```json
{"mode":"preflight","state":"complete","role_count":3,"application_table_count":14,"auth_user_count":0,"writes":false}
```

The existing `DeliveryGate.provenance(True)` was separately executed in the normal
Windows CurrentUser context using the reviewed protected recovery directory, without
calling its write-capable delivery runner. Twelve provenance assertions passed:

- Exact DB/REST project and workdir labels, expected PostgreSQL host port 54322,
  exposed public/graphql_public schemas and current running target passed the
  production `verify_target` checks.
- DB mounted retained local volume `supabase_db_veriquest-local-test` at
  `/var/lib/postgresql/data`; both project labels, local driver/no custom options
  and creation time `2026-10-01T06:31:44Z` matched the reviewed provenance.
- Ledger was complete for 001/003/004/005; current canonical SQL and permission
  manifest checksums matched. Seed 002 remains deferred. Full structural, ownership,
  ACL/RLS/helper/trigger assertions passed inside READ ONLY transactions/ROLLBACK.
- All fourteen application tables had zero rows; Auth users/identities were zero;
  retained Auth audit count was 136. No account identities/row content was printed.
- Live Auth health returned HTTP 200. JWKS HTTP 200 published exactly one
  ES256/EC/P-256 key. The verified Auth configuration declared issuer exactly
  `http://127.0.0.1:54321/auth/v1`; no transport URL substitution changed that identity.
- Existing CurrentUser/SYSTEM-only protected directory ACL and DPAPI decryptability
  passed; runtime passwords remained distinct. This is private artifact verification,
  **not a newly executed API/worker restricted TCP login or real issued-token test**.
- Historical snapshot project/image/manifest and archive SHA256 matched; all archive
  blocks were readable using `pg_restore --list` / `--file=-`, without executing a
  restore. No restore-success claim is made.
- Current DB container identity still differs from the historical snapshot because
  of the previously reviewed restart. The existing verifier independently confirmed
  retained volume/schema/image/provenance and appended a separate encrypted rebind
  attestation. Historical snapshot pins, credentials and metadata were not overwritten
  or relaxed. This is the only new private recovery artifact from this task.

No passwords, DSNs, API keys, tokens, account identifiers, submitted HDL or private
bench content were emitted, placed in argv or saved in tracked files. The private
recovery directory remains outside Git/build contexts. No task account/fixture
intent was released to a writer, because the gate stopped before provisioning.

## Concrete blockers

### QNG-01: zero-reward challenge fixtures are forbidden by the actual schema

Source: `supabase/migrations/001_initial_schema.sql`, challenges definition,
constraint `xp_reward_positive` (line 97). Historical migration source says:

```sql
CHECK (xp_reward > 0)
```

This is not merely an assumption from migration source. A READ ONLY query of
`pg_constraint` and `pg_get_constraintdef` against the verified disposable database
returned the actual installed constraint:

```text
public.challenges / xp_reward_positive / CHECK ((xp_reward > 0))
```

The current applied 003/004/005 do not remove this constraint. A separate read-only
server evaluation of its zero predicate returned false. Consequently the required
fixture INSERT with xp_reward=0 cannot be applied under the current schema, regardless
of whether the authorized fixture operator or restricted API inserts it.

No INSERT was attempted to generate an avoidable failure; there is **no observed
23514 DML error** to report. Constraint rejection is established from actual installed
metadata and server predicate evaluation, not a fabricated execution trace.

This is a gate-request/schema incompatibility, not evidence that ordinary positive-
reward challenges fail. Its correction would require a separately reviewed forward
schema change; editing applied migration SQL/checksums would be prohibited.

### QNG-02: current acceptance accounting cannot record a zero reward

Source: `backend/app/gamification/xp.py:award_xp`, unconditional challenge_completion
INSERT into public.xp_transactions with amount=xp_amount. The actual installed
ledger constraint from the same READ ONLY metadata query is:

```text
public.xp_transactions / amount_non_zero / CHECK ((amount <> 0))
```

The server evaluated its zero predicate as false. If zero-reward challenges were
enabled independently, the existing award_xp path would still attempt to insert
amount=0 and conflict with that constraint. Idempotency checks only bypass awards
for previously completed/existing-ledger challenges; they do not enable fresh
zero-reward completion. No progress was preseeded to bypass that path.

`worker/tasks/hdl_task.py:_execute_hdl_submission` persists the evaluator's verdict
before opening the accepted accounting transaction and calls award_xp, update_streak,
check_quest_completion and check_badge_awards. Its exception handler subsequently
writes system_error / WORKER_ERROR. Thus a fresh zero-reward accepted simulation,
if made possible by a separate schema change alone, would risk a terminal override
by existing accounting failure. **This consequence is source analysis, NOT an
observed worker/native execution in this task.**

Do not change accounting, suppress its calls, pre-complete progress, drop constraints
or mutate runtime grants to force acceptance. This task explicitly forbids those
workarounds and requires stopping dependent checks on a blocking accounting defect.

## Live coverage status

| Requested condition | Actual result in this task |
| --- | --- |
| Correct queued native solution | Not executed; blocked before zero-reward fixture setup |
| Ordinary wrong logic | Not executed |
| Syntax error | Not executed |
| Forged ACCEPTED/counters | Not executed |
| Timeout or output overflow | Not executed |
| Real Redis route / task ID / worker receipt | Not executed; no temporary broker/worker |
| Independent native executor lifecycle/process/output/cleanup | Not executed; no executors |
| Durable owner-only polling / second-student denial | Not executed; no accounts/submissions |
| Sequential same-key nonpublication/nonexecution | Not executed |
| Restricted API/worker TCP/pool checks and actual image builds | Not executed; dependent gate stopped |
| Profiles/progress/XP/awards after actual submissions | No submissions; all actual application counts remained zero |

Actual submission HTTP case count: **0**. Native evaluations: **0**. Broker messages:
**0 created by this task**. Queued-native business assertions: **0 executed**, not
passing. No catalog fixture rejection is counted as grading proof, and no native
verdict was inferred from logs or composed from earlier separate milestones.

## Commands and focused checks actually executed

All commands used existing dependencies. No installations were performed.

| Command/check | Actual outcome / evidence type |
| --- | --- |
| Git branch / HEAD / status / origin | Exit 0; expected baseline, clean initial tree |
| `git ls-remote origin refs/heads/main` | Exit 0; remote equals baseline HEAD |
| `$D context show`, `$D info --format '{{.OSType}} {{.ServerVersion}}'`, `$D ps -a --format '{{.ID}} {{.Names}} {{.State}}'` | Exit 0; existing local engine/stack metadata, no service start |
| Production preflight command above | Exit 0; complete / 3 roles / 14 tables / Auth 0 |
| Python private call to `DeliveryGate.provenance(True)` | Exit 0; 12 assertions, full READ ONLY permissions/provenance/Auth metadata; private append-only attestation |
| Production `gate.psql` READ ONLY constraint metadata query | Exit 0; installed positive-reward and nonzero-ledger checks confirmed |
| Final independent READ ONLY counts/full assertions/manifest/predicate checks | Exit 0; all application/Auth counts zero, audit 136, 001/003/004/005 retained, both zero predicates false |
| `.venv/Scripts/python.exe -B tests/test_native_diagnostics.py` | Exit 0; 3 production trace methods, controlled faults, not native grading |
| `.venv/Scripts/python.exe -B tests/test_verdict_integrity.py` | Exit 0; 9 production parser/adapter methods plus subcases, mocked Docker/storage |
| `.venv/Scripts/python.exe -B tests/test_database_gate.py` | Exit 0; 14 production runner/manifest/refusal methods, no database writes |
| `.venv/Scripts/python.exe -B tests/test_auth_compatibility.py` | Exit 0; 17 generated-key authentication methods; not real Auth account/token integration |
| `git diff --check` before report | Exit 0; no tracked implementation diff |

Focused unit total: **43 methods** across the four suites, not 43 live workflows.
Failure assertions exit nonzero. Existing Starlette testclient deprecation warning
was observed; no dependency installation or upgrade was performed for it. Linux
workspace/worker suites require unavailable host Docker SDK/asyncpg/Celery/POSIX
dependencies and were not substituted with host success. Their previously recorded
actual-image results remain historical; no new packaged/native run is claimed.

The constraint query's SQL shape, passed privately through production psql stdin:

```sql
BEGIN TRANSACTION READ ONLY;
SET LOCAL statement_timeout='10s';
SELECT coalesce(json_agg(json_build_object(
  'table', c.conrelid::regclass::text,
  'name', c.conname,
  'definition', pg_get_constraintdef(c.oid)
)), '[]')
FROM pg_constraint c
WHERE c.conrelid IN ('public.challenges'::regclass,
                    'public.xp_transactions'::regclass)
  AND c.contype='c';
ROLLBACK;
```

Diagnostic command mistakes are retained, not counted as validation:
the first inline PowerShell quoting attempt failed before Python/SQL execution
with a parser error (exit 1). The corrected private command exited 0. Initial source
lookups used nonexistent `003_submission_statuses.sql` and `admin/schemas.py` paths
(rg diagnostics); corrected inventory found `003_status_contract.sql` and the admin
router. Those lookup errors did not execute SQL or affect database state.

## Cleanup and scope

No application fixtures/accounts, services, broker, native executor, network,
workspace volume, image build/tag or long-lived observer process was created.
Therefore there was no queued/unacked work owned by this task to drain/quiesce;
no claim is made from inspecting an unrelated broker. No resources were pruned,
deleted by name prefix, replaced or reset. Supabase/schema/runtime roles remained intact.

Independent final observations:

- All fourteen application tables still zero; Auth users and identities zero;
  Auth audit history remains 136, unchanged from initial provenance.
- Complete migration ledger/checksums and full production permission assertions
  remain intact. No schema/permission repair was attempted.
- Existing ten Supabase containers remain present, nine running and the preexisting
  edge_runtime exited. Three retained project volumes remain; no task volume exists.
- Current historical/private recovery artifacts were not overwritten. The new
  provenance attestation is encrypted outside Git/build contexts; snapshot restore
  remains untested.
- Unexecuted local harness drafts were removed after discovering the gate blocker.
  They created no external resource and are not delivered as a validated runner.
  Existing implementation and historical reports were not discarded or changed.

Only intended Git change: this new report,
`docs/handoff/QUEUED_NATIVE_GRADING_REPORT.md` (untracked/unstaged). Branch/HEAD
remain baseline. Nothing committed or pushed. Docker/backend-security skills informed
exact target/provenance checks, nonsecret evidence and stopping before incompatible
writes rather than adding a privileged or synthetic workaround.

## Decision needed before another live gate

Smallest way to test the existing production accounting path without changing it:
**explicitly authorize small positive-reward disposable fixtures** (for example 1 XP)
under the current schema. Record actual profile/progress/ledger/attempt effects,
including defects, and clean only exact disposable rows/accounts afterward. This is
a revision to the zero-reward constraint of the present request, so it was not assumed.
Unrelated quest/badge definitions must remain absent. Do not certify scoring from
one reward or from fixture cleanup.

Alternatively, if zero-reward authenticated challenges are genuinely required,
separately authorize a reviewed zero-reward schema/accounting compatibility design
and implementation with forward migration/recovery/testing. Changing the challenge
constraint alone would leave the ledger/award_xp conflict. Do not edit applied SQL
checksums or bypass accounting. That is outside this queued-native task.

Only after resolving that decision: reverify this same target/provenance, prepare
and review a private recoverable exact-resource harness, then execute the actual
API -> Redis -> Celery -> native cases with independent Docker/process evidence,
owner-only durable results, sequential idempotency and exact cleanup. Do not resume
write-capable steps automatically from this report.

Still separate/unverified: queued concurrency, atomic claims/outbox/exactly-once,
job crash recovery, accounting correctness, revision-safe admin publication, LAN
containment, snapshot restoration, historical SQL/SDK timeout attribution and
production readiness. Existing Supabase port exposure/firewall settings and the
already-exited edge service were left unchanged. Stop after this blocked report.
