# Codex Takeover Review — VeriQuest

Review date: 2026-09-28  
Reviewed commit: `4a49d625fdc43782ba2387fb9bcb9168dd4e0d60`

## Scope and evidence

This review used the current repository as authoritative. The investigation was read-only: no source edits, dependency installs, commits, pushes, services, deployments, or migrations were performed. This document was subsequently created at the owner's request.

Evidence labels:

- **Verified by source:** implementation was inspected; runtime behavior is not implied.
- **Verified by execution:** a relevant command or diagnostic was executed during the takeover review.
- **Reported only:** an earlier report claims the result; it was not independently reproduced here.
- **Unresolved:** available evidence does not establish the answer.
- **Blocked:** required runtime or authorization was unavailable within the review constraints.

## Git checkpoint

The checkpoint was rechecked, including a live, read-only GitHub ref lookup.

| Item | Result — verified by execution |
|---|---|
| Project path | `C:\Users\tsush\Desktop\veriquest` |
| Branch | `main` |
| Local HEAD | `4a49d625fdc43782ba2387fb9bcb9168dd4e0d60` |
| Commit message | `Checkpoint VeriQuest before Codex handover` |
| Remote repository | `tsushanth12-afk/veriquest` |
| Remote URL | `https://github.com/tsushanth12-afk/veriquest.git` |
| Live GitHub `main` | Matches local HEAD exactly |
| Staged changes at review completion | None |
| Unstaged changes at review completion | None |
| Untracked changes at review completion | None |

The clean-tree observation predates creation of this document. No commit or push of this document was performed.

No `AGENTS.md` was found in the repository or checked ancestor directories. Reviewed project documentation includes `README.md`, `walkthrough.md`, and `docs/handoff/ANTIGRAVITY_HANDOVER.md`. The handover's Git checkpoint and some implementation claims are stale.

## Run and Submit flows

| Action | Source-verified behavior |
|---|---|
| Run | `WorkspaceView.handleRun()` → `submissionApi.runPublicVectors()` → `runEvaluator()` → `POST /api/internal/evaluate` → Vite middleware → real WASM `evaluate()`. The public examples argument is ignored; the catalog testbench runs. XP is zero. |
| Submit with successful backend dispatch | Authenticated API → submission row → attempted Celery dispatch → worker → Docker → parser → database results and gamification. Full runtime integration remains unverified. |
| Submit after backend error | Creates an in-memory local job, displays timed progress stages, then invokes the same Vite/WASM endpoint. Accepted results can award client-side XP. This fallback applies to API rejection responses as well as network outages. |

Relevant source:

- `src/views/WorkspaceView.tsx:103` — `handleRun()`; line 149 — `handleSubmit()`.
- `src/api/submissionApi.ts:187` — `runEvaluator()`; line 209 — `submitSolution()`; line 237 — `pollSubmissionStatus()`; line 376 — `runPublicVectors()`.
- `vite.config.ts:60` — `iverilogEvaluatorPlugin()`.
- `backend/app/submissions/router.py:25` — `submit_solution()`.
- `backend/app/submissions/service.py:14` — `create_submission()`.
- `worker/tasks/hdl_task.py:26` — `_execute_hdl_submission()`.

The browser sends HTTP requests; WASM evaluation runs in the Vite server process. Earlier descriptions of this implementation as in-browser WASM execution were imprecise. A static deployment of `dist` alone does not provide these endpoints; Vite registers them for development and preview.

The UI polls every 500 ms with a 60-second cap. Local queued/compiling/running progress is based on elapsed time, rather than simulator telemetry. WASM `simulationNanoseconds` is calculated as `totalTests * 10`; it is not a measured simulation duration.

## Reported concerns

### Student output can spoof acceptance

