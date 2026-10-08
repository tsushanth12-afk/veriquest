# Native sandbox reliability/resource follow-up

Date: 2026-10-08, Asia/Calcutta. Local Docker Desktop Linux only.
Repository: `C:\Users\tsush\Desktop\veriquest`, branch main, unchanged HEAD
`6ef8c478115b9961dd78fc1d6da51e6d8c68dc1f`.

## Outcome

**The corrected bounded follow-up passed, exit 0.** It ran the full production
native gate (848 assertions, 36 recorded cases, 32 independently inspected native
executors, 40 matching packaged Python source hashes), then a fixed 42-case
reliability/resource matrix. All four catalog correct solutions remained accepted
through actual Icarus. All tested exhaustion conditions failed closed and ordinary
recovery jobs subsequently passed. One initial attempt failed an ineffective memory
fixture; that failure and its observed acceptance are retained below, not relabeled.

**The historical real Docker SDK ReadTimeout was NOT reproduced. Its precise
original RPC and cause remain unresolved.** No execution/RPC deadline was increased,
no production grading retry was added, and the agent did not restart Docker or any
Supabase service to obtain passing results. New safe diagnostics can distinguish
the relevant RPCs on a future occurrence; later success is not a causal diagnosis.

No database connection/query, account, migration, grant, API/Redis/Celery service,
XP/job-lifecycle change, firewall change, reset, commit, push or deployment occurred.
This is direct packaged native evaluation, not end-to-end queued grading or
production readiness.

## Initial ownership/environment gate

Read project instructions (no applicable AGENTS.md found), PAUSE_CHECKPOINT,
NATIVE_SANDBOX_WORKSPACE_REPORT, production sandbox/workspace/runner/profile/parser,
Docker/Compose packaging, native harness and relevant tests. Historical reports
and the checkpoint are preserved. Initial pending inventory was the expected eight
tracked modifications and seven native-workspace untracked files, none staged.

Unlike the preceding read-only check, Docker responded this time: context
desktop-linux, Linux engine 29.8.0. No service start was performed. Read-only
inventory compared each of the twelve retained native resource plans with actual
container names, volume names and image tags: all exact planned resources absent;
no sandbox.job/native-gate-labelled container. No uncertain resource was deleted.

Initial unrelated inventory: ten existing Supabase containers, **nine running and
edge_runtime exited**; three Supabase volumes, four networks, thirteen original
image tags. The existing stopped edge container was not repaired/restarted. No
current application schema/role/data claim is made from Docker metadata.

## Corrections and design

### Safe per-RPC diagnostics

New `worker/execution/diagnostics.py:RpcTrace` is used by DockerSandbox._execute_docker
and Workspace operations. It records at most 96 events per evaluation, with fixed
phase vocabulary, relative monotonic start/elapsed ms, configured deadline ms,
outcome and a fixed error category. Thread-safe event retention is bounded;
truncation is explicit. No call arguments, responses, source, bench, nonce,
credentials, arbitrary exception messages or traceback are stored in these events.
Nested cleanup spans preserve the first specific failing RPC rather than replacing
remove with a generic cleanup failure. Safe events travel in raw adapter metadata;
the existing public verdict parser does not expose them as compiler diagnostics.

Instrumented phases include volume/worker/image inspection, create, inspection
before start, attach, start, output collection/wait, inspection after output/kill,
kill, container wait, stream close, collector join, exact cleanup inspection,
remove/removal verification and workspace filesystem spans. Invalid vocabulary
fails; exception messages are never copied. Docker-client bootstrap/ping retains
its existing generic failure log and is not part of the per-execution trace.

Unchanged deadlines: Docker SDK requests 10000ms; container wait 3000ms; collector
join 2000ms; execution 1..5000ms, starting before start RPC. Output wait records
the remaining execution deadline. Filesystem spans/stream close have null explicit
deadline rather than a fabricated bound. These are not an end-to-end five-second
SLA; total duration includes setup, RPC waits and cleanup. No deadline-based
automatic retry or daemon restart was introduced.

