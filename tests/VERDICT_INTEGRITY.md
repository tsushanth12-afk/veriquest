# Evaluator verdict integrity

## Trust boundary

`evaluate` (TypeScript) and `DockerSandbox.execute` (Python) prepare a fresh
256-bit cryptographic capability for each execution. Only the trusted testbench
contains that capability. It emits one record:

`VQ_TRUSTED:<capability>:<ACCEPTED|WRONG_ANSWER>:<total>:<passed>:<failed>`

The expected capability and total reach the production parsers through host
arguments/metadata, never through student output. Legacy status markers, totals,
passed/failed counts, timing fields, and vector lines are diagnostics only.
Unknown-capability records cannot establish a verdict. Exactly one matching
record is required; duplicates (even identical), conflicting, incomplete,
noncanonical, or inconsistent records fail closed. The total must match the
trusted configuration; passed + failed must equal total; acceptance requires
zero failures. Parsing precedes diagnostic truncation/redaction.

**A nonce alone is not the security boundary.** Both execution paths first enforce
a restricted student HDL capability profile. Preprocessor directives/macros
other than a literal whole-line `timescale`,
escaped identifiers, hierarchical access (except named port connections),
scope resolution, bind/force/DPI, and non-allowlisted system tasks are rejected.
This blocks source/bytecode/filesystem reads and writes, VPI-style inspection,
and subprocess access. Grader module/task/integer names are moved into the
reserved `__vq_grader_` namespace; student identifiers in that namespace are
rejected. This also blocks unqualified upward access to grader counters/tasks.
Ordinary student locals called `passed`, `failed`, or `i` remain available.
Diagnostic strings may contain any legacy verdict text; they do not confer trust.

The allowlisted system calls are display/write/strobe/monitor, time/realtime,
signed/unsigned/clog2/bits/isunknown, finish/fatal. Decimal literals and named
port shorthand are supported; hierarchy remains prohibited. Early termination loses the trusted
record; nonzero termination cannot produce acceptance. The capability is
redacted from returned diagnostics. Do not relax the capability gate without
reassessing token secrecy and grader-state isolation in both implementations.

TypeScript's bounded worker runs separate preprocessing, compilation and simulation
stages and requires successful compile and simulation exits. Python's fixed shell writes separate compiler/simulator exit
files, inaccessible to capability-restricted HDL. The worker requires those
successful stages AND a successful container exit. Both parsers require explicit
complete/untruncated capture evidence (Python also requires `timed_out=false`).
Missing, malformed, timeout, truncated output, or incomplete log collection fails closed. Output text cannot
assert process success. A worker simulation failure uses its existing neutral
`system_error` contract; TypeScript exposes `SIMULATION_ERROR`.

## Compatibility and limits

The current four catalog testbenches and seeded database AND testbench use the
supported trusted template profile: simple module/task/integer declarations,
integer passed/failed counters initialized to zero, one literal TOTAL display,
and exactly one emitter for each legacy terminal status. Preparation instruments
these in memory; no catalog, database, or migration changes are needed. Other
template profiles fail closed and must be reviewed before use. Functions and
complex trusted declarations are deliberately unsupported in this milestone.

This is a restricted HDL grading environment, not unrestricted SystemVerilog:
otherwise-correct programs requiring arbitrary directives/macros, file
I/O, escaped names, hierarchy, or other blocked features receive a capability
diagnostic. Raw vector diagnostics remain useful but are not populated into a
trusted failed-vector object. Unverified synthetic simulation times are no longer
reported. The WASM worker and Docker adapter enforce a combined 65,536-byte
capture budget before retaining output and terminate on overflow. Docker daemon
log storage and SDK frame allocation are not proven bounded by this adapter.
This change does not fix Docker filesystem permissions, packaging,
simulator vulnerabilities, API authorization,
XP persistence, or deployment.

## Run and classify the regressions

Run from the repository root with installed dependencies; no installation or
service startup is performed by the default tests:

```powershell
node --experimental-strip-types tests/verdict_integrity.test.mjs --python <python-executable>
& <python-executable> -B tests/test_verdict_integrity.py
node --experimental-strip-types tests/test_fix1_error_classification.mjs
node node_modules/typescript/bin/tsc -p tsconfig.app.json --noEmit
node node_modules/typescript/bin/tsc -p tsconfig.node.json --noEmit
```

| Test | Evidence type |
| --- | --- |
| Shared JSON parser cases | Production parser unit tests with adversarial result fixtures, not a reimplementation |
| Catalog A-I plus exploit cases | Real WASM compilation/simulation through production `evaluate` |
| Python bridge cases | Python production preparation/parser with real WASM output; **not Docker** |
| Python preflight/adapter methods | Production adapter with mocked Docker transport; **not container execution** |
| Error-classification test | 20 production evaluator cases; assertions now exit nonzero; report writes are opt-in |
| Status contract suite | Static source checks; narrow allow-list for a counter name, not a status |

All new assertions fail the process on mismatch. Coverage includes correct,
ordinary wrong, syntax error, forged status/counters/vectors, actual final-block
output after the grader, before/after combinations, conflicting and duplicate
trusted records, missing records, failed processes with successful-looking
output, stale tokens, inconsistent counts, capability attacks, and log loss.

## Native workspace gate (separate from WASM)

The native adapter now requires a Linux worker container with root/file-ownership
authority, Docker access, and a 128MiB tmpfs-backed local named volume at
`/var/lib/veriquest/workspaces`. `VQ_WORKSPACE_VOLUME` must match the inspected
worker mount. There is no host/container-private temporary-directory fallback.
Executors get only generated job input/output volume subpaths, not the whole volume.
The exact reviewed tmpfs options and actual capacity are checked; persistent
unbounded volumes are rejected. Admission permits at most four outstanding jobs
per volume. Interrupted-job records survive caller death while the mount remains,
but tmpfs is not a power-loss durable journal; host test resource intents remain
outside Git. No automatic replacement of an existing volume is performed.
The worker Docker SDK requirement is 7.2 or later; unsupported subpath/isolation
configuration fails closed before executor startup.

With separately authorized local image builds and temporary resources:

```powershell
.venv/Scripts/python.exe -B tools/native_sandbox_gate.py --docker <docker-executable> --authorize-native-test
```

This opt-in gate uses the actual worker/executor Dockerfiles, production sandbox
and parser, catalog fixtures, actual Docker inspection, permissions and cleanup.
It creates no database rows/accounts/queues. Safe exact-resource intents/results
are retained outside Git in a printed temporary directory; job records contain
no source, bench or token. Failed assertions exit nonzero. The legacy Node
`--docker` bridge is not a standalone Windows-host setup: it needs this correctly
mounted worker environment and a prebuilt executor. Absent prerequisites are
failures/blockers, never passing container tests.

See `docs/handoff/NATIVE_SANDBOX_WORKSPACE_REPORT.md` for executed native evidence,
including disabled daemon logging and the separate remaining SDK/memory limits.
The earlier compatibility/limitations section describes the original verdict-only
milestone, not a claim that the later native workspace changes are unimplemented.
No queued end-to-end grading, database accounting, deployment or production
readiness is established by this direct native gate.
