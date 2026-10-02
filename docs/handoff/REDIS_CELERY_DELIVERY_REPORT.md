# Real API → Redis → Celery delivery gate

Date: 2026-10-02, Asia/Calcutta. Disposable local target only.
Baseline/current HEAD: `bb8fdfc570d37a3c99fe3b9713673a3ed350c2d0`, branch `main`.

## Outcome and scope

**The final real delivery gate passed: exit 0, 152 assertions, 12 recorded API
HTTP cases, three actual broker messages and actual Celery worker receipts.**
An earlier complete corrected run also passed with 152 assertions. Repeated runs
are not additional unique coverage. There were three failed harness attempts and
one explicit recovery, recorded below rather than counted as passing runs.

The actual Dockerfiles packaged the API and worker. Their default application
commands ran with production authentication, pools, limiter, publisher, task
registration and worker functions. No HTTP/DB/broker dependency override or
synthetic receipt was used in the live gate. Redis was a real isolated temporary
service. Accounts signed up and signed in through actual local Supabase Auth.

Verified: successful publication, canonical queue routing, real worker receipt,
durable evaluator-configuration failure, owner polling, sequential idempotent
nonpublication, queued administrator validation failure, definite broker outage
failure and subsequent delivery after broker restoration. XP and scored completion
remained zero. **No native HDL simulation or successful grading was attempted.**
This is not atomic delivery, exactly-once execution, job crash recovery, accounting
certification, successful native administrator validation or production readiness.

No migration, seed 002, grant change, reset, administrative runtime fallback,
firewall change, commit, push or deployment occurred. Existing Supabase was retained.

## Source/checkpoint and retained target verification

Read the applicable instruction locations (no AGENTS.md found), PAUSE_CHECKPOINT,
database runbook/live/follow-up reports, startup/dispatch remediation report,
current publisher, submission/admin handlers/services, runtime pool, worker tasks,
profiles, Dockerfiles, exclusions and Compose. Historical reports are preserved.

Initial Git tree was clean. HEAD/message:
`bb8fdfc570d37a3c99fe3b9713673a3ed350c2d0` —
`Harden backend dispatch and verify local database permissions`.
Origin is `https://github.com/tsushanth12-afk/veriquest.git`.
Read-only `git ls-remote origin refs/heads/main` returned the same hash.

Docker context `desktop-linux`; Linux engine 29.8.0, x86_64. Before resources and
again immediately before first Auth/database writes, the harness checked:

- Exact named DB/REST/Auth project/workdir labels: veriquest-local-test,
  `C:\Users\tsush\Desktop\veriquest-local-test`; gateway credentials came only
  from the verified local project.
- DB host port 54322, Auth/API 54321, exposed schemas public/graphql_public.
- Actual DB mount is volume `supabase_db_veriquest-local-test` at
  /var/lib/postgresql/data. Its local-driver metadata, both project labels,
  absence of custom volume options and creation time `2026-10-01T06:31:44Z` match
  the verified retained volume.
- Production preflight: complete, 3 roles, 14 application tables, Auth users 0.
  Full production structural/ownership/ACL/RLS/helper/trigger assertions passed
  in READ ONLY transactions. All 14 application tables and Auth identities were 0.
- Applied 001/003/004/005 and their canonical manifest checksums remain unchanged;
  002 is deferred. In particular 004 is
  `416a96975a680b6be2909496cc2acae4ed711926cb7e4e21dc376055347d38bd`,
  and 005 is `998ec791149fbba706f85161b398db298b5fcf44e93f265fe75175413d780af6`.
- Auth health 200, JWKS 200, one ES256/EC/P-256 key; declared issuer exactly
  `http://127.0.0.1:54321/auth/v1`. Production verification subsequently accepted
  real issued tokens on authenticated HTTP operations. Container JWKS/PG transport
  used host.docker.internal; issuer identity did not change.

### Restarted identity pins and private provenance

`DeliveryGate.provenance()` in
[tools/redis_celery_delivery.py](C:/Users/tsush/Desktop/veriquest/tools/redis_celery_delivery.py)
rechecks the protected CurrentUser/SYSTEM directory DACL, DPAPI decryptability,
original snapshot project/image/manifest and archive SHA256, then reads all archive
blocks with pg_restore --list / --file=- without restoring/executing SQL. Retained
runtime passwords are distinct and were used for actual restricted TCP/pool checks.