`failure_phase` now uses the specific trace failure; `failure_type` is a safe
category rather than an arbitrary exception string. Cleanup failures still retain
exact records and force system_error / SANDBOX_CLEANUP_FAILED. The trusted token,
compile/simulation/container evidence, complete bounded capture and strict trusted
summary parsing are preserved. There is no synthetic acceptance path.

### Aggregate workspace storage and admission

The prior named disk volume plus per-file RLIMIT_FSIZE was **not an aggregate
quota**. Normal restricted student HDL cannot call file/host tasks. Ordinary
artifacts are two inputs, sim.vvp, compile/simulation exits, compiler temporary
files in /tmp, and now two small kernel-evidence files. Trusted benches can use
file tasks, and simulator/compiler faults may produce additional artifacts/core
files. A 64MiB limit on each file does not bound many files, concurrent jobs,
abandoned jobs or growing job metadata.

Smallest chosen hard bound: the existing named-volume/subpath architecture now
requires **exact local-driver tmpfs options**:

```text
type=tmpfs
device=tmpfs
o=size=134217728,mode=0700
```

This is a kernel-enforced **128MiB aggregate workspace volume**, not an arbitrary
host mount, new privileged helper or student-controlled configuration. Compose and
the opt-in driver use those same options. Workspace.__init__ checks exact driver
options, actual worker mount identity and actual statvfs capacity. Unbounded plain
volumes, alternate devices/options and mismatched capacity fail closed. No existing
volume is replaced, pruned or reformatted automatically. An old unbounded volume
at the configured name requires separate reviewed operator action, not fallback.

Workspace.reserve uses a Linux flock admission lock, bounded 500ms acquisition,
and permits at most **four outstanding job records per shared volume**, including
pending-cleanup/interrupted jobs. It requires 512KiB free before releasing a new
intent. Rejection happens before new job/container creation. The lock file remains
as bounded infrastructure metadata, not a job residue. Cleanup releases a slot only
after exact resource removal. This caps metadata/directory accumulation; it is not
a scheduler/outbox/job-recovery redesign. More worker processes do not grant more
volume slots. Dedicated capacity planning is needed for other deployment sizes.

Job UUID paths, root/input/output ownership/modes, no-symlink checks, exact RO input
and RW output subpaths, non-root executor, dropped capabilities, network none,
read-only root, no-new-privileges, /tmp 64MiB and validated CPU/memory/PID/output/time
limits are unchanged. Per-file 64MiB still applies separately. Worker socket access
remains privileged infrastructure authority; executors never get the socket.

**Trade-off:** workspace storage now consumes bounded RAM, not persistent grading
disk. Job JSON records still survive caller interruption while the mount exists
(retested), but tmpfs/fsync is NOT power-loss/remount-durable. Host test intents and
Docker resource labels persist separately. Whole-host/daemon/volume-unmount recovery
is not certified. Do not describe this as crash-safe job recovery. Student output
retention, SDK frame/socket buffering, worker RSS, /tmp, images/build caches and
multiple deployment volumes are separate resource budgets.

### Resource evidence and classification

The fixed image-owned run.sh records kernel pids.events:max and
memory.events:oom_kill using shell builtins, even when another PID cannot fork.
Workspace.stage_exit reads these bounded regular single-link files with O_NOFOLLOW.
Missing/malformed kernel evidence prevents complete production acceptance. These
are trusted execution artifacts, not student stdout. The restricted HDL file-access
boundary remains essential. This deployment uses Linux cgroup-v2 evidence; other
runtime/cgroup namespace configurations require separate validation.

