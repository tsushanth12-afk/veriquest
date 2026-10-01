# Live local Supabase authentication integration

Date: 2026-10-01 (Asia/Calcutta). Repository HEAD remains `a041524ac8babebde659cf85ee0e0c88889d53bd`.

## Outcome

**Passed the scoped live authentication gate.** One newly created disposable local Auth account signed in through actual Supabase Auth. Its real ES256 access token was validated through production authentication dependencies over TCP HTTP on Windows and in a Linux container. The live runner exited 0 with **40 assertions, 22 authentication HTTP cases, zero failed cases**. The generated-key regression suite separately passed **17 unittest methods**.

This does not verify the full VeriQuest backend, application database permissions, administrator role queries, dispatch, scoring, database transactions, grading containers or production readiness. No VeriQuest migrations, permissions, Supabase signing settings, existing accounts, commits, pushes or deployments were changed.

## Initial review and implementation corrections

Read the remediation report, current authentication/settings implementation, focused tests, relevant diff and authentication-patterns skill. No applicable AGENTS.md was found in the checked repository/ancestor locations. The skill guided credential-safe execution and separation of configured issuer identity from transport.

No concrete production defect requiring a correction was found in this focused review or reproduced by the integration. **Production authentication/configuration code and prior tests/reports were not modified during this task.** Existing restrictions were preserved: exact issuer, explicit ES256 local allow-list, signature verification, required claims, UUID subject, compatible unique key, scoped cache and bounded refresh, and strict optional credentials.

New reproducible test harness files:

- `tests/auth_live_integration.py`: opt-in local-only orchestration, private credential acquisition, account creation/sign-in/deletion, HTTP assertions, Docker lifecycle and cleanup.
- `tests/auth_live_runtime/service.py`: minimal FastAPI/Uvicorn HTTP service using production `get_current_user` and `get_optional_user`; wrong-issuer control invokes production dependency with deliberately wrong trusted settings.
- `tests/auth_live_runtime/Dockerfile`: separate temporary Linux authentication image; no application packaging changes.
- `tests/auth_live_runtime/requirements.txt`: pinned authentication-test dependencies matching this run's host versions.
- `docs/handoff/AUTH_LIVE_INTEGRATION_REPORT.md`: this report.

## Credentials and local account lifecycle

Only `http://127.0.0.1:54321` and named containers for project `veriquest-local-test` were used. The runner has a fixed local API target rather than an arbitrary hosted URL.

The local `.temp/start-secrets` read attempt failed with PermissionError. No value was emitted. Instead, the runner captured the local gateway declarative configuration through read-only Docker inspect/exec subprocesses and privately selected existing anon/service-role API credential candidates. Candidate role decoding only selected credentials; the actual local Auth API validated their authority. Credentials were never printed, persisted in test source/configuration, passed as command arguments, or supplied to the authentication test container environment.

A unique test email and a cryptographically random password were generated in memory. Account creation used supported `POST /auth/v1/admin/users` with email confirmation for this one account; no global signup/email policy was changed. Password sign-in used `POST /auth/v1/token?grant_type=password`. Both returned **200**. The returned Auth user ID was retained privately for subject comparison and exact deletion. No existing account was used.

Decoded user-token algorithm/issuer were initially observations only. They matched ES256 and `http://127.0.0.1:54321/auth/v1`. Subsequent production signature/claim validation and exact Auth-account subject comparison succeeded before this report treats them as validated. Passwords, tokens, API keys, test email and user ID are deliberately absent from this report and tool output. Uvicorn access logging was disabled; credentials travelled only through HTTP headers/body in process memory. Normal local Auth internals may retain their own operational account event records; those were not inspected or globally erased.

## Actual authentication HTTP results

Windows service: `127.0.0.1:51963`. Linux service published to `127.0.0.1:51971`. Requests below were real HTTPX TCP requests, **not TestClient/MockTransport**.

