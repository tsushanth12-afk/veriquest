# Native sandbox workspace milestone

Date: 2026-10-02. Local Docker Desktop Linux only.
Repository: `C:\Users\tsush\Desktop\veriquest`, branch `main`.
Baseline and unchanged HEAD: `6ef8c478115b9961dd78fc1d6da51e6d8c68dc1f`,
`Verify real Celery delivery and reject missing evaluators`.

## Outcome

The final isolated native gate **passed, exit 0: 847 assertions, 36 recorded
evaluation cases, 32 inspected executor configurations, 39 matching packaged
production Python source hashes**. Correct and alternate implementations for all
four catalog challenges passed real native Icarus compilation/simulation.
Wrong logic, syntax errors, forged summaries, missing results, unsuccessful
processes, overflow, timeout and configuration failures did not gain acceptance.

There is an unresolved reliability observation: an additional run overlapping
the WASM suite encountered a real Docker SDK `ReadTimeout` on the MUX wrong case.
It returned system_error, exited the gate nonzero and cleaned its resources.
The subsequent separate native run passed completely without increasing timeouts
or retrying production jobs. This does NOT establish the timeout's cause or cure.
Failed attempts below are retained, not counted as successful verification.

The final WASM/cross-language suite separately passed 146 named assertions,
53 TypeScript production WASM evaluations and 13 Python-parser real-WASM cases.
Those are not native container evidence.

No database queries/writes, accounts, migrations, seed execution, queue/API
services, scoring changes, firewall changes, commit, push or deployment occurred.
Existing Supabase containers and volumes were left running and unchanged.
This directly exercises the packaged sandbox/parser, **not a Celery-delivered
native job**, finalized accounting, crash-safe job recovery or production readiness.

## Initial verification and safe reproduction

Read the checkpoint, delivery report, comprehensive audit, worker tasks/config,
profile/parser/protocol, sandbox, Dockerfiles/Compose and verdict tests. No applicable
AGENTS.md was found in the repository or checked ancestors. Initial tree was clean.
Origin is `https://github.com/tsushanth12-afk/veriquest.git`; authorized read-only
ls-remote matched HEAD. The first sandbox-restricted network attempt failed;
the subsequent approved read-only query succeeded. Docker context desktop-linux,
Linux engine 29.8.0. Ten existing Supabase containers and three existing Supabase
volumes were inventoried before testing and independently checked afterward.

Baseline source: `DockerSandbox._execute_docker` used worker-local mkdtemp, then
a daemon host bind of that string; Compose shared only the Docker socket. Temp
directory mode was 0700/root. The old executor image's system UID was not explicitly
1000 although the adapter forced 1000:1000. Cleanup exceptions were swallowed.

Executed reproduction used the actual old worker/executor Dockerfiles and an
isolated worker tmpfs: worker created/read its task-only temp file, mode 0700;
the real daemon rejected a bind mount with **bind source path does not exist**.
Mount syntax deliberately prevented the old `-v` behavior from creating a stray
empty host directory. This was a daemon-resolution probe, NOT a complete invocation
of the old sandbox or an observed old Icarus compilation. The old UID access defect
is source/POSIX-permission evidence, not a separate executed old-UID test.
A final equivalent baseline probe also passed with exact resource journaling.

## Design and production trust boundaries

`worker/execution/workspace.py`, Workspace.__init__/reserve/populate/mounts:

- Require VQ_WORKSPACE_VOLUME, a plain local named Docker volume with no custom
  driver options. Inspect the actual worker container's RW volume mount at the
  fixed `/var/lib/veriquest/workspaces`; reject missing/wrong/RO/shadowed mounts,
  non-root execution and unsafe directory/volume configuration. No arbitrary
  host-path configuration or container-private temp fallback.
- Random UUID4 hex job identity; exclusive, fsynced, root-only 0600 JSON intent
  before files or container creation. Contains only version, job, exact container,
  volume and infrastructure owner ID, under 1KiB; never source/bench/token.
- Root/job directories 0700. Input directory root:1000 0750; source/bench files
  root:1000 0440. Output directory 1000:1000 0700. Validate real directory type,
  modes/ownership and no symlink job/input/output before mounting.
- Mount only `<job>/input` RO and `<job>/output` RW using named-volume subpaths.
  No whole-volume executor mount or parent job directory. Generated paths exclude
  traversal. Runtime host-path source names are never accepted from student HDL.