The adapter additionally reads actual Docker OOMKilled and statvfs free space.
Known OOM, PID events, zero workspace free space, SIGXFSZ exit 153 or admission
failure produce an explicit resource_failure. Production parser uses the already
existing resource_limit status; no database enum/migration, XP routine or job code
was changed. Cleanup failure takes precedence. Resource/infrastructure failures
cannot become acceptance even if successful grader output preceded exhaustion.
No guarantee is made that every shared-volume transient ENOSPC is specifically
classified; failure without sufficient evidence remains fail-closed system/compile
error. A full shared quota can affect an otherwise-correct concurrent job.

## Fixed matrix and actual results

The matrix was fixed before execution. There were **two complete attempts**, the
second after one concrete trusted-fixture correction; no open-ended testing. Each
attempt ran 36 full-native regression cases plus 42 matrix cases: 78 recorded
evaluations, including preflight/start/admission cases that are NOT simulations.
Repeated attempts do not double unique coverage. A third checks-only image run
executed final focused units, with no further load/stress matrix.

Final base gate: 848 assertions (includes source/config/cleanup assertions, not
848 jobs), 32 independent native executor inspections and 40 matching packaged
production source hashes. The image-owned runner hash also matched.

| Correct catalog solution | Actual final native result | Compile / simulation / container |
| --- | --- | --- |
| and-gate-demo | accepted, 4/4 | 0 / 0 / 0 |
| mux-2to1 | accepted, 8/8 | 0 / 0 / 0 |
| sync-counter-4bit | accepted, 20/20 | 0 / 0 / 0 |
| xor-gate | accepted, 4/4 | 0 / 0 / 0 |

All four alternatives E also remained accepted; C wrong solutions and D syntax
errors retained their classifications. Existing native attacks, missing/duplicate
summary, unsuccessful process, flood after genuine success, timeout, repeated/
mixed concurrent jobs, actual OCI failure and caller interruption/recovery passed.
Unsupported file access was scanner preflight, not a native attack execution.

| Final mode | Fixed cases/budgets | Actual result | Whole adapter elapsed range |
| --- | --- | --- | --- |
| Serial | 2 rounds × 4 catalog × correct/wrong = 16 | all matched, no RPC errors | 637.240–794.220ms |
| Concurrent | 2 waves × 4 correct catalog jobs = 8; four caller threads | all matched, no RPC errors | 920.956–1621.082ms |
| WASM overlap schedule | 4 catalog × correct/wrong = 8; async full WASM suite co-launched by host driver | all matched, no RPC errors; WASM exit 0 | 1053.714–1549.586ms |
| Trusted resources/recovery | four exhaustion/recovery pairs plus full-admission/recovery = 10 | all matched; no RPC errors | 26.839–1862.398ms |

Normal matrix budgets: each executor 64MiB memory+swap ceiling, 0.25 CPU, 64 PIDs,
5000ms and 65536 captured bytes. Four admitted jobs therefore have at most 256MiB
configured executor memory ceilings and one configured CPU in these waves; workspace
cap is shared 128MiB. The probe worker is independently 512MiB/one CPU/128 PIDs.
This establishes **four concurrent direct callers at these tested profiles**,
not four Celery prefork consumers or maximum-resource/student worst-case throughput.
Peak simultaneous running executor count and precise per-process WASM overlap
duration were not separately sampled; the asynchronous launch/order is in the
executed driver. No end-to-end queued concurrency was exercised.

Each overlap schedule completed the actual WASM suite: 146 named assertions,
53 TypeScript production evaluations and 13 Python-parser real-WASM cases. WASM
evidence stays distinct from native Docker/transport evidence. No Vite service
was started. A normal new job passed after every exhaustion condition.

### Safe per-RPC observations

No unexpected actual RPC error/ReadTimeout occurred in the 32 normal matrix cases
in either attempt. Final observed maxima in ms:

| RPC | Serial | Four-caller waves | WASM overlap schedule | Unchanged request deadline |
| --- | ---: | ---: | ---: | ---: |
| create | 127.802 | 309.381 | 465.828 | 10000 |
| inspect before start | 12.632 | 61.050 | 62.751 | 10000 |
| attach | 30.791 | 79.606 | 94.398 | 10000 |
| start | 315.112 | 581.076 | 600.449 | 10000 |
| wait | 19.284 | 33.707 | 20.492 | 3000 |
| remove | 57.099 | 196.510 | 90.474 | 10000 |
| output collection span | 429.979 | 762.385 | 796.130 | execution budget 5000 |

Complete safe event arrays, outcomes/deadlines and every case are retained in the
outside-Git result.json, not just these maxima. Null filesystem/stream-close
deadlines remain explicit. These measurements do not guarantee tail latency.

Actual expected negative RPCs in the final base gate:

- Missing image: image.inspect, elapsed 16.522ms / configured 10000ms,
  error category not_found; verdict system_error, exact cleanup.
- Actual wrong-image OCI startup: start, elapsed 159.804ms / configured 10000ms,
  daemon_error; verdict system_error, exact cleanup. This is not a mocked startup.
- Overflow/timeout exercised real kill/wait/remove and output-collection outcomes;
  retained capture bounded and later ordinary evaluations passed.

Production adapter units additionally inject ReadTimeout at create, start,
inspect.after_output, wait and cleanup; every result fails closed, has the expected
precise phase/category/deadline, excludes unsafe messages and assesses no attempt.
Production workspace unit injects remove failure and retains its exact record with
phase remove. These are **controlled faults**, not reproduction of the original
daemon timeout. Original coarse start-phase evidence cannot be retrospectively
mapped to a specific RPC. No root-cause explanation was established.

### Trusted exhaustion evidence, not student-accessible shell

Stress wraps the real image-owned grader with a FIXED trusted shell command in
the actual executor. It still calls the production sandbox/parser and real SDK;
all isolation/limits are inspected. No token is injected or guessed. Overriding
the trusted command for these probes is not permission for student shell/file
tasks; no scanner restriction was changed. The probes do not certify all restricted
HDL forms that might allocate resources.

| Final probe | Budget and observed evidence | Verdict / cleanup / recovery |
| --- | --- | --- |
| Memory | finite 64MiB pipe retention under 32MiB executor, 2000ms; OOMKilled=true, kernel oom_kill=1, exit 137, elapsed 1862.398ms | resource_limit / clean / accepted |
| PID | bounded fork attempts under 16 PIDs, 2000ms; kernel max event=1, exit 2, 831.993ms | resource_limit / clean / accepted |
| Per-file | bounded 80MiB write request, 256MiB executor, 3000ms; actual SIGXFSZ exit 153; volume still had 67072000 free bytes, 1031.764ms | resource_limit / clean / accepted |
| Aggregate workspace | at most three 48MiB requests, each below the per-file ceiling, 256MiB executor/3000ms; 128MiB quota reached, actual free bytes=0, container exit 0, 1060.761ms | resource_limit despite successful process / clean / accepted |
| Admission | four exact reserved records; fifth rejected before allocation, compile/run absent, exit -1, 26.839ms | resource_limit / clean / accepted after exact release |

Memory/PID/file/workspace probes had real initial compile and simulation exits 0;
their later resource conditions did not establish acceptance. The zero-exit aggregate
probe is why successful process/summary alone is insufficient once storage evidence
indicates exhaustion. Recovery elapsed 747.351/755.290/663.985/637.634/652.692ms.
The stress set is serial, not a host-wide OOM/fork/disk attack. No arbitrary host
path, host port or privileged executor workaround was used.

## Failures and corrections retained

1. First complete attempt, safe intent suffix **60tlw5ha**, exit 1. Serial16,
   concurrent8 and overlap8 passed; all 10 stress cases were recorded. Initial
   memory command read a seekable character device and returned normally; compile,
   simulation/container were 0, OOMKilled=false and no exhaustion evidence. It
   legitimately returned accepted for correct grading, violating the intended
   STRESS expectation. This did not reach OOM and is not evidence of acceptance
   after actual exhaustion. No RPC failure occurred. Exact cleanup succeeded.