| Case | Route | Windows status | Linux status | Assertion |
| --- | --- | --- | --- | --- |
| Real user token, required | `/required` | 200 | 200 | Subject equals newly created Auth account |
| Real user token, optional | `/optional` | 200 | 200 | Same subject |
| No credentials, required | `/required` | 401 | 401 | Required auth rejects anonymous |
| No credentials, optional | `/optional` | 200 | 200 | Subject is null |
| Malformed Basic credentials, required | `/required` | 401 | 401 | No downgrade |
| Malformed Basic credentials, optional | `/optional` | 401 | 401 | No downgrade |
| Empty Authorization, required | `/required` | 401 | 401 | Rejected |
| Empty Authorization, optional | `/optional` | 401 | 401 | Rejected |
| Tampered token, required | `/required` | 401 | 401 | Modified payload retains original signature; rejected |
| Tampered token, optional | `/optional` | 401 | 401 | Rejected, not anonymous |
| Wrong configured issuer | `/wrong-issuer` | 401 | 401 | Real unmodified token rejected |

Forty counted assertions comprise seven local Auth/credential/token observations, fourteen HTTP status/subject assertions per environment, and five Linux/source/transport assertions. Cleanup statuses are recorded separately, not inflated into this assertion total. The 17 generated-key methods contain additional subcases; these are not counted as live requests or added to the live assertion total.

## Linux transport and source evidence

Docker server reported Linux, version 29.8.0. The test image targets Python 3.12 slim. The service reported platform Linux, not a host process masquerading as container evidence.

- Windows JWKS transport: `http://127.0.0.1:54321/auth/v1/.well-known/jwks.json`.
- Linux JWKS transport: `http://host.docker.internal:54321/auth/v1/.well-known/jwks.json`.
- Expected issuer in both: **exactly** `http://127.0.0.1:54321/auth/v1`.
- Linux `/jwks-probe` returned **200**, using production `_fetch_jwks` and compatible-key checks against real local Supabase. Container reachability was therefore observed, not assumed.
- Real-token HTTP verification then succeeded through that container transport.
- Host and Linux SHA256 for production `security.py` were identical: `46f166f18614ceac1cd6b785f0c7db486d80c48c1894bdb5d5ec9ca19c84d13d`.
- Backend source was mounted read-only. The container ran UID/GID 1000, read-only root, cap-drop ALL, no-new-privileges, 256 MB memory, one CPU, 64 PIDs and a restricted temporary filesystem.
- Docker socket was not mounted; both source inspection of the run command and the container service's socket-presence check support this. Auth networking was intentionally available; this is not an HDL sandbox isolation test.

## Commands and results (secrets omitted)

Repository working directory: `C:\Users\tsush\Desktop\veriquest`. `$Docker` below denotes the existing executable `C:\Users\tsush\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe`. `$TestImage`/`$TestContainer` are unique generated `vq-auth-live-*` identifiers, not credentials.

