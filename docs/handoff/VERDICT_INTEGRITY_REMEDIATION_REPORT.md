# Verdict-integrity remediation report

Date: 2026-09-30 (Asia/Calcutta). Repository: `C:\Users\tsush\Desktop\veriquest`. Branch `main`; HEAD `4a49d625fdc43782ba2387fb9bcb9168dd4e0d60`. No staging, commit, push, installation, deployment, migration, or full application service startup occurred.

## Outcome and evidence boundary

All four requested corrections are implemented in the local working tree and pass available focused tests. This is **not production-verified**: no real Docker container, Docker SDK, WSL distribution, deployed Vite server, or native Icarus integration was available for validation. A mocked Docker transport does not prove mount permissions, daemon streaming behavior, UID access, log-driver bounds, or cleanup. Do not commit or deploy this as container-validated work without the next validation step.

## Fixes

1. **Output capture (H1).** The installed `@veriflow/iverilog-wasm` adapter accumulated all stdout/stderr before returning. `evaluate` now uses a local bounded worker (`boundedWasm.ts`/`boundedWasmWorker.mjs`) with actual Icarus WASM preprocessing, compilation, and VVP execution. Print callbacks check UTF-8 byte length *before* retaining a line; at the 65,536-byte combined budget they signal incomplete/truncated capture to the host, which terminates the worker. Compile and simulation each have a five-second host timeout. The Docker adapter streams demultiplexed output into bounded bytearrays, kills the container on overflow, and reports explicit capture flags. Its watchdog still enforces the configured wall timeout. A real-WASM regression emits a genuine ACCEPTED record and then floods output; the capture is incomplete and the production parser returns SYSTEM_ERROR. A mocked Docker generator raises if the adapter reads beyond the budget; the adapter stops, kills, and returns neutral failure. SDK frame allocation and Docker daemon log storage remain outside the adapter's proven bound.

2. **Token-aware template preparation (M1).** Both protocols lex comments, strings, identifiers and punctuation before finding trusted TOTAL/status display calls or grader declarations. Only actual display constructs are instrumented; only selected code identifiers are renamed. Comments and strings cannot add a DUT name to the reserved set. Named-port labels after `.` are not renamed. Line/block-comment, string, similar-name, formatted-emitter, multiple-reference, and parameterized-instance regressions cover the audited `// module and_gate` failure. Current catalog and seeded templates remain supported. Functions and complex trusted declaration profiles still fail closed.

3. **Beginner HDL compatibility (M2).** The capability scan now tokenizes decimal numbers and allows ordinary named-port shorthand, literal whole-line `timescale` directives, and `$isunknown`. It still excludes arbitrary preprocessor macros/includes, escaped identifiers, hierarchy, scope resolution, bind/force/DPI-style constructs, and non-allowlisted system calls that could expose the token, bytecode, files, or grader state. Positive tests run the four formerly rejected correct examples through production `evaluate` and real WASM; negative capability cases and all catalog solutions still pass. The lexer is conservative, not a full Verilog grammar; expansion of supported syntax requires further differential testing.

4. **Explicit completeness evidence (M3).** Python `parse_evaluation_result` requires actual string stdout/stderr keys, exact boolean `output_complete=True`, `output_truncated=False`, `timed_out=False`, and integer zero compilation, simulation, and container exits before it can accept. Missing, null, wrong-type, incomplete, truncated, contradictory or unsuccessful evidence fails closed. TypeScript `parseEvaluationResult` similarly requires a string output, explicit complete/untruncated capture, and zero compile/simulation exits. The production Docker adapter and bounded WASM runner now supply the evidence; the cross-language test bridge supplies explicit fixture evidence rather than relying on defaults. Diagnostic text never supplies process success.

## Executed verification

All commands ran from the repository root. Exit codes shown are observed, not inferred from test files.

