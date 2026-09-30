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

To additionally run real worker container parity, append `--docker` to the Node
command. It requires an already-running Docker daemon, Python Docker SDK, and
prebuilt execution image; the test preflights the image and does not build/pull.
Absent prerequisites are failures/blockers, never passing container tests.

Next validation milestone: run this container parity suite in a provisioned
environment and verify the existing workspace ownership/mount and shell exit
recording behavior, including compilation failures and cleanup. No commit,
deployment, database, or scoring validation is implied by these tests.