- verify_executor reloads actual Docker configuration BEFORE start and refuses
  dropped subpath, mount or isolation options. Unsupported implementations fail
  closed instead of silently mounting the whole volume.

Compose maps sandbox_workspaces to the explicit name `veriquest_workspaces` and
mounts it only in the worker. `.env.example` documents the matching setting;
EXECUTION_IMAGE remains `veriquest-icarus:latest`. Worker SDK minimum is the
exercised 7.2.0. No backend database/runtime configuration was changed.

**The root worker's Docker socket is privileged infrastructure authority.** It can
control the daemon; executor isolation does not constrain a compromised worker.
The probe worker had network none, read-only root, 512MiB/1 CPU/128 PIDs,
CHOWN/FOWNER/DAC_OVERRIDE for file management, and the socket. Production Compose's
worker remains privileged infrastructure rather than an untrusted student sandbox.
No executor had a socket/host bind/port. No API was started; its Compose service
still has no socket/volume mount. Prior live API inspection is historical evidence.

`execution/run.sh` is image-owned, mode 0555, not an editable job script. Executor
image explicitly creates/runs UID/GID 1000. It compiles RO inputs into the writable
output subpath, writes separate compile.exit and simulation.exit, then exits with
the real subprocess code. Status artifacts are bounded regular, single-link files
read with O_NOFOLLOW, not parsed student stdout.

`worker/execution/sandbox.py`, DockerSandbox.__init__/execute/_execute_docker:

- Validate every resource through the existing production profile parser, not
  merely the output budget. Preserve a lower MAX_OUTPUT_BYTES ceiling; invalid
  ceiling configuration is rejected, not silently increased.
- Bounds remain timeout 1..5000ms, memory 16..256MiB, CPU 0.1..1, PIDs 1..64,
  combined retained bytes 1..65536. Raw source/testbench inputs are capped at
  65536 UTF-8 bytes. Missing/non-string/blank bench fails before job allocation.
- Explicit network none/disabled, cap_drop ALL, no-new-privileges, read-only root,
  nonroot 1000:1000, memory=memory+swap ceiling, bounded /tmp tmpfs with
  noexec/nosuid/nodev, and 64MiB per-file RLIMIT_FSIZE for output artifacts.
- Require prebuilt image; no automatic image pull or synthetic grading fallback.
- Subscribe to attach before start, logs=False, Docker log driver none. Capture
  bounded combined bytes in a daemon collector; overflow, transport errors,
  timeout and incomplete evidence fail closed. EOF while the executor is still
  running is not treated as complete capture. Join/close collectors explicitly.
- Execution deadline starts before container.start; startup acknowledgment time
  consumes that budget. Docker RPC timeout 10s, process wait 3s and collector join
  2s are separate infrastructure bounds, not a five-second whole-operation SLA.
- Exceptions reveal only safe phase/type, never raw daemon/HDL diagnostics.

The existing cryptographic token preparation, restricted HDL capabilities,
reserved grader names and exact-one consistent trusted summary remain unchanged.
Expected token/total travel in private adapter metadata, independently of stdout.
The token is in the trusted mounted bench/compiled program, not argv/environment,
container labels/journals/printed results or daemon logs. Returned diagnostics
redact it and omit the new trusted input bench path. Files are removed on cleanup;
Python memory is not securely zeroized, and deletion is not secure disk erasure.
Compiler/VVP, the trusted runner/bench, daemon and worker remain trusted components.
Unrestricted HDL or simulator/kernel compromise is not covered by nonce freshness.

`evaluator.py:parse_evaluation_result` additionally makes cleanup_error or explicit
non-true cleanup_success system_error / SANDBOX_CLEANUP_FAILED, zero attempt flag.
Compile/run/container success, complete/untruncated capture and valid trusted
summary remain required. Cleanup evidence is adapter data, not student markers.
The shared parser fixtures/WASM bridge retain their existing contracts.

## Final real native results

All A/E rows are accepted with compilation, simulation and container exits 0,
complete=true, truncated=false, and matching trusted totals. All C rows reached
real VVP with exits 0 and wrong_answer. All D rows reached Icarus: compile/container
exit 2, simulation not run, compilation_error. Every allocated case cleaned up.