| Command | Exit | Actual result / evidence type |
| --- | ---: | --- |
| `node --experimental-strip-types tests/verdict_integrity.test.mjs --python C:/Users/tsush/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe` | 0 | 146 named equality assertions; 53 production TypeScript catalog/exploit WASM evaluations; 13 Python production-parser cases fed by real WASM output. Additional direct bounded-worker, lexical, parser and overflow assertions also ran. **Not Docker.** |
| `& C:/Users/tsush/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe -B tests/test_verdict_integrity.py` | 0 | 9 unittest methods, including production parser, preparation, capability gate and mocked Docker adapter/stream. **Mocked transport, not container execution.** |
| `node --experimental-strip-types tests/test_fix1_error_classification.mjs` | 0 | 20 production evaluator classification cases. |
| `node node_modules/typescript/bin/tsc -p tsconfig.app.json --noEmit` | 0 | TypeScript application check. |
| `node node_modules/typescript/bin/tsc -p tsconfig.node.json --noEmit` | 0 | TypeScript Vite/config check. |
| `node node_modules/oxlint/bin/oxlint src/evaluator/evaluator.ts src/evaluator/verdictProtocol.ts src/evaluator/boundedWasm.ts src/evaluator/boundedWasmWorker.mjs tests/verdict_integrity.test.mjs tests/test_fix1_error_classification.mjs tests/status_contract_consistency.test.mjs --deny-warnings` | 0 | Focused lint. |
| `node tests/status_contract_consistency.test.mjs` | 0 | 6/6 static contract checks. An earlier run caught a new counter-name allow-list line; the narrow test allow-list was updated and rerun successfully. |
| `node tests/security_and_contracts.test.js` | 0 | 23/23 existing mocked/static checks. |
| `node tests/backend_multiuser_security.test.mjs` | 0 | 23/23 existing mocked/static checks; not live multi-user evidence. |
| `git diff --check 4a49d625fdc43782ba2387fb9bcb9168dd4e0d60` | 0 | No whitespace errors; Git emitted only LF/CRLF warnings. |

One intermediate verdict test failed because its string-content fixture put an `initial` block outside a module; the fixture was corrected and the full command passed. One intermediate bounded-worker test timed out because the WASM runtime swallowed a callback exception; the worker now notifies the host on overflow before the host terminates it, and the full command passed. The initial Python evidence test exposed truthy-string timeout handling; it now requires `timed_out is True` and passed on rerun. These failures are not counted as passing evidence.

## Files and repository state

Implementation files modified/new for the original verdict milestone and this remediation: `src/evaluator/evaluator.ts`, `src/evaluator/verdictProtocol.ts`, `src/evaluator/boundedWasm.ts`, `src/evaluator/boundedWasmWorker.mjs`, `worker/execution/evaluator.py`, `worker/execution/verdict_protocol.py`, `worker/execution/sandbox.py`. Test and design files: `tests/verdict_integrity.test.mjs`, `tests/test_verdict_integrity.py`, `tests/verdict_integrity_cases.json`, `tests/status_contract_consistency.test.mjs`, `tests/test_fix1_error_classification.mjs`, `tests/VERDICT_INTEGRITY.md`. This report is the only new handoff document from this remediation. No XP, database, UI, migration, lockfile, or Docker packaging file was edited.

At the final pre-report check, the five tracked modifications were `src/evaluator/evaluator.ts`, `worker/execution/evaluator.py`, `worker/execution/sandbox.py`, `tests/status_contract_consistency.test.mjs`, and `tests/test_fix1_error_classification.mjs`; there were no staged files. The new protocol, bounded-worker, test, and design files above were untracked, as were the two historical handoff reports. This report is now also untracked. The takeover report SHA256 remains `5964DA4DA8B358266B4F888FB742141E49A229B70CAA5531122DBC405DC85D21`; the security review SHA256 remains `80497153DE5973D75D441B7213FCD1A255701E3A6F248AAC34F92C13E776AB96`. Both were preserved byte-for-byte.

No repository `AGENTS.md` was found. The Docker CLI is absent from PATH, bundled Python has no Docker SDK, and `wsl --status` reports WSL not installed. No real container check was run.

## Remaining risks and next task

The source capability gate is a conservative lexer rather than a formal Verilog parser. Unsupported legitimate HDL includes arbitrary macros/includes, escaped identifiers, hierarchy, scoped/package constructs, non-allowlisted system tasks, and complex trusted template declarations. The Docker adapter's own retained bytes are bounded, but Docker SDK frame buffering/daemon-side log retention is not proven bounded without a real daemon. Existing workspace ownership/mount and best-effort cleanup risks from the security review remain. The bounded WASM runner uses the installed package's Icarus assets/configuration and passed direct Node execution, but Vite server bundling/runtime behavior was not exercised.

**Recommended next task:** in a provisioned environment with the prebuilt image, run the existing `--docker` parity cases plus a real output-flood test; verify workspaces are mounted/readable by UID 1000, stage files and exit statuses are correct, capture flags are truthful, Docker log storage is constrained, and cleanup is observable. Separately smoke-test the server-side Vite evaluation route with the bounded worker. Keep these as validation/follow-up work, not claims satisfied by the current mocks.

**Completion status:** four source-level remediation fixes implemented and locally regression-tested; production/container conclusion still blocked by unavailable Docker/WSL and untested deployment runtime.
