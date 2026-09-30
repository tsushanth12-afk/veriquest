# Milestone 1: scoring authority and truthful frontend failures

Date: 2026-09-30. Repository: `C:\Users\tsush\Desktop\veriquest`. Baseline: main at `7c644a921362aad9a680e7567e6e92fcd4e7299c`.

## Outcome and scope

Implemented VQ-AUD-04 and the frontend portion of VQ-AUD-08. Scored Submit has no local fallback, client completion ledger, or local XP award. Local WASM practice remains available through an explicitly labelled Run action, with zero XP and no scored completion. Matrix/reference execution is likewise unscored. Admin failures no longer fabricate saved, validated, published, or unpublished state; server-created IDs are retained.

Local verification passed. Live account/database/admin workflows and the native production pipeline remain unverified. This is not a database permission fix, an XP algorithm fix, or production-readiness certification.

Initial Git status contained only the untracked comprehensive audit. No applicable AGENTS.md was found in the repository or checked ancestors. The complete relevant findings and production adapters, AppContext, workspace, admin UI, navigation, Supabase session integration, profile response schema, and backend role enforcement were inspected before implementation. The authentication-patterns skill guided identity-generation checks and least-privilege UI gating; the browser-automation skill guided visible UI checks. No backend authorization was weakened.

## Before / after

| Area | Before | After / production references |
| --- | --- | --- |
| Scored submission | Six API errors and exceptions created local jobs that could accept and award XP | `submissionApi.submitSolution` requires an active identity and backend submission ID; errors reject. No local job map exists |
| Polling | Backend polling errors fell through to misleading local queued states | `pollSubmissionStatus` returns backend result fields or rejects; no local poll path |
| Practice | Local fallback could be presented as scored server success | `runPublicVectors` remains real HTTP WASM, explicitly unscored; workspace/app/editor label the boundary |
| Matrix | Correct reference fixtures could mark student completion and award XP | `runTestMatrixCase` always returns xpEarned=0 and performs no completion writes |
| Account profile | Failed profile load merged old stats into a new identity; awardXP mutated MOCK_USER | `emptyProfile` creates zero/unavailable progress for a fresh identity; `loadProfile` accepts only current matching server identity; awardXP removed |
| Delayed work | Old account responses could update current views or scoring | `sessionBoundary` generation/identity checks, API token-subject matching, workspace operation checks, keyed user views/auth modal |
| Cached previews | Authenticated errors/empty responses could display fixture completions, quests/badges/ranks | Authenticated catalog/leaderboard failures return empty, successful empty lists remain empty; quests/badges do not fall back to earned fixtures; anonymous catalog has no solved flags/attempts |
| Admin authorization | Editable metadata granted UI; anonymous navigation/routes exposed controls | Successful backend-authorized admin list check grants isAdmin; navigation, route, component and mutating handlers gate it |
| Admin lifecycle | Network errors and exceptions invented success | `requireApiData`, session checks, error toasts, persisted-state refresh; no fake validation or fixture audit logs |
| Admin creation | Server UUID discarded for a timestamp ID | `handleCreateOrUpdate` retains challenge_id; edit/update/validate/publish/unpublish target that ID |

### Trust and session details

Backend APIs alone own authenticated results, XP and progress. Workspace acceptance triggers a server profile refresh; it never increments stats locally, and never claims “Server progress updated.” xpEarned on scored results is the backend xp_awarded field, not a frontend reward calculation.

Practice is a deliberate Run action rather than an automatic response to an API error. The anonymous preview is prominently labelled sample data/unscored. Authenticated users may also choose Run, but it cannot affect their account stats. This remains the existing restricted WASM catalog grader, not a new public-testbench architecture; the public-versus-hidden Run concern remains separate.