The old DB container ID differs after restart. A **separate encrypted append-only
delivery-rebind attestation** records old/new IDs, unchanged image, verified retained
volume metadata, original snapshot ciphertext hash, manifest and fresh read-only
state. Historical snapshot metadata, credentials and original strict snapshot
validation are not overwritten or relaxed. New delivery intents bind the independently
verified current container ID. This is checked restart provenance, not a tested restore.

Private artifacts remain outside Git/build contexts under the existing recovery
directory. Windows resolves its alias to:

```text
C:\Users\tsush\AppData\Local\Packages\OpenAI.Codex_2p2nqsd0c76g0\LocalCache\Local\VeriQuest\recovery\live-ee7fe07f5535490f89728348b707c83d
```

No credentials, account identifiers, emails, passwords, source or tokens are in
this report. Task/submission IDs below are expressly scoped correlation evidence.

## Small production correction

[worker/tasks/hdl_task.py](C:/Users/tsush/Desktop/veriquest/worker/tasks/hdl_task.py:78),
`_execute_hdl_submission()` previously saved missing testbench data as system_error,
and allowed whitespace-only data through its initial check. It now rejects missing,
empty, whitespace-only or non-string data before parsing profiles/constructing
DockerSandbox, and saves `evaluator_not_configured / MISSING_EVALUATOR` with completion
time. Existing invalid-profile behavior remains fail-closed.

[tests/test_worker_dispatch.py](C:/Users/tsush/Desktop/veriquest/tests/test_worker_dispatch.py:125)
adds actual production-worker function coverage for absent secrets, empty, whitespace
and null benches, asserting the persisted classification, no sandbox construction and
pool cleanup. These focused cases use controlled DB objects; the separate live gate
proves real database persistence and worker delivery for deliberately empty data.

No publisher, authentication verifier, permission, XP, sandbox, grading protocol,
Dockerfile, Compose or applied-migration implementation was changed.

## Harness and security boundaries

New opt-in driver:
[tools/redis_celery_delivery.py](C:/Users/tsush/Desktop/veriquest/tools/redis_celery_delivery.py).
Key functions: `provenance`, `new_intent`, `packaged_checks`, `service`, `message`,
`receipt`, `run_live`, `cleanup`, `execute`, `decode_message`, `validate_intent`.
New isolated fixture/recovery probe:
[tests/redis_celery_delivery_probe.py](C:/Users/tsush/Desktop/veriquest/tests/redis_celery_delivery_probe.py),
`run()`.

Before releasing writes, CurrentUser DPAPI exclusive-create/fsync/readback seals
immutable exact account emails/metadata markers, challenge slugs, fixture IDs,
idempotency keys, container/network names, test names and application image tags.
The shared exact-resource resolver recovers Auth/API-generated IDs by equality and
checks markers. No prefix deletion or unknown-target fallback is used.

The resource-plan format reserves three account keys/four slugs, but this gate
creates **only two accounts** (one student and one DB-provisioned disposable admin)
and **two challenges**. Unused reservations are not created. The admin also serves
as the different identity for owner-polling denial; no second student was needed.

Secrets are acquired privately and passed through captured binary stdin. The API
receives only its vq_api DSN; the worker only vq_worker. Neither receives operator
passwords, admin API keys or its counterpart's credential. Credentials become
process-local environment values only after inspected startup, not Docker Env
configuration/argv or tracked/plaintext files. A separate short-lived fixture probe
receives authorized supabase_admin setup authority; it is NOT the API/worker service.
It verifies that SQL identity and uses real asyncpg. Passwords and Auth tokens remain
in memory. No host/global Python installation was performed.

`packaged_checks()` compares every packaged backend app source hash (29 files in
API; 38 backend/worker files in worker) with current source, using canonical-LF
hashes. API and worker services have **no production source bind mounts**. The
probe/test mounts are read-only, and tests import production packaged functions.
The service launcher only supplies private environment then execs the actual
image's default command, not a replacement application or fake worker.