| Catalog | Correct A | Alternative E | Wrong C | Syntax D |
| --- | --- | --- | --- | --- |
| and-gate-demo | accepted 4/4, 386ms | accepted 4/4 | wrong_answer 2/4 | compilation_error |
| mux-2to1 | accepted 8/8, 368ms | accepted 8/8 | wrong_answer 4/8 | compilation_error |
| sync-counter-4bit | accepted 20/20, 331ms | accepted 20/20 | wrong_answer 0/20 | compilation_error |
| xor-gate | accepted 4/4, 322ms | accepted 4/4 | wrong_answer 1/4 | compilation_error |

Elapsed ms here is measured whole adapter wall time, not HDL simulated ns or
persisted runtime_ms. Existing parser runtime telemetry remains unchanged.

| Other final cases | Actual verdict / process evidence |
| --- | --- |
| Forged ACCEPTED plus total/passed/failed before real summary | wrong_answer 3/4; compile/run/container 0 |
| Same forgery in final block AFTER real summary | wrong_answer 3/4; actual after-summary position asserted |
| Conflicting legacy markers/counters | wrong_answer 3/4; real simulation |
| Trusted-looking record with guessed all-zero token | wrong_answer 3/4; no internal token injected |
| Early finish, missing trusted summary | system_error; exits 0; empty capture cannot accept |
| Successful-looking printed output then fatal | system_error; compile 0, simulation/container 1 |
| File-access capability attempt | compilation_error in scanner; NO native execution claim |
| Genuine success then excessive STUDENT final-block output | system_error; genuine trusted success asserted before flood; compile 0, simulation status absent, killed exit 137; 65536 retained bytes, incomplete/truncated; 342ms |
| Infinite zero-delay student simulation, profile 1000ms | timeout; compile 0, no simulation exit file, killed exit 137; incomplete; 1210ms including infrastructure/cleanup |
| Trusted fixture executing its one success emitter twice | system_error despite compile/run/container 0 and complete output; two nonce-bound records observed |
| Missing executor image | system_error, no image pull, allocated workspace removed |
| Actual OCI start failure using the packaged worker as wrong executor image | system_error; real start error, not mock; no success evidence; exact container/workspace removed |
| Two concurrent jobs, correct versus wrong | accepted 4/4 and wrong_answer 3/4; distinct job IDs/tokens/subpaths, independent cleanup |
| Three repeated correct jobs | accepted 4/4 each, 322/343/318ms, clean after each |
| Recovery job after overflow / timeout / interrupted caller | accepted 4/4 each, 313/325/314ms |

The duplicate-summary bench is an explicitly TRUSTED test fixture changing emitter
execution cardinality. It is not a student ability to learn the token or modify
the production trusted bench. No scanner restriction was relaxed. Wrong/forgery/
overflow/timeout cases used actual student HDL through production execute.

Additional actual preflight assertions: missing/null, empty, whitespace, numeric,
mapping and list benches allocate no job and return evaluator_not_configured;
six invalid resource profiles raise before execution; four unsafe/missing volume
configurations produce system_error before files. Unit negatives cover custom
volume options, mismatched/RO/nested mounts, symlinks/traversal, malformed records,
bad status artifacts, daemon outage/mismatched cleanup identity and environment
output ceilings. These unit transports are controlled, not live Docker failures.

## Actual inspection, permissions, resource and cleanup evidence

32 real native executor configurations were independently inspected by the probe.
Instrumentation wraps and calls the real Docker collection.create; it does not
replace Docker transport, the sandbox, runner or parser. Concurrent calls deliberately
do not use that global wrapper; production verify_executor still inspects them.
Inspected user, network, rootfs, capabilities, security options, memory/swap,
CPU/PIDs, tmpfs, file limit, log driver, absence of binds/ports and exact subpaths.

A separate trusted OS permissions probe in the actual executor read its input,
failed input/root writes, wrote its intended output, saw no socket/volume root/
other job, and verified the produced file from the worker. This proves actual
shared storage, not equal path strings. It verified input mode 0440 and the baked
runner's canonical source hash. Its Linux cgroup reads were memory.max=67108864,
pids.max=16, cpu.max=`50000 100000` for its configured 64MiB/16 PID/half-CPU profile.
This probe runs trusted shell, not permission to submit student shell/file tasks.
Stage symlink read was rejected; unit symlink cleanup preserved an unrelated
sentinel. Restricted role/database grants were never changed.