2. Corrected trusted memory command uses finite pipe input, forcing actual buffered
   allocation. Fixed runner also records kernel oom_kill evidence, not merely a
   guessed exit 137. Corrected full attempt **cqrdw7cx**, exit 0: native848 plus
   fixed42, all matched, both native/WASM results preserved; exact cleanup.
3. Final focused-unit-only build/run **3fl2f1pc**, exit 0, including new precise fault
   assertions. No third load matrix or indefinite retries. Exact cleanup.
4. Initial non-escalated Windows parser/mock test encountered sandbox temporary-file
   permissions and failed ten subcases/cleanup operations. This was not a live
   native failure. Normal Windows-user rerun and packaged-image suites passed.
   The explicitly observed failed temp path was later absent; no uncertain host
   temporary directories were swept/deleted by prefix.
5. A read-only result-summary snippet initially assumed preflight rpc_events was
   iterable instead of null; it failed, then a null-safe read-only summary succeeded.
   No implementation/resource modification was made for that reporting error.

## Commands/checks and versions

From the repository root; D is
`C:\Users\tsush\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe`:

```powershell
.venv/Scripts/python.exe -B tools/native_sandbox_gate.py --docker $D --authorize-native-test --reliability
# Exactly two complete attempts; one corrected fixture, no automatic grading retry.
.venv/Scripts/python.exe -B tools/native_sandbox_gate.py --docker $D --authorize-native-test --checks-only
.venv/Scripts/python.exe -B tests/test_native_diagnostics.py
.venv/Scripts/python.exe -B tests/test_verdict_integrity.py
node node_modules/typescript/bin/tsc -p tsconfig.app.json --noEmit
node node_modules/typescript/bin/tsc -p tsconfig.node.json --noEmit
node tests/status_contract_consistency.test.mjs
git diff --check
```

The driver uses actual Dockerfiles: worker build `-f worker/Dockerfile .`, executor
build `execution`, unique tags and a unique labelled bounded volume. Default worker
command is overridden with sleep for direct probe execution; no Celery consumer or
fake evaluator is substituted. Only fixtures/tests are RO mounts, not production
worker/backend source. Probe payload is private stdin, never token/source argv or
logs. Seed 002 remains RO test fixture TEXT, never SQL. Final full run records 24
host Docker invocations, all exit 0; actual executor RPCs occur inside the worker.
Safe host command/result ledgers live under `%TEMP%\vq-native-intent-<suffix>`.

| Check | Actual result |
| --- | --- |
| Packaged production-parser/mock-adapter suite | exit 0, 9 methods with expanded timeout/resource subcases |
| Packaged production worker-dispatch suite | exit 0, 8 methods; controlled DB/sandbox, not live dispatch |
| Packaged production workspace/profile suite | final exit 0, 10 methods; controlled daemon and actual Linux temp files |
| Packaged and host production diagnostics suite | exit 0, 3 methods; safe vocabulary/cap/exception handling |
| Packaged pip check | exit 0 |
| Full native gate | final exit 0, 848 assertions / 36 cases / 32 inspections |
| Fixed reliability matrix | final exit 0, 42 cases, zero failed; four direct callers tested |
| Actual WASM suite, co-launched each attempt | exit 0 each; 146 named / 53 TS evaluations / 13 Python-parser WASM |
| Host parser suite in normal Windows context | exit 0, 9 methods; not native proof |
| Both TypeScript noEmit checks | exit 0 |
| Static status contract | exit 0, 6 checks |
| Compose config with no-env-resolution and dummy required interpolation | exit 0, three quota/volume/socket checks; no private env resolution/service start |
| Source AST/limited literal-secret/whitespace scan | exit 0; ten pending Python files, zero candidate secret patterns; not exhaustive certification |
| git diff --check | exit 0, LF/CRLF informational warnings only |
| Independent exact cleanup/baseline comparison | exit 0, all three new plans absent; unrelated resources preserved |