Each live container was actually inspected for read-only root filesystem, ALL
capabilities dropped, no-new-privileges, 512MiB memory limit, pids 64, no privileged
mode, no persistent volume and no Docker socket. Service flags also limit CPU to 1
and use bounded tmpfs/log files. Redis runs as uid/gid 65534 with persistence disabled
and tmpfs /data; it has no host port. Worker/probes have no host ports. API port is
loopback-only; final run **127.0.0.1:50978 → 8000**.

Actual network inspection found only this run's Redis/API/worker in its unique
labelled bridge. That bridge allows necessary host Supabase connectivity; it is not
network-none/outbound-blocked isolation. Registration/unit probes use network none.
No full Compose stack or grading executor was started.

## Actual HTTP results — final run

These are actual production API responses, not mocked expectations. Internal health,
readiness, polling-loop requests, Auth requests and cleanup verification are additional
checks outside the 12-entry recorded API case array. The 152 assertion count includes
environment/isolation/resource assertions; it is not 152 separate business workflows.

| Case | HTTP | Observed/asserted result |
| --- | --- | --- |
| Admin creates submission fixture | 201 | Server-returned real challenge ID, draft |
| Admin creates validation fixture | 201 | Server-returned real challenge ID, draft |
| Student submits | 201 | Real submission ID, queued; actual Redis envelope captured |
| Owner polls completed worker result | 200 | evaluator_not_configured, MISSING_EVALUATOR, completed, zero XP |
| Different identity polls same submission | 404 | NOT_FOUND |
| Sequential same idempotency key repeated | 201 | Same submission ID and terminal status; no queued/unacked message added |
| Admin requests validation | 202 | validating, actual task ID equal to Redis wire ID |
| Admin reads finalized validation | 200 | validation_failed, unpublished, validated_at null |
| Student submits while only temporary Redis is stopped | 503 | DISPATCH_FAILED; safe pollable submission ID |
| Owner polls that failure | 200 | system_error / DISPATCH_FAILED, completed, no worker/start evidence, zero XP |
| Student submits a new key after Redis restoration | 201 | New real submission ID, queued, actual wire message |
| Owner polls restored delivery | 200 | evaluator_not_configured / MISSING_EVALUATOR, completed, zero XP |

Fixture publication was deliberately performed by authorized setup SQL, **not native
validation**. Its private bench is empty. The separate unpublished validation fixture
has nonblank solution/bench but `timeout_ms=0`; API prechecks allow queue publication,
and production worker profile validation rejects it before DockerSandbox. Those
failures reach their intended conditions rather than failing earlier on authentication.

### Broker/worker correlation — final run

| Canonical task, queue hdl_execution | Real task ID | Exact submission row / outcome |
| --- | --- | --- |
| execute_hdl_submission | dce00b66-db92-422f-856d-05ce6158f3ff | 69e105e1-b530-4fc9-b44b-ca0ec898e75f; evaluator_not_configured |
| validate_challenge_task | cab0eb53-4446-4225-85c6-302b9c4c8f36 | Corresponding unpublished challenge finalized validation_failed |
| execute_hdl_submission after restoration | d7361517-58c5-4310-8da5-5838dd00f751 | 76fffdbf-3b88-4ab4-9342-84386d959271; evaluator_not_configured |

The harness inspects real Kombu JSON/base64 envelope task name, arguments, generated
UUID and routing key. Worker is not yet started for the first publication; it is
paused only after draining earlier work for later message inspections. Inspection
does not pop/inject messages or call task functions. The unmodified actual Celery
consumer then reports each captured ID received, once in this controlled run's
bounded logs. Queue LLEN and unacked HLEN become zero after each execution. Durable
rows are independently read through real SQL and owner HTTP, not inferred from logs.
One observed receipt per ID is **not an exactly-once guarantee**.

There are exactly three submission rows before cleanup. The two delivered rows have
started_at/worker_id evidence and terminal MISSING_EVALUATOR. The failed-publication
row `9bb74620-8e09-4bc4-8205-ee7ca9b3fa97` has neither start nor worker evidence.
All have zero tests and XP. Profiles have zero XP/solved counts, no completed progress,
and no XP transactions. Existing initial submission attempt updates remain unchanged;
this gate does not certify attempt accounting during infrastructure failures.

Admin audit persists challenge_validation_requested / {status: validating}, then
the existing legacy action name **challenge_validated** with
`{result: execution_error, status: validation_failed}`. That action name alone does
not mean successful validation; actual state/details are asserted.