Resource claims are deliberately separated:

- Combined retained raw bytearrays stopped at 65536 on real flood; executor was
  killed and capture marked incomplete. Decoded strings, parser concatenation,
  thread stacks and other Python allocations are additional memory, not a 64KiB
  whole-worker claim.
- Largest final flood SDK chunk observed: 8192 bytes. This is an observation,
  NOT a general SDK/socket/frame allocation or kernel-buffer bound. Larger single
  frames, aggregate concurrency and transport buffering were not memory-profiled.
- Actual native log driver none and empty Docker LogPath prevent normal stdout/
  stderr daemon log storage for these executors. No assumption that capture alone
  bounds json-file logs. Daemon administrative logs/caches were not audited.
- Kernel cgroup settings were read in the permissions probe and limits inspected
  in grading executors. OOM, PID/CPU saturation, compiler-memory and filesystem-full
  stress were NOT performed. RLIMIT_FSIZE is per-file, not a volume/aggregate quota.

Workspace.cleanup validates exact name/job/volume/owner labels, removes the owned
container first, confirms absence, then symlink-safe Linux rmtree of the exact
job and deletes its record. Daemon error is not NotFound. Failure retains intent
and blocks acceptance. No prefix sweeps, arbitrary host deletion or global prune.

Cleanup fault injection replaced ONLY cleanup with an OSError after REAL successful
execution. Production parser reported SANDBOX_CLEANUP_FAILED; actual retained
container/files were then removed by production Workspace.recover. This is a
controlled cleanup fault, not a naturally occurring daemon removal failure.

Controlled interruption: SIGTERM a test-only calling Python process after its
real infinite executor was observed running. Its exact journal survived; production
recover removed the executor/workspace, and a later normal job passed. This does
not prove Celery/DB job recovery. An opt-in harness PID guard also supports scoped
quiescence before recovery if Docker exec CLI times out; that specific live-parent
guard, whole-worker/host death, power loss, creation/fsync windows and concurrent
recovery controllers were NOT intentionally exercised.

Independent final inspection confirmed all TWELVE runs' exact worker containers,
workspace volumes and both image tags absent, including failed runs. No task network
was created. Ten original Supabase container IDs still run; original three volume
names and original image tags remain. Private historical recovery artifacts were
not accessed/changed. Safe native intent/result ledgers remain under
`%TEMP%\vq-native-intent-<suffix>` outside Git/build contexts; no source/token/bench
payloads are stored there. Docker shared build caches were not pruned.
No temporary host server/test process remains.

If an interrupted future run retains resources, first inspect its exact safe
resources.json and worker/volume labels; do not infer ownership from a prefix.
Quiesce its verified probe, then run the production recovery for exact recorded
job IDs in that verified volume. Do not delete a volume still mounted by any
container. If the worker is unavailable or identities drift, retain the intent
and require reviewed scoped recovery; there is no automatic arbitrary-target
restore/prune. Production journals do not implement automatic job reconciliation.

## Commands and actual checks

Working directory is the repository above; D is the verified local Docker executable:
`C:\Users\tsush\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe`.

```powershell
.venv/Scripts/python.exe -B tools/native_sandbox_gate.py --docker $D --authorize-native-test --baseline
.venv/Scripts/python.exe -B tools/native_sandbox_gate.py --docker $D --authorize-native-test
node --experimental-strip-types tests/verdict_integrity.test.mjs --python .venv/Scripts/python.exe
```

The driver records exact safe Docker argv/exit ledgers in its outside-Git result.
Final native run: 19 host Docker commands, all exit 0, including actual builds:
`docker build --quiet -t <unique-worker-tag> -f worker/Dockerfile .` and
`docker build --quiet -t <unique-executor-tag> execution`; volume create, isolated
worker run, packaged regressions/pip check, native exec, recovery, inspect and exact
resource/tag removal. Native executor create/attach/start/kill/wait/inspect/removal
uses the real SDK inside that image, not extra host CLI surrogate commands.
Only test fixtures are mounted RO; production worker/backend sources are packaged,
not host-mounted. 39 canonical-LF source hashes and runner hash matched.
Seed 002 is mounted as READ-ONLY text for its existing parser fixture test, never SQL.