`changeSessionIdentity` advances a host-side generation on account changes and explicit logout. Expected identity/generation is captured before requests and checked before applying results. The API wrapper checks SDK token subject against expected identity, never attaches retained SDK tokens while logged out, and rejects responses from prior generations. A 401 refresh retry preserves the real subsequent failure (e.g. FORBIDDEN), rather than relabelling it UNAUTHORIZED.

Account transitions clear profile/role/toasts/search/active challenge/auth dialog state. `AppContent` keys the view subtree and auth modal by generation, disposing component-local caches and old forms. Workspace additionally invalidates operations on navigation/unmount and checks the session before status/results/toasts/profile refresh. Polling is serialized through setTimeout after each response rather than overlapping async intervals. In-flight network work is invalidated, not forcibly aborted; hung-request deadlines are still a separate issue.

The old origin-wide completion/checksum/session ledgers are no longer read or written. Existing legacy browser keys are left inert rather than deleted; they cannot establish scored completion. Authenticated challenge badges come from backend challenge responses. Dashboard rank/badge previews no longer invent earned fixture values, and aggregate solved count no longer establishes AND-demo completion. ChallengeHistoryTable does not fetch authenticated history while logged out.

Admin role is established through the existing backend admin-list endpoint, which enforces its database role check. Neither user_metadata nor app_metadata is used to grant the UI. This adds a read-only admin probe per authenticated auth event; an unavailable/forbidden probe fails closed. Backend checks remain the real security boundary.

Lifecycle actions require successful data/status, then refresh the actual challenge list. A refresh failure displays an error and retains previously loaded state; a confirmed mutation may still be acknowledged as a backend operation, without inventing a new lifecycle state. Create uses the backend-created ID and constructs its newly confirmed draft row. Real persisted publication/validation semantics, including the existing backend unpublish inconsistency, remain outside this frontend fix.

## Executed verification

All checks used installed dependencies. Assertions throw or reject on failure and Node exits nonzero. No live sessions were created; no real admin data was mutated.

| Command / check | Exit | Actual evidence |
| --- | ---: | --- |
| `node tests/scoring_authority.test.mjs` | 0 | Final 127 counted production adapter/component assertions; real HTTP WASM practice and matrix |
| `node tests/test_fix3_tamper_resistance.mjs` | 0 | Historical entry point now imports the same production scoring-authority suite, replacing obsolete client-ledger tests; final 127 assertions. Not an additional unique suite |
| `node tests/security_and_contracts.test.js` | 0 | 23/23 existing static/reimplemented/mock checks; not live security evidence |
| `node tests/backend_multiuser_security.test.mjs` | 0 | 23/23 existing static/mock checks; not live DB/auth evidence |
| `node tests/status_contract_consistency.test.mjs` | 0 | 6/6 static contract checks |
| `node tests/test_fix2_payload_limit.mjs` | 0 | Actual HTTP: three oversized cases returned 413, including observed chunked 413; all four catalog solutions HTTP 200 ACCEPTED: AND4/4, mux8/8, counter20/20, XOR4/4 |
| `node node_modules/typescript/bin/tsc -p tsconfig.app.json --noEmit` | 0 | Final application type check |
| `node node_modules/typescript/bin/tsc -p tsconfig.node.json --noEmit` | 0 | Node/Vite configuration type check |
| Focused `node node_modules/oxlint/bin/oxlint <changed source/test paths>` | 0 | Nine warnings on the last full run: unused catch variables, mixed useApp export, effect state updates/ref cleanup. No lint errors; success does not mean warning-free |
| Vite production build to fresh temporary directory | 0 | Final 1,970 modules; 638.26KB JS; existing chunk-size warning. Repository dist preserved |
| Git diff/whitespace/scope checks | 0 | No staged files; no backend/worker/migration/grading-protocol/manifests/lockfile/historical verdict-report changes |
| Final localhost cleanup probes | 0 | Browser servers 60976 and 62907, test port 5199 and checked ephemeral focused-test ports closed |

