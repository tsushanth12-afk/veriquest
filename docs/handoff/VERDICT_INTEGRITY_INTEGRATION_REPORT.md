# Verdict-integrity Vite HTTP integration report

Date: 2026-09-30 (Asia/Calcutta). Workspace: `C:\Users\tsush\Desktop\veriquest`. Branch `main`, HEAD `4a49d625fdc43782ba2387fb9bcb9168dd4e0d60`.

## Verdict and scope

**Vite development HTTP integration passed** for the tested catalog, attack, overflow, timeout, and recovery cases. This is a local dev-server result, not Docker/container, deployed-build, production-safety, database, or XP validation. No evaluator or middleware integration defect was found, so production implementation files were not changed in this task. One focused HTTP regression test and this report were added. No staging, commit, push, dependency installation, migration, Docker/WSL provisioning, or deployment occurred.

No repository `AGENTS.md` was found. The remediation and security handoff reports and `tests/VERDICT_INTEGRITY.md` were read before starting the server. All pre-existing changes and reports were preserved.

## Route and server

`vite.config.ts` registers `iverilogEvaluatorPlugin` in the Vite dev server. `POST /api/internal/evaluate` accepts JSON `{ "challengeId": string, "code": string }` and, on a handled evaluation, returns HTTP 200 with the production `EvaluatorResult`: `status`, `success`, `testsPassed`, `totalTests`, `compilerOutput`, `executionTimeMs`, and `simulationNanoseconds` (optional `failedVector`). The route also has 65,536-byte request limit, 20 requests per 60 seconds per IP, and 413/429/500 error branches. The test made 12 requests from localhost and did not alter the limiter.

An available port was checked, then Vite was started with `node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5177 --strictPort`. Vite v8.3.0 reported ready on `http://127.0.0.1:5177/` in 1,775 ms. Only that session was stopped at the end by Ctrl-C; its process ended, and a subsequent localhost fetch returned `SERVER_STOPPED` (exit 0). Ctrl-C caused the expected server command exit 1. No unrelated process was stopped.

## Actual HTTP observations

The checked-in `tests/verdict_integrity_http.test.mjs` sends actual student HDL to the real HTTP route and uses assertions that exit nonzero on failure. No execution token was supplied to any request. Every response below was HTTP 200 and had the shown verdict; the test also checked the `success` flag and absence of a 64-hex-character token in returned diagnostics for each case.

| Case | Verdict | Passed/total | Other observed evidence |
| --- | --- | ---: | --- |
| Correct AND | ACCEPTED | 4/4 | 454 ms |
| Correct mux 2:1 | ACCEPTED | 8/8 | 402 ms |
| Correct synchronous 4-bit counter | ACCEPTED | 20/20 | 481 ms |
| Correct XOR | ACCEPTED | 4/4 | 429 ms |
| Ordinary wrong AND logic | WRONG_ANSWER | 3/4 | 397 ms |
| AND syntax error | COMPILATION_ERROR | 0/4 | 237 ms |
| Wrong AND logic printing forged ACCEPTED, TOTAL, PASSED and FAILED | WRONG_ANSWER | 3/4 | Forged marker was present in returned diagnostics, proving that payload executed; 405 ms. |
| Correct AND logic, real trusted success summary, then excessive output | SYSTEM_ERROR | 0/4 | Captured diagnostics contained the redacted genuine `VQ_TRUSTED:[grader-token]:ACCEPTED:4:4:0` before overflow; 65,501 returned diagnostic characters; 479 ms. |
| Infinite zero-delay simulation | SYSTEM_ERROR | 0/4 | Returned diagnostic said timed out; 5,289 ms. |
| Normal correct AND immediately after overflow and timeout | ACCEPTED | 4/4 | 371 ms. |
| Correct AND repeat 1 | ACCEPTED | 4/4 | 382 ms. |
| Correct AND repeat 2 | ACCEPTED | 4/4 | 414 ms. |

Result: **57 HTTP assertions across 12 real route requests, 0 failed**. The overflow fixture was not merely rejected at source validation: a genuine trusted success record was observed before excess student output. The timeout fixture was not merely rejected at compilation: the response contained the host timeout diagnostic. The forged marker and counters were observed in returned simulator output but could not establish ACCEPTED.

## Bounded worker integration and evidence limits