| Command/check | Exit/result |
| --- | --- |
| Git status, instruction/source/report reads and authentication diff review | Successful; prior changes preserved |
| `$Docker ps --format '{{.Names}}'`; server version query | 0; running local Supabase observed; Linux 29.8.0 |
| Private local `.temp/start-secrets` read | PermissionError; fallback acquisition used; no values emitted |
| Private Docker inspect/exec credential presence probes | 0; anon/service-role candidates present, values withheld |
| `.venv/Scripts/python.exe -m pip install uvicorn` | 0; installed only in ignored project venv, not global Python |
| `.venv/Scripts/python.exe -B tests/auth_live_integration.py --docker <existing Docker executable>` | **0; 40 assertions, all 22 HTTP cases passed** |
| Runner: `$Docker build --quiet -t $TestImage tests/auth_live_runtime` | 0; temporary image built before account creation |
| Runner: minimal Uvicorn host service in an owned thread with a pre-bound available socket | Started at 51963; no existing process stopped |
| Runner: `$Docker run -d --name $TestContainer --read-only --cap-drop=ALL --security-opt=no-new-privileges:true --memory=256m --cpus=1 --pids-limit=64 --tmpfs /tmp:rw,noexec,nosuid,size=16m -p 127.0.0.1::8080 --mount <backend read-only at /app/backend> -e JWT_ISSUER=<public local issuer> -e JWT_JWKS_URL=<public container transport> -e JWT_ALGORITHMS=ES256 $TestImage` | 0; actual Linux service reached at 51971; no secrets or socket in args/mounts |
| `.venv/Scripts/python.exe -B -m unittest discover -s tests -p test_auth_compatibility.py -v` | **0; 17 methods passed in 0.196 seconds** |
| `.venv/Scripts/python.exe -m pip check` | 0; no broken requirements |
| AST parse of new live-test Python files | 0 |
| `git diff --check` | 0; only LF/CRLF informational warnings |
| Limited secret-pattern scan of new harness files | 0; zero candidates for private-key PEM, GitHub tokens, AWS IDs or JWT literals; not an exhaustive secret guarantee |
| Independent Docker test-container/image inventory and local port probes | 0; no matching temporary container/image; ports 51963 and 51971 closed |

Focused suite uses generated in-memory signing keys and controlled JWKS HTTP transport; those are **regressions**, not real Supabase login. The live runner does not mock Auth, JWKS, production verification or TCP requests.

Host and Linux dependency versions observed through their service health responses:

| Dependency | Both environments |
| --- | --- |
| FastAPI | 0.142.2 |
| Uvicorn | 0.54.0 |
| python-jose | 3.5.0 |
| cryptography | 50.0.2 |
| HTTPX | 0.28.1 |
| Pydantic | 2.13.5 |
| pydantic-settings | 2.15.0 |

Generated-key TestClient run emitted the already known Starlette HTTPX deprecation warning; no tests failed and no additional HTTPX2 installation was attempted.

## Cleanup

Runner finally-cleanup and independent follow-up checks confirmed:

- Owned Windows service thread stopped; its socket closed.
- Temporary Linux container removed with exact unique name.
- Temporary tagged image removed.
- Disposable account deleted through supported local Auth administration DELETE: **200**.
- Follow-up administration GET for that exact account: **404**.
- Supabase Auth health remained **200** after cleanup and on independent recheck.
- The ten existing Supabase containers remained running, with vector/logflare absent as initially observed.
- Both temporary listener ports were closed.

No cleanup failure was observed. Shared Docker base images/build cache may remain; no broad prune or deletion of pre-existing images was attempted. The test source and ignored project venv are retained for reproducibility, not running services. Deleting the account does not prove stateless access-token revocation; no post-delete revocation claim is made.

## Scope limits and next gate

Verified: generated-key security regressions; actual local Supabase password sign-in; real-token production verification and negative HTTP controls; independent Linux verification with observed JWKS transport; scoped cleanup.

Not verified: actual packaged VeriQuest API startup/routing, application profile creation, DB grants/RLS, student/admin privileges, session/key revocation, production TLS/proxies, multi-user state isolation, Celery/Redis dispatch, scoring, native grading sandbox or production readiness. The test container is a minimal auth service, not `backend/Dockerfile` or the application Compose backend. No full backend pytest claim is made.

Recommended next task: make the actual packaged API start and its API-to-worker dispatch contract testable, while preparing a separately reviewed disposable-database permission/migration validation gate. Do not treat this successful authentication gate as authorization to apply migrations or repair unrelated components automatically.

## Repository state

All changes remain unstaged, uncommitted and unpushed. Pre-existing pending modifications remain `.env.example`, `backend/app/core/config.py`, `backend/app/core/security.py`; prior untracked remediation/environment reports and generated-key test remain. This task adds only the four live harness files and this report. No credentials, image dependencies or venv contents are intended for Git.