Focused lint covered App, adapters/helpers, AppContext/profileState, WorkspaceView/AdminView, navigation/editor, dashboard Activity/Hero/History, user type, and both scoring tests. Type checks were rerun after the final account-reset changes. The build command used an in-memory Node mkdtemp/spawnSync wrapper to run `node node_modules/vite/bin/vite.js build --outDir <fresh directory>` without overwriting existing dist.

### Focused suite coverage and limitations

The suite imports production modules through Vite SSR and directly invokes production adapter functions and component callbacks. A minimal React hook dispatcher supplies state/effect/context during component checks. This does not replace full browser reconciliation, StrictMode coverage, or live authentication. It is explicitly a simulated session/component test, not a reimplementation of the adapters.

Coverage includes:

- UNAUTHORIZED, FORBIDDEN, VALIDATION_ERROR, RATE_LIMITED, SYSTEM_ERROR, NETWORK_ERROR, and unexpected exceptions for submission and polling; no local evaluator dispatch on those failures.
- Successful backend ID/result/XP mapping and actual Workspace acceptance triggering a server profile refresh.
- Real HTTP WASM correct practice and correct reference matrix, both with zero XP, unchanged fixture profile, and removed completion-ledger exports.
- A → immediate logout → B; delayed A profile, delayed logout completion, delayed submission/poll and delayed Workspace accepted response. None replaces B's profile or refreshes/toasts from old scoring work.
- Rejection of editable role metadata and acceptance of a successful simulated backend authorization probe; direct admin route/component/sidebar gating and generation-keyed user subtree.
- Seven failure modes across create/update/validate/publish/unpublish, asserting unchanged lifecycle and no success toast.
- Actual server-created ID retained, then used by edit, update, validate, publish and unpublish callbacks.
- Production fetch wrapper retaining FORBIDDEN after a 401 refresh, rejecting delayed old-session HTTP results, and refusing wrong-identity/logged-out SDK tokens.
- Authenticated catalog failures do not produce fixture progress; anonymous fixture completions/attempts are zero; unavailable badges/rank and demo completion are not inferred from fixture or aggregate stats.

The count reports 127 explicit counted assertions; guard assertions also throw on missing controls. Repeated successful runs are not added together as distinct coverage. Early implementation checks failed on missing variables/type inference and tests exposed a conditional publish-fixture mismatch and a missing component-level admin gate; these were corrected before final passing runs. Failures exited 1 and temporary servers closed in finally.

### Browser evidence

Temporary Vite servers used existing createServer configuration, host127.0.0.1, port0; actual assigned ports were 60976 and final62907. The startup command was `node --input-type=module -e "import {createServer} from 'vite'; ... await server.listen(); ..."`. No unrelated process was stopped.

Observed in the real browser:

- Guest dashboard: practice-preview banner, zero XP/solved stats, no Admin navigation.
- Start Demo workspace: explicit Run zero-XP/no-completion versus authenticated backend Submit text.
- Guest Submit: sign-in dialog and truthful sign-in-for-scoring message; terminal stayed IDLE, no local submission was created.
- Actual Run with unchanged undriven starter: WRONG_ANSWER0/4 with real simulator diagnostics/redacted grader token; no XP/progress awarded.
- Dashboard after Run: zero XP/solved, practice zero-XP text, rank unavailable and server badges unavailable.
- Final fresh browser load at62907 rendered normally; browser error log query returned an empty list.

While editing the initial dev session, exporting emptyProfile from AppContext caused Fast Refresh invalidation and a useApp/context error. The helper was moved to profileState.ts; the suite/typechecks/build and fresh browser load passed afterward. General hot-edit behavior of the pre-existing mixed AppContext/useApp module was not exhaustively verified and still has a lint warning. This report does not treat the earlier hot-reload error as a passing browser check.

No live authenticated B login or privileged admin UI workflow was performed. Those are simulated production-component tests only. No credentials, internal execution token, or external write was used to make tests pass.