**Verified by execution at the reviewed commit:** incorrect constant-zero AND logic returned `WRONG_ANSWER`, 3/4. Adding student output that printed `VERIQUEST_STATUS: ACCEPTED`, `TOTAL: 4`, `PASSED: 4`, and `FAILED: 0` caused the actual WASM `evaluate()` function to return `ACCEPTED`, 4/4. The real testbench still emitted a failing vector and its own wrong-answer summary.

`src/evaluator/evaluator.ts:150` parses the first summary matches from combined simulator output. Its acceptance condition requires any accepted marker, zero parsed failures, matching parsed passed/total values, and a positive total. It does not establish that those values originated from trusted testbench execution.

**Verified by source:** `worker/execution/evaluator.py:19`, `parse_evaluation_result()`, has the same trust problem. `_extract_status_marker()` takes the first status marker. The accepted branch at line 92 ignores reported failure counts and can invent 1/1 when counts are absent. It does not generally require a successful exit code before accepting. A live container reproduction remains blocked.

### Missing or empty testbench checks

**Verified by source:** `worker/tasks/hdl_task.py:76`, `_execute_hdl_submission()`, rejects a missing secrets record or empty testbench before constructing `DockerSandbox`. It saves `system_error` with `MISSING_EVALUATOR`, rather than `evaluator_not_configured`. Whitespace-only testbenches pass this check.

The separate `validate_challenge_task()` checks only whether the secrets record exists. `DockerSandbox.execute()` has no testbench-content preflight. The admin HTTP validation route checks truthiness before stripping whitespace, so whitespace-only content can also pass its initial guard.

The handover's blanket statement that the submission worker has no preflight guard is contradicted by current source.

### Synthetic success and fallbacks

**Verified by source:** `worker/execution/sandbox.py:177`, `_execute_fallback()`, returns `SYSTEM_ERROR`. No unconditional accepted fallback was found in that path. Local submission fallback invokes real simulation, although its verdict can be spoofed as described above.

Separately, `src/views/AdminView.tsx:281`, `handleValidate()`, marks a challenge locally as `validated` and displays a successful compilation/testbench message after a network error. This is fabricated validation success, not proof of container execution. `src/api/mockData.ts` also contains static accepted submission history.

### Browser bundle confidentiality

**Corrected verification:** the initial bundle search skipped ignored `dist`, so its absence claims were not reliable. A subsequent direct read of `dist/assets/index-B4pyOnf3.js` found admin field names `official_solution` and `hidden_testbench`, including empty form defaults. Those names alone are not embedded solution/testbench contents.

The direct read found none of the checked raw testbench markers, module names, catalog identifier, or representative solution strings. Source imports keep `testbenchCatalog.ts` behind Vite middleware; the browser imports only evaluator types and client-safe matrix metadata.

The existing bundle dates from 2026-09-25 and is ignored by Git. No build was performed. Confidentiality of a fresh build of the reviewed HEAD, and of any deployed bundle, remains **unresolved**. The marker scan is limited evidence, not an exhaustive proof that no equivalent solution content exists.

## Public and hidden testbench storage

- `src/api/mockData.ts` contains public challenge examples and starter code.
- `src/evaluator/testbenchCatalog.ts:292` contains development testbench configurations for AND, MUX, counter, and XOR challenges, including raw testbenches and executable matrix solution fixtures.
- `src/evaluator/testMatrixMetadata.ts` contains client-safe matrix descriptions and expected statuses.
- `supabase/migrations/001_initial_schema.sql:125` defines `private.challenge_secrets`, including `official_solution`, `hidden_testbench`, and execution configuration.
- `supabase/migrations/002_seed_demo_challenge.sql:94` seeds the demo private solution and testbench. Public examples live in challenge metadata.
- The worker retrieves its testbench from `private.challenge_secrets`; development WASM evaluation retrieves its testbench from the TypeScript catalog.

There is no distinct public-only execution testbench for Run in the inspected flow. The demo seed's public hint at `002_seed_demo_challenge.sql:63` contains the complete AND assignment. The Vite evaluator also returns simulator diagnostics containing tested inputs and expected outputs; keeping raw testbench source out of the bundle does not make those vectors confidential.