| Check | Actual exit and result |
| --- | --- |
| Packaged worker `python -B /app/tests/test_verdict_integrity.py` | 0; 9 methods; real parser, controlled storage/Docker transport including lost/early EOF, exit/overflow and cleanup evidence |
| Packaged worker `python -B /app/tests/test_worker_dispatch.py` | 0; 8 methods; actual task functions with controlled DB/sandbox, not another live queue run |
| Packaged worker `python -B /app/tests/test_native_workspace.py` | 0; 8 methods; actual workspace/profile on Linux temp files, mocked daemon metadata/cleanup |
| Packaged worker `python -B -m pip check` | 0; no dependency conflicts |
| Final direct native gate | 0; 847 assertions / 36 cases / 32 independently inspected executors |
| Final Node verdict suite, separately repeated | 0; 146 named assertions / 53 TS WASM evaluations / 13 Python-parser real-WASM cases |
| Host `python -B tests/test_verdict_integrity.py` | 0; 9 methods, not native |
| Host `python -B tests/test_redis_celery_delivery.py` | 0; 8 helper methods, not live delivery |
| Host `python -B tests/test_database_gate.py` | 0; 14 methods, unchanged manifest/source checks; no DB connection/application |
| `node tests/status_contract_consistency.test.mjs` | 0; 6 static checks |
| TypeScript app and node project noEmit checks | Both 0 |
| Docker Compose config, no-env-resolution, dummy required interpolation values, private output captured | 0; 5 mapping/socket/image checks; no private env file resolution or service start |
| AST/limited secret/trailing whitespace inventory | 0; 7 changed/new Python files parse, zero candidate PEM/GitHub/AWS/JWT literal patterns; not exhaustive secret certification |
| `git diff --check` | 0; LF/CRLF informational warnings only |
| Independent exact-resource cleanup probes | Final 0; all twelve run plans absent. Initial diagnostic matcher exited 1 due not-found text case; corrected read-only matcher passed, not an actual leftover |

Assertions/unittest failures exit nonzero. Unit counts are methods with subcases,
not independent live jobs; repeat runs do not multiply unique coverage. Host lacks
Docker/asyncpg/Celery libraries; native/worker/Linux-file suites were run in the
authorized actual image, not replaced by host mocks or dependency installation.
No backend pytest or new live Auth/permission/queue test was needed or run here.

Observed final image dependencies: Python 3.12.15; Docker Python 7.2.0,
Celery 5.6.3, asyncpg 0.31.0, Pydantic 2.13.5; Icarus Verilog 11.0 stable.
Base tags/lower-bound requirements are not dependency locks or vulnerability proof.

### Attempts and corrections, not erased from evidence

Safe ledger suffixes identify the run's exact resource intent/result directories:

| Suffix | Actual outcome |
| --- | --- |
| zmyhq120 | Baseline exit 0: private bind rejection/mode 0700; cleaned |
| 3o110ch1 | Initial native exit 0, 241 assertions, but inspection wrapper actually ran zero times; NOT configuration-inspection evidence |
| wl3sjd_f / 8e_m90ko / rshdidcc | Three native exits 1 while correcting inspection instrumentation/diagnostics; final identified KeyError ReadOnly because Docker omits default false. Exact cleanup succeeded each time |
| yzfz2_a3 | Exit 0: 657 assertions, 28 inspections, before later coverage/packaging refinements |
| 9ekbevum | Exit 0: 782 assertions, 32 inspections, cgroup/source-hash evidence |
| dokidv1l | Exit 1 at permissions-helper Icarus version assertion; helper lacked writable /tmp. Adding the same bounded tmpfs made that probe pass; grading already had it |
| yvh_kms4 | Exit 0: 847 assertions, 32 inspections |
| 77e_08wa | Final baseline exit 0, exact intent cleanup and 39 source hashes |
| _1j7kwuo | Exit 1: real ReadTimeout/system_error at MUX C while WASM also ran; cleanup succeeded |
| b6tb6xd8 | Final separate native rerun exit 0: 847 assertions / 36 cases / 32 inspections; no limit increase |

Production refinements were named-volume/UID sharing, explicit network-none,
validated bounds/no-log capture, pre-start inspection, EOF/process evidence,
exact observable cleanup and private diagnostics. Test-only fixes corrected the
SDK collection wrapper, omitted-false inspection field, writable version-probe
tmpfs and safe not-found diagnostic matching. No grading restriction was loosened.