Unchanged verdict-integrity security, parser, bounded-worker and full attack-suite evidence is reused from the prior milestone reports. No grader/protocol changes were made; repeating the full expensive forgery/overflow/timeout sweep was unnecessary for this frontend milestone.

## Changed files and repository state

Modified:

1. src/App.tsx
2. src/api/challengeApi.ts
3. src/api/client.ts
4. src/api/questApi.ts
5. src/api/submissionApi.ts
6. src/components/dashboard/ActivityCard.tsx
7. src/components/dashboard/ChallengeHistoryTable.tsx
8. src/components/dashboard/HeroQuestCard.tsx
9. src/components/layout/AppSidebar.tsx
10. src/components/layout/MobileNav.tsx
11. src/components/workspace/CodeEditor.tsx
12. src/context/AppContext.tsx
13. src/types/user.ts
14. src/views/AdminView.tsx
15. src/views/WorkspaceView.tsx
16. tests/test_fix3_tamper_resistance.mjs

New:

1. src/api/requireApiData.ts
2. src/api/sessionBoundary.ts
3. src/context/profileState.ts
4. tests/scoring_authority.test.mjs
5. docs/handoff/SCORING_AUTHORITY_FIX_REPORT.md

Preserved pre-existing untracked file: docs/handoff/PROJECT_COMPREHENSIVE_AUDIT.md. Its SHA256 is `0E010C0125C426BDDD76B9B91EE088E7CD29A4C65D06953912CF7B4D544C97AE`; this task did not edit it. Existing handoff reports remain unchanged.

Final state: main/HEAD unchanged; zero staged files; the16 modified files above unstaged; the5 new files plus the preserved audit untracked. No commits or pushes. No dependencies installed, external data changed, migrations applied, or deployment performed. Only frontend adapter/state/UI/type and focused-test/report files were changed. Most diff deletion removes fallback jobs, ledgers and fabricated admin success.

## Cleanup and remaining gates

Both browser tabs created for this task were closed. Server sessions86785/12667 were stopped with Ctrl-C (expected exit1); focused and payload-test servers close in finally, including failed test runs. Checked temporary ports were independently closed. No unrelated process was terminated.

Fresh builds remain outside the repository at temporary directories including `C:\Users\tsush\AppData\Local\Temp\veriquest-scoring-qIQq0U`, `veriquest-scoring-final-0CkjPE`, and final `veriquest-scoring-verified-0SAZRb`. No generated build/dependency files were added to Git; existing dist/scratch evidence was not overwritten.

Remaining limitations:

- VQ-AUD-01 database grants/protected-column permission gap is untouched.
- Dispatch/image/workspace, real Docker execution, finalized accounting/XP algorithms, queue recovery and revision lifecycle are untouched. Backend provisional acceptance/XP timing can still produce stale server totals; the frontend now reports them without compensating locally.
- Live Supabase sessions, applied DB roles, authorized admin creation/publication/reload persistence, and real multi-tab auth event ordering need an existing configured integration environment. No such environment was provisioned or externally mutated here.
- HTTP requests lack a full abort/deadline mechanism. Session invalidation prevents stale UI application but does not cancel backend work already submitted or a pending transport.
- Legacy ledger keys are inert but not deleted. Anonymous sample leaderboard/catalog data remains explicitly labelled preview; this is not persisted progress.
- Local Run still uses the four-question catalog/full bench, not a generalized server-defined public-run bench for newly authored questions. That backend/content milestone remains required.
- Activity heatmap/history-contract and wider product audit findings are not all repaired. This milestone does not certify curriculum completeness, accessibility, or production readiness.
- The new focused suite is an explicit command and is not yet wired into CI; existing mock suites cannot prove production security.

Recommended next milestone: implement the API-to-worker named task/dispatch contract and startup tests from the audit, then validate native Docker workspaces before repairing and verifying final transactional accounting. Preserve the local WASM verdict-integrity checkpoint and this stricter frontend authority boundary.