### Outage classification

Only the temporary Redis container was stopped after drain, with the worker paused.
Real HTTP failure elapsed **4313ms** in the final run, including rate-limit fallback
and publisher work. Pre-send connection failure is definitely nonpublished according
to the production phase boundary. After restart the broker had no message for that
failed job; the row remained terminal, and a different key delivered normally.

No ambiguous post-send failure was induced. `DISPATCH_UNCERTAIN` and conditional
non-overwrite behavior retain focused controlled-transport regression coverage only.
This outage is not a proof for network partitions, lost acknowledgements, broker
data loss, total DNS deadlines or distributed delivery guarantees.

## Commands, execution and failed attempts

Working directory `C:\Users\tsush\Desktop\veriquest`. Safe abbreviations:

```powershell
$D = 'C:\Users\tsush\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe'
$R = 'C:\Users\tsush\AppData\Local\VeriQuest\recovery\live-ee7fe07f5535490f89728348b707c83d'
.venv/Scripts/python.exe -B tools/redis_celery_delivery.py --docker $D --private-directory $R --authorize-local-delivery-test
# Recovery of ONE exact journal only, not automatic replay of a directory:
.venv/Scripts/python.exe -B tools/redis_celery_delivery.py --docker $D --private-directory $R --authorize-local-delivery-test --recover-journal '<exact delivery-intent file from the run>'
```

Without explicit authorization the opt-in driver exits 2. Fresh live mode requires
the empty application/Auth baseline; recovery uses the same pinned target/manifest,
quiesces exact labelled services, discards only its owned broker, then resolves/deletes
only exact journal resources. If target/container/manifest/markers drift, stop rather
than bypass identity checks. Retain journals until independent cleanup confirmation.

| Command/check | Actual result |
| --- | --- |
| Git status/branch/log/origin; read-only ls-remote | 0; expected baseline/origin, remote main equal |
| Docker context show / info metadata | 0; desktop-linux / Linux 29.8.0 x86_64 |
| Production database_gate.py --docker $D --mode preflight | 0; complete, 3 roles, 14 tables, Auth 0 |
| Delivery driver attempt 1 | 1; 29 assertions before stop; missing verdict-test fixture mounts; no accounts; cleanup complete |
| Delivery driver attempt 2 | 1; 44 assertions before stop; probe ModuleNotFoundError; no accounts; initial cleanup probe also failed, exact network/tags retained for recovery |
| Same driver --recover-journal delivery-intent-3501690de77448069f183a63cb5de505.dpapi | 0; 33 cleanup/provenance assertions; zero accounts/challenges resolved, exact residual resources removed |
| Delivery driver attempt 3 | 1; 147 assertions and all 12 HTTP cases; final audit query used nonexistent event name; exact accounts/fixtures/service cleanup complete |
| Delivery driver attempt 4 | 0; 152 assertions / 12 cases; all three real receipts and persisted outcomes |
| Final delivery driver after fail-closed inspection/version recording | 0; 152 assertions / 12 cases; full final-source run |
| Actual builds: $D build --quiet -t vq-delivery-api:<sealed-run-nonce> backend; worker equivalent -f worker/Dockerfile . | 0 in every run; no substitute Dockerfiles |
| Actual image source hash probes | 0; 29 API app / 38 worker+backend Python files match |
| Actual API image python -B -m pytest -p no:cacheprovider -q tests, network none | 0; 52 passed, 2 existing deprecation warnings |
| Actual worker image python -B /app/tests/test.py, mounted test_worker_dispatch.py | 0; 8 methods passed; includes four missing/empty data subcases |
| Actual worker image same for test_verdict_integrity.py and read-only fixture/catalog/seed mounts | Final 0; 9 methods passed; production parser, controlled Docker transport, no simulator |
| .venv/Scripts/python.exe -B tests/test_redis_celery_delivery.py | 0; final 8 methods passed |
| .venv/Scripts/python.exe -B tests/test_database_live_resources.py | 0; 7 methods passed |
| .venv/Scripts/python.exe -B tests/test_database_gate.py | 0; 14 methods passed; expected refusal messages are negative assertions |
| .venv/Scripts/python.exe -B tests/test_auth_compatibility.py | 0; 17 generated-key methods passed; existing Starlette warning |
| .venv/Scripts/python.exe -B tests/test_database_live_driver.py | Sandbox attempt: one DPAPI error among 6 methods; rerun in authorized Windows CurrentUser context: 0, all 6 passed |
| node tests/status_contract_consistency.test.mjs | 0; 6 static source checks |
| AST parse / limited literal credential scan | 0; five changed/new Python files parse; zero private-key/token/literal password-DSN pattern hits; not exhaustive certification |
| git diff --check | 0; tracked diff, LF/CRLF informational warnings only |
| Read-only new-file trailing-whitespace inventory | 0; all four new files checked, no trailing whitespace |
| Independent READ ONLY counts/full assertions and exact Docker inventory/cleanup receipt | 0; final counts/resources below |
| $D image rm redis:7-alpine | 0; only the task-pulled unused dependency tag, no force/prune, after checking no remaining container references it |