Successful HTTP compilation/simulation through `evaluate` verifies that Vite resolved the local worker script and Icarus WASM assets in this dev-server environment and that worker startup/messages worked. The overflow response arrived in 479 ms rather than waiting for the million requested print iterations; the timeout response arrived after the approximately five-second host timer. By source, `runBoundedWasm` awaits `Worker.terminate()` before resolving/rejecting, and the worker posts incomplete/truncated capture as soon as its byte budget is exceeded. Thus the response and later recovery are consistent with worker termination. Direct observation of individual worker IDs or a worker-count metric was not available through this route. The Vite Node process had 60 OS threads before the requests and 59 afterward; this is a coarse observation, **not proof of zero worker leaks**. Three successful post-fault requests show that the server did not stall.

The output budget is enforced in `boundedWasmWorker.mjs` `collector.add` before retaining lines; the host `boundedWasm.ts` timer and `settle` terminate the worker. `evaluator.ts` `parseEvaluationResult` requires `outputComplete === true`, `outputTruncated === false`, and zero compile/simulation exits before a trusted record can accept. `verdictProtocol.ts` `prepareTestbench` lexically discovers emitters/declarations and ignores comments/strings in identifier rewriting; `validateStudentSource` permits the four audited beginner HDL examples while keeping capability restrictions. Python `parse_evaluation_result` requires explicit capture and process evidence. These are source findings and prior focused-test evidence, not claims that this HTTP run exercised the Docker worker.

## Other executed commands and checks

| Command/check | Exit | Result |
| --- | ---: | --- |
| `node --experimental-strip-types tests/verdict_integrity_http.test.mjs http://127.0.0.1:5177` | 0 | 57 assertions / 12 HTTP requests; per-case responses above. |
| `node --experimental-strip-types tests/verdict_integrity.test.mjs --python C:/Users/tsush/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe` | 0 | 146 named assertions; 53 production TypeScript WASM evaluations; 13 Python-parser cases using real WASM output. Not Docker. |
| `& C:/Users/tsush/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe -B tests/test_verdict_integrity.py` | 0 | 9 unittest methods; Docker transport tests are mocked. |
| `node node_modules/typescript/bin/tsc -p tsconfig.app.json --noEmit` | 0 | Type check. |
| `node node_modules/typescript/bin/tsc -p tsconfig.node.json --noEmit` | 0 | Vite/config type check. |
| `node node_modules/oxlint/bin/oxlint tests/verdict_integrity_http.test.mjs src/evaluator/evaluator.ts src/evaluator/boundedWasm.ts src/evaluator/boundedWasmWorker.mjs src/evaluator/verdictProtocol.ts --deny-warnings` | 0 | Focused lint. |
| Localhost fetch after stopping Vite | 0 | `SERVER_STOPPED`; cleanup confirmed. |

An overlapping first focused-WASM run yielded a process session before its exit was captured; it is not counted. The same command was rerun alone and observed to exit 0 with the totals above. Neither run contacted the Vite route or Docker.

## Changed files and Git state

Files added in this task: `tests/verdict_integrity_http.test.mjs` and `docs/handoff/VERDICT_INTEGRITY_INTEGRATION_REPORT.md`. No existing file was changed by this HTTP integration task. Pre-existing implementation/test modifications and untracked handoff documents remain in place and unstaged. The two historical reports `docs/handoff/CODEX_TAKEOVER_REVIEW.md` and `docs/handoff/VERDICT_INTEGRITY_SECURITY_REVIEW.md`, plus the remediation report, were preserved.

At final check, staged files: none. Pre-existing tracked modifications: `src/evaluator/evaluator.ts`, `tests/status_contract_consistency.test.mjs`, `tests/test_fix1_error_classification.mjs`, `worker/execution/evaluator.py`, `worker/execution/sandbox.py`. Untracked: the three pre-existing handoff reports, `src/evaluator/boundedWasm.ts`, `src/evaluator/boundedWasmWorker.mjs`, `src/evaluator/verdictProtocol.ts`, `tests/VERDICT_INTEGRITY.md`, `tests/test_verdict_integrity.py`, `tests/verdict_integrity.test.mjs`, `tests/verdict_integrity_cases.json`, `worker/execution/verdict_protocol.py`, and this task's two new files. Git HEAD stayed at the checkpoint commit.

## Remaining gates

Real Docker execution is still blocked by missing Docker/WSL/SDK and remains a separate gate. The Vite result says nothing about Docker workspace mounts, UID permissions, SDK frame buffering, daemon logs, or container cleanup. A deployed/preview build was not started, and no database/API submission, XP, or UI workflow was exercised. The supported HDL/template profile remains intentionally restricted; new challenge templates need validation against it. No claim of production readiness follows from this dev-server pass.