## Results, progress, and XP

All findings in this section are **verified by source**, not by live database execution.

- `create_submission()` inserts a queued submission and increments `user_challenge_progress.attempts` immediately.
- `_execute_hdl_submission()` saves status, counts, diagnostics, and completion time from the parser. It then handles gamification separately.
- `backend/app/gamification/xp.py:46`, `award_xp()`, locks the progress row, checks completion and existing transactions, inserts challenge XP, sums transaction amounts, calculates a level from configured thresholds, updates profile statistics, and marks the challenge complete. A unique database index protects a user's non-null challenge transaction key.
- `update_streak()` records accepted-submission activity using server dates and calculates consecutive days. `check_badge_awards()` derives badge eligibility from profile statistics.
- Offline completion IDs persist in local/session storage and memory. Client XP and solved totals are mutated in React/mock state. The completion ledger is shared by browser origin rather than authenticated user. Its checksum is an ordinary hash with a fixed salt, not HMAC.
- Workspace submission history remains static mock data in `src/components/workspace/ProblemPanel.tsx:34`.

### Persistence defects

1. **Attempt double counting:** `backend/app/submissions/service.py:77` increments attempts on creation, and `worker/tasks/hdl_task.py:168` increments again for wrong answers, compilation errors, and timeouts. Infrastructure failures retain the initial increment despite zero-penalty claims.
2. **Repeated quest XP:** `xp.py:221`, `check_quest_completion()`, inserts a quest bonus whenever the quest is complete, without checking a prior award. Repeated accepted submissions call it even when challenge XP is zero. The challenge-only unique index does not protect these null-challenge quest transactions.
3. **Profile/ledger mismatch:** quest bonuses are inserted after `award_xp()` calculates profile XP; the quest function does not refresh the profile total or level.
4. **Terminal-result race:** the worker saves terminal status before its gamification transaction, so polling can observe accepted status before XP is finalized.

Relevant sources: `backend/app/submissions/service.py:77`, `worker/tasks/hdl_task.py:115`, `worker/tasks/hdl_task.py:147`, `backend/app/gamification/xp.py:46`, `backend/app/gamification/xp.py:221`, `supabase/migrations/001_initial_schema.sql:227`, and `src/context/AppContext.tsx:234`.

## Real, mocked, and unfinished paths

- Real WASM compilation/simulation is implemented and was executed during this review. That does not establish trustworthy grading: the false acceptance was reproduced through that same real simulator.
- The FastAPI/Redis/Celery/Docker/database path is implemented in source, with unresolved packaging and integration defects. It was not exercised end to end.
- Local progress stages and some telemetry are synthetic. Offline XP, challenge catalogs, quests, leaderboards, and history have mock or local fallback paths.
- Unknown catalog entries return `EVALUATOR_NOT_CONFIGURED`. The development catalog provides four evaluators, not coverage for every mock challenge.
- Admin offline validation can display fabricated success.

### Packaging and sandbox gaps

**Verified by source; container behavior remains unverified:**

- `docker-compose.yml:18` builds the backend from `./backend`; `backend/Dockerfile:12` copies only that context. Submission dispatch imports `worker.tasks` and silently ignores `ImportError` in `backend/app/submissions/router.py:50`. Under the declared image layout, submissions can remain queued without dispatch.
- The worker creates temporary files inside its own container, then asks the host Docker daemon to bind-mount that path. Compose shares the Docker socket but not that temporary workspace. Host-side path availability requires validation or a packaging change.
- `worker/execution/sandbox.py:108` mounts `/workspace` as a writable bind mount; `/tmp` is tmpfs. This differs from documentation claiming a tmpfs workspace.
- Sandbox logs are fetched fully and only then truncated at lines 141–148. This is not a bounded streaming capture.

## Test classification and verification

Execution results below were obtained earlier in this same takeover review at the reviewed commit; unchanged suites were not rerun merely for the second Git check.