Full safe argv/exit ledgers and results are retained in encrypted delivery receipts;
final live receipt records 146 Docker invocations, including inspections/polls.
Expected nonzero inspections of absent resources are distinguished from failures.
The additional no-index comparison of the new report against NUL exited 1 for
file differences, with no whitespace-error diagnostic; it is not reported as an
exit-0 regression check. The final driver now fails closed on daemon/inspection outages rather than treating
arbitrary inspection errors as resource absence. No secret-bearing stdout/diagnostic
stream was published. Setup/cleanup SQL used real bounded asyncpg or verified psql
stdin; passwords/DSNs/keys/tokens were absent from argv.

Harness corrections were limited to read-only verdict fixture mounts, adding /app
to the fixture probe's packaged import path, querying actual challenge_validated
audit action, and fail-closed inspection tests. The first two failed runs stopped
before Auth writes. Attempt 3's audit failure is retained as a failed assertion,
not retroactively labelled a passing gate. No production grant/status workaround
was used to satisfy it.

The new unit suite calls the production harness protocol/intent methods and asserts
failed expectations raise/exit nonzero. Persistence failure does not release an intent;
daemon failure does not become absence. Mocked durability/transport helper tests are
not real delivery evidence. Actual CurrentUser DPAPI and live HTTP/SQL/Redis/Celery
results are separate evidence.

### Resolved final image dependencies

API `sha256:8bc0bd4a19f7decbb53e303c9d76997d8a477770c3d1f2f3918a74d5732d7764`;
worker `sha256:c75f1db65f64a8f0cef17af3f4a5f72303b3fcb495e94b88a14e5520ecdb7950`.
Both Python 3.12.15; asyncpg 0.31.0, Celery 5.6.3, Kombu 5.6.2, Redis Python 8.1.0,
Docker Python 7.2.0, Pydantic 2.13.5/settings 2.15.0. API FastAPI 0.142.2,
Uvicorn 0.54.0, python-jose 3.5.0, cryptography 50.0.2, HTTPX 0.28.1,
pytest 9.1.1. Actual temporary Redis server **7.4.11**. Requirements/base tags remain
unlocked; these are observed build versions, not reproducible dependency pinning.

## Cleanup and independent final verification

After the final queue/unacked drain, the API publisher was stopped first, then the
actual worker warm-stopped; both exit codes 0. Only exact nonce-labelled containers
were removed. The broker was removed before fixture deletion, so no task-owned queue
consumer/publisher or message store could act on deleted fixtures. On failure the
same recovery path reports pending/unknown queue state and retains intent, rather
than claiming distributed quiescence.

Shared `resources.cleanup()` performs bounded, exact-key/marker lookup, parent-row
locks, outside-reference refusal and one FK-ordered transaction: audit/XP/submissions
before challenges/other definitions. Supported Auth administration then deletes only
the two resolved disposable IDs. Each deletion returned **200**, followed by **404**
absence. Profile-linked data cascades under the installed schema. No prefix sweep,
reset or platform audit purge was used.

Independent verification after the final harness confirmed:

- Zero rows in all 14 application tables, Auth users 0, identities 0.
- Applied ledger/checksums, roles, full permission assertions retained.
- All ten existing project-labelled Supabase containers still running.
- No task-labelled container/network; all five intent plans' API/worker image tags
  absent. No persistent test volume was created; tmpfs vanished with containers.