Observed actual full-run image versions: Python 3.12.15, Docker Python 7.2.0,
Celery 5.6.3, asyncpg 0.32.0, Pydantic 2.14.0, Icarus 11.0 stable. Changed upstream
dependency versions are build observations, not source dependency-lock changes.
Host system/global dependencies were not installed. Mocks are disclosed above;
failed expectations exit nonzero rather than being counted as passing tests.

## Cleanup, scope and Git

Independent Docker inspection verified each new plan's exact worker, workspace
volume and both image tags absent, and zero sandbox.job/native-gate-labelled
containers. Original container IDs/names/states match the initial snapshot: ten
Supabase containers, nine running/one edge exited. Original three volumes, four
networks and thirteen image tags remain. No new test network/host port was created.
No original private recovery artifact was accessed/changed. Safe new ledgers are
retained outside Git; shared Docker build caches were not pruned. Probe workspaces
and per-job records were empty apart from the infrastructure lock before volume
removal. Host-owned WASM process was communicated/reaped; cleanup terminates only
its exact process on failure. No known task Docker residue remains.

New implementation in this follow-up: diagnostics.py; kernel/resource evidence in
sandbox.py, workspace.py, run.sh and evaluator.py; bounded-volume/admission wiring
in Compose/.env example. New tests: native_reliability_probe.py and
test_native_diagnostics.py. Existing native/unit/driver/test instructions were
updated, including diagnostic faults, final --checks-only mode and volatile-quota
compatibility notes. Existing executor Dockerfile/build exclusions and SDK minimum
from the workspace milestone remain pending but were not newly changed here.

All eight original tracked changes and seven original new files were preserved.
Three new technical files plus this report make **eight modified tracked files,
eleven intended untracked files**, none staged. Baseline-to-current tracked diff
before report: 312 insertions / 254 deletions; includes earlier workspace work.
Auth/backend/frontend, worker task/XP/job code, migrations/manifests and historical
handoff reports/checkpoint are unchanged. Nothing committed or pushed.
Docker/backend-security skills informed exact ownership, private diagnostics,
bounded storage and truthful evidence separation; no privileged executor or database
permission workaround was used.

## Remaining limitations and next gate

- Historical ReadTimeout cause still unresolved; this bounded sample does not
  guarantee no future RPC timeout or replace a production latency investigation.
- SDK/transport/frame allocation, aggregate worker RSS, multiple volumes/workers,
  maximum-resource concurrency, long-running throughput and hostile simulator/kernel
  vulnerabilities are not certified. Four-caller results use the stated modest
  profiles. Retained capture bounds are not all-allocation bounds.
- Tmpfs is volatile. Power/daemon/volume-unmount recovery, durable production job
  reconciliation, cleanup RPC outage and all admission/fsync race windows need
  separate work. Resource labels/intents aid exact recovery, not automatic safety.
- No live API→Redis→Celery→native successful grading, accounting/XP/attempt correctness,
  revision-safe authoring or production/deployment readiness is established.
- Existing Supabase LAN exposure, snapshot restore gate, historical SQL timeout
  and already-exited edge service remain untouched/unresolved.

Smallest next separately authorized task: review/checkpoint these native changes,
or proceed to a narrowly scoped real queued correct/wrong native job gate after
reverifying the disposable database/roles and explicitly authorizing exact accounts/
fixtures/services. Use the reviewed bounded volume and restricted runtime identities;
observe real task IDs, durable owner-only results and exact cleanup. Do not call it
XP correctness, exactly-once delivery or production readiness, and do not apply
migrations or restore/reset anything automatically. Stop after this report.