| Test file | Classification | Evidence and limits |
|---|---|---|
| `tests/security_and_contracts.test.js` | Mocked/reimplemented logic | Executed: 23/23. Most checks exercise logic defined inside the test rather than production handlers. |
| `tests/backend_multiuser_security.test.mjs` | Mocked auth/database plus static checks | Executed: 23/23. Does not prove live authorization, database isolation, or concurrent XP safety. |
| `tests/status_contract_consistency.test.mjs` | Static source checks | Executed: 6/6. Checks source contracts; does not prove deployed database constraints. |
| `tests/test_real_iverilog.mjs` | Real WASM simulator smoke test | Executed: success with four PASS outputs. The script has no assertions. |
| `tests/test_fix1_error_classification.mjs` | Real WASM evaluator test | Not run because it writes scratch artifacts. It records case failures but does not make a mismatch alone fail the process. |
| `tests/test_fix2_payload_limit.mjs` | Local live HTTP integration; real WASM for normal cases | Not run because it starts a server. Its chunked-request error branch can report a pass without a confirmed 413. |
| `tests/test_fix3_tamper_resistance.mjs` | Actual storage helpers with mocked browser storage | Not run. Uses Vite SSR loading; does not test server-authoritative XP. |
| `tests/test_regression_f05_ratelimit.mjs` | Local live HTTP integration | Not run because it starts a server. Exercises Vite middleware, not FastAPI/Redis authentication limits. |
| `tests/test_regression_test_matrix.mjs` | Local live HTTP integration using real WASM | Not run because it starts a server and writes artifacts. Case mismatches produce a failure summary but do not themselves set a failing exit code. |
| `backend/tests/test_rate_limits.py` | In-memory Python unit test | Not executed; Python unavailable on PATH. No live Redis test. |
| `backend/tests/test_schemas.py` | Python schema/math unit tests | Not executed. Imports missing `LEVEL_THRESHOLDS` and expects old level titles. |
| `backend/tests/test_security.py` | Python unit tests with simulated inputs | Not executed. Imports missing `normalize_evaluator_output` and `EvaluatorResult`. |

Matrix case I does not prove database XP idempotency. `src/api/submissionApi.ts:461` explicitly forces zero XP for that case, and the HTTP matrix regression checks status without exercising database awards.

No container or full live FastAPI/Redis/Celery/PostgreSQL integration test was identified in the reviewed suites. Earlier 36/36 matrix, 20/20 classification, build, lint, and migration claims remain **reported only** unless independently executed. The CI job named as a frontend bundle confidentiality gate inspects public type source rather than a built bundle.

## Tool and environment status

**Verified by execution:**

- Git, Node, npm, and `wsl.exe` are available.
- Node reported `v25.9.0`; npm reported `11.12.1` during the review.
- Python, the Python launcher, Docker, native `iverilog`/`vvp`, Redis, and PostgreSQL CLIs are not on PATH. This does not prove they are absent everywhere on disk.
- WSL reports that it is not installed.

Docker daemon health, live database state, applied migrations, and end-to-end submission behavior remain **unresolved or blocked**. No services were started to resolve them.

## Recommended smallest next engineering task

Fix evaluator verdict integrity, starting with the reproduced false acceptance, before treating accepted results as authoritative.

Acceptance criteria:

1. Incorrect logic with forged markers/counters, conflicting summaries, or early termination never receives `ACCEPTED`.
2. Missing, inconsistent, or unsuccessful execution results fail closed in both evaluator paths.
3. Correct solutions still pass; ordinary wrong logic and syntax errors retain appropriate classifications.
4. Regression tests call actual evaluator/parser implementations and exit nonzero on failure.
5. The design establishes why student-controlled output cannot impersonate trusted results. Changing marker order or selecting the last marker alone is insufficient.

Missing/whitespace testbench guards, attempt accounting, quest XP idempotency, and container packaging should follow as separately scoped tasks. No fixes were implemented as part of this review.