- The exact unused Redis dependency tag pulled for this task was separately removed
  after verifying no container reference; no unrelated image pruning. Shared Docker
  build/base caches may remain.
- Snapshot binding unchanged; encrypted credentials, five immutable delivery intents,
  separate restart attestations, receipts and independent cleanup evidence retained
  under the verified private ACL. The recovered failed run was not erased.
- Auth audit history retained: initial 112, final **136**, with normal task-created
  Auth event appends. Zero accounts does not mean platform logs were deleted.

The independent cleanup probe exited 0 and stored a DPAPI receipt. No temporary
host test service or attached Docker launcher remains. Existing Supabase volume,
schema, runtime roles, signing settings and historical artifacts were not replaced.

Final read-only private verification compared all nine restart attestations with
the historical snapshot's current ciphertext SHA256: unchanged since the first
delivery recheck; every attestation manifest and protected directory ACL also passed.

Existing gateway/PG/Studio/Mail ports 54321/54322/54323/54324 still publish on
**0.0.0.0 and ::**. No firewall/network settings changed. Prior reported broad
Docker inbound allowance is not newly certified here; LAN containment remains
explicitly unresolved. Temporary API was loopback-only and Redis/worker unexposed.

## Remaining gates and evidence limits

Verified by execution: real Auth-to-API lifespan, restricted TCP pools, actual Redis
wire publication/routing, actual worker receipt, exact terminal DB rows/audit,
owner denial, sequential nonpublication, stopped-broker definite failure/restoration,
zero awards and exact cleanup. Source plus mocked worker regression establishes the
pre-sandbox branches; no simulator launch was instrumented or executed.

Still unverified/outside this task:

1. Native simulator/container workspace, mount/UID, isolation, execution/cleanup and
   successful grading. No Docker socket was present in API or worker; a grading
   executor was deliberately absent.
2. XP/attempt/quest/badge correctness, concurrent awards and reconciliation. Initial
   failed-dispatch attempts are not corrected here.
3. DB/broker atomicity, outbox, concurrent idempotency, atomic worker claim,
   exactly-once behavior, unknown post-send outcomes and job crash recovery.
4. Revision/task-bound administrator lifecycle and successful native validation.
   Test-setup publication is not validation evidence.
5. Full snapshot restore rehearsal; original unexplained permission-harness timeout;
   host/Docker/power loss, unknown in-flight Auth requests, interrupted recovery,
   concurrent recovery controllers and other untested distributed crash windows.
   The explicit recovery here exercised a known pre-account probe failure, not
   in-flight job recovery. Journals support exact later discovery, not cancellation.
6. Existing LAN exposure, TLS/hosted/deployed configuration and production readiness.

The delivery driver relies on the reviewed private Windows directory/DPAPI profile
and same current DB binding. A future restart or launcher/profile drift requires
fresh independent provenance review, not editing snapshot pins. It normally removes
its application image tags; upstream/base dependency cache handling is separately
reviewed as done above. Do not reset, auto-restore or restart a new milestone from
this report.

## Changed files and final Git state

Modified tracked files:

- worker/tasks/hdl_task.py — five-line missing/empty evaluator preflight/status fix.
- tests/test_worker_dispatch.py — 15-line focused regression addition.

New files:

- tools/redis_celery_delivery.py — opt-in private real delivery/recovery driver.
- tests/redis_celery_delivery_probe.py — actual packaged SQL role/fixture/state/cleanup probe.
- tests/test_redis_celery_delivery.py — eight focused production-helper regressions.
- docs/handoff/REDIS_CELERY_DELIVERY_REPORT.md — this report.

Tracked implementation diff: 18 insertions, 2 deletions. Existing reports,
PAUSE_CHECKPOINT, migration SQL/manifest/policy, authentication, permissions,
configuration, grading protocols and accounting are unchanged. New private artifacts
are outside Git/build contexts; no dependency/cache/env artifact appears in status.

Final branch/HEAD/origin remain baseline and remote main above. **Nothing staged,
committed or pushed**: two tracked modifications and four untracked intended files.
The backend-security-coder skill informed independent target provenance, restricted
credential separation, durable exact intent, fail-closed inspection and scoped cleanup.

Stop after this milestone. Real delivery/configuration failure is locally verified;
the next engineering gate requires separate authorization and must not be described
as production readiness.