ReadTimeout investigation: daemon info subsequently returned Linux 29.8.0;
the scoped event-history query returned no matching retained events. That absence
does not establish whether the executor started or which RPC timed out. The safe
phase `start` spans startup and status/wait handling; exact call/root cause remains
unresolved. Overlap/load is a hypothesis, not demonstrated causation. No automatic
production retry, higher timeout, daemon restart or unrelated service change was used.

## Changed files and repository state

Eight modified tracked files:

- .env.example — safe workspace volume example.
- docker-compose.yml — worker volume/image wiring only.
- execution/Dockerfile — explicit execution UID/GID and fixed image-owned runner.
- worker/requirements.txt — exercised subpath-capable Docker SDK minimum.
- worker/execution/sandbox.py — resource validation, adapter/capture/execution/cleanup.
- worker/execution/evaluator.py — cleanup fail-closed and new trusted-path filtering.
- tests/test_verdict_integrity.py — adapted controlled transport and added evidence negatives.
- tests/VERDICT_INTEGRITY.md — current opt-in native test instructions and boundaries.

Seven new files:

- execution/.dockerignore — executor build allowlist, only Dockerfile/run.sh.
- execution/run.sh — fixed compile/simulate/status runner.
- worker/execution/workspace.py — volume validation, exact subpaths/records/recovery.
- tools/native_sandbox_gate.py — opt-in actual-image host driver/cleanup ledger.
- tests/native_sandbox_probe.py — real native, inspection, OS permissions and interruption checks.
- tests/test_native_workspace.py — focused production workspace/profile units.
- docs/handoff/NATIVE_SANDBOX_WORKSPACE_REPORT.md — this report.

Tracked implementation/documentation diff before this report: 242 insertions,
252 deletions across eight files; new-file lines are additional. No unexpected
dependency/cache/private artifact appears in Git status. Root/backend build
allowlists are unchanged; executor context now has its own allowlist. Review found
no literal secret in intended files; no actual generated token/source/stdout was
saved in tracked reports. Historical reports, checkpoint, migration SQL/manifests,
Auth, permissions, publisher, worker job/XP code and frontend are unchanged.
Security skill backend-security-coder informed privileged-worker disclosure,
exact mounts/ownership, safe diagnostics, pre-start checks and scoped cleanup.

Final branch/HEAD/origin unchanged. **Staged: none; eight tracked modifications,
seven intended untracked files. Nothing committed or pushed.**

## Remaining gates and exact next engineering boundary

1. Investigate the observed Docker RPC timeout with safe per-RPC timing under
   bounded load. The successful later run is not evidence that it is fixed.
2. SDK/transport/aggregate memory and disk quotas, OOM/PID/CPU stress, simulator
   vulnerabilities, Docker outages and whole-worker/host/power-loss recovery.
3. Existing Supabase LAN exposure, actual snapshot restoration and the historical
   unexplained SQL timeout remain unresolved; no containment/restoration claim.
4. Future templates must obey the existing restricted trusted-template/HDL contract.
   Arbitrary SystemVerilog/new declaration profiles and question authoring/public
   versus hidden bench lifecycle were not implemented by this agnostic adapter.
5. Still no API→Redis→Celery→native successful grading evidence, finalized XP/
   attempts/quests/badges correctness, atomic claims/outbox/exactly-once delivery,
   distributed job recovery or revision-bound administrator publication.

Smallest later end-to-end queued grading test, requiring separate authorization:
reverify the disposable target/ledger/roles, use one exact disposable student and
one narrowly scoped compatible challenge fixture with zero XP reward, actual API,
isolated Redis and actual worker with reviewed workspace/socket configuration;
submit known correct and ordinary wrong HDL through authenticated HTTP. Correlate
real task/submission IDs, observe native execution and durable owner-only results,
independent process/cleanup evidence, then quiesce publishers/worker before exact
FK-ordered fixture/account/service cleanup. Fixture publication is test setup, not
native admin lifecycle proof. Observe resulting accounting without claiming it is
correct or repairing it in that gate. Resolve persistent native infrastructure
failures before proceeding; never turn a timeout into a fabricated acceptance.

Stop here. Direct local native grading and its explicit limits are now evidenced;
no additional milestone or production-readiness assertion is authorized.
