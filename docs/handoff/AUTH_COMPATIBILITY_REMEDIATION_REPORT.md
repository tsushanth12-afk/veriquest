# JWT compatibility remediation

Date: 2026-10-01 (Asia/Calcutta). Baseline HEAD: `a041524ac8babebde659cf85ee0e0c88889d53bd`.

## Outcome and evidence boundary

Implemented strict configured ES256/RS256 verification and consistent required/optional authentication. Final focused run: **17 unittest methods passed**, including parameterized negative cases, with real cryptographic signatures and production verifier/dependencies. Six existing static status-contract checks also passed. The production JWKS fetcher read and validated the local Supabase ES256 public key. **No real Supabase-issued user token was exercised; end-to-end authentication is not verified.**

No account creation, Supabase configuration/signing-key change, migration, database connection, deployment, commit or push occurred. No services were started. Existing untracked `BACKEND_VALIDATION_ENVIRONMENT_ASSESSMENT.md` was preserved byte-for-byte (SHA256 `1eaa317a3507d8d085e9aa270e9c0ea50e6f2218932e17e277a2be33ae68c08f`). Applicable instructions, current auth/settings/dependencies/environment example and relevant comprehensive audit findings were inspected. No applicable AGENTS.md was found in checked locations. The prior authentication review was supplied in conversation rather than a saved standalone review file.

The authentication-patterns skill informed the configured trust boundary, credential-safe diagnostics and explicit rotation/cache policy. It did not authorize external mutations.

## Files and functions changed

| File | Changes |
| --- | --- |
| `backend/app/core/config.py` | Settings adds independent issuer/JWKS transport, explicit algorithm list, expected audience and clock tolerance. Validators reject empty/unsupported/duplicate algorithms, invalid URL configuration, empty audience and tolerance outside 0..60 seconds. Issuer is not normalized. |
| `backend/app/core/security.py` | `verify_supabase_jwt` verifies signatures and required claims; `_find_key` validates a unique compatible public key; `_material` checks key encoding/material; `_validate_jwks` validates structure/cardinality/unique IDs; `_fetch_jwks` bounds transport; `get_jwks` isolates cache and bounds refreshes; `_authenticate`, `get_current_user`, `get_optional_user` share strict header handling and offload verification. `require_admin` remains an authentication marker; existing route-level DB checks are untouched. |
| `.env.example` | Documents safe local JWT configuration and container transport distinction. Existing unrelated example settings retained. |
| `tests/test_auth_compatibility.py` | New production-calling generated-key regression suite with controlled HTTP transport and in-process FastAPI test routes. |
| `docs/handoff/AUTH_COMPATIBILITY_REMEDIATION_REPORT.md` | This report. |

## Configuration and compatibility changes

Safe local defaults/example values:

```env
JWT_ISSUER=http://127.0.0.1:54321/auth/v1
JWT_JWKS_URL=http://127.0.0.1:54321/auth/v1/.well-known/jwks.json
JWT_ALGORITHMS=ES256
JWT_AUDIENCE=authenticated
JWT_CLOCK_TOLERANCE_SECONDS=30
```

Container JWKS transport can be configured as `http://host.docker.internal:54321/auth/v1/.well-known/jwks.json` after verifying reachability; **issuer must remain exactly the declared public issuer**. No actual environment file or Supabase config was edited. JWT issuer/JWKS no longer derive implicitly from SUPABASE_URL. Hosted users must configure both explicitly. RS256 works only when explicitly selected, e.g. `JWT_ALGORITHMS=RS256` or an intentionally approved `ES256,RS256` list. Header/JWKS algorithms never expand that list.

Claims require exact issuer, configured audience membership, integer nonnegative expiry, and canonical hyphenated UUID subject (case-insensitive representation; nil UUID rejected). Supplied nbf/iat must be nonnegative integers; nbf is time-validated. Booleans, numeric strings, fractional dates and malformed identity types are rejected. Email/role must be strings if supplied. A documented 30-second tolerance applies to expiry/not-before; it can be configured within 0..60 seconds. Optional routes allow anonymous only when Authorization is absent; empty, malformed, duplicate or invalid supplied credentials return 401. Signature verification stays enabled.

Keys require exact alg, matching kty, P-256 for ES256, valid coordinate lengths/points through material and crypto validation, or RSA modulus at least 2048 bits with a valid odd exponent. Supplied use must be sig; supplied key_ops must be exactly [verify]. Private/symmetric key material is rejected. JWKS alg metadata is required, a deliberate strictness change. Key documents allow 1..64 uniquely identified keys. Token length is bounded to 16,384 characters and kid length to 256.

## Cache and transport design

- Cache identity includes trusted URL, issuer, audience, algorithms and tolerance; maximum 16 entries, one-hour TTL.
- One serialized refresh attempt per configuration per 30 seconds, including failed attempts. Concurrent/random unknown kids cannot trigger an unbounded fetch storm.
- Initial fetch starts the cooldown. An immediately rotated unknown key may consequently be rejected until cooldown expires; this is intentional fail-closed availability behavior.
- Failed fetch/malformed response fails the requesting authentication. Expired cached keys are never accepted as an outage fallback. Previously valid, still-fresh cache entries may continue serving known keys within their TTL.
- HTTPX uses explicit five-second operation timeouts, no redirects, no environment proxy selection and a 65,536-byte retained response bound. An elapsed ten-second check runs between body chunks; this is not a hard cancellation timer around every blocking operation.
- Async dependencies run synchronous verification/fetching in Starlette's threadpool. A process-local lock prevents concurrent refresh races. No token/response-body/URL exception contents are logged.

## Executed commands and actual results

Commands ran from repository root unless noted. Python environment is ignored `.venv`, not global Python.

| Command/check | Exit | Result |
| --- | --- | --- |
| Git/instruction/source reads | 0 (rg without matches can return 1) | Baseline inspected; only pre-existing environment report untracked |
| Bundled Python `-m venv .venv-auth-tests`; move new environment to `.venv` | 0 | Newly created isolated environment; checked destination absent before move |
| `.venv/Scripts/python.exe -m pip install fastapi pydantic-settings 'python-jose[cryptography]' httpx` | 1 initially, then 0 outside sandbox | Initial download blocked by socket restrictions; approved retry installed only in project venv |
| `.venv/Scripts/python.exe -B -m unittest discover -s tests -p test_auth_compatibility.py -v` | 0 | Initial 15 methods passed; final expanded 17 methods passed in 0.187 seconds, zero failures |
| `.venv/Scripts/python.exe -m pip check` | 0 | No broken requirements |
| `.venv/Scripts/python.exe -B -m pytest backend/tests -p no:cacheprovider` | 1 | Blocked: no pytest in isolated auth environment; broader backend tests not executed |
| Python AST parse of backend/worker plus new test | 0 | 39 files parsed; syntax evidence, not whole-stack import/startup proof |
| Production live JWKS probe, backend cwd | 0 | `_fetch_jwks(Settings(_env_file=None).jwt_jwks_url)` and `_find_key` validated live ES256 public key; no token/authenticated account |
| `node tests/status_contract_consistency.test.mjs` | 0 | 6/6 existing static checks; not database execution evidence |
| `git diff --check` | 0 | No whitespace errors; Git emitted LF/CRLF informational warnings |
| Limited secret-pattern scan of changed source/example/test | 0 | Zero PEM private key, GitHub token, AWS ID or JWT-literal candidates; not an exhaustive secret guarantee |
| Existing environment report hash | 0 | Unchanged |

Live probe command (no key material printed):

```powershell
# Run from backend; use absolute path to project venv Python.
& 'C:\Users\tsush\Desktop\veriquest\.venv\Scripts\python.exe' -B -c "from app.core.security import _fetch_jwks,_find_key; from app.core.config import Settings; s=Settings(_env_file=None); doc=_fetch_jwks(s.jwt_jwks_url); key=doc['keys'][0]; _find_key(doc,key['kid'],'ES256'); print('Live JWKS: structure and ES256 public-key compatibility verified; no token tested')"
```

Installed auth-test versions: python-jose 3.5.0, cryptography 50.0.2, FastAPI 0.142.2, HTTPX 0.28.1, Pydantic 2.13.5, pydantic-settings 2.15.0. A Starlette TestClient deprecation warning recommends HTTPX2; tests still pass. No new dependency declaration is needed for ES256. Requirements remain unpinned; this run does not prove behavior of every lower-bounded version.

## Regression scope

Seventeen methods exercise valid ES256 and audience-list acceptance; explicit RSA acceptance/disallowing; tampering/wrong signatures/none/HS256/other algorithms; missing/malformed/expired exp; issuer/audience/subject negative matrices; future/malformed nbf and tolerance positives; incompatible EC/RSA metadata/material; malformed/duplicate/oversized JWKS; HTTP error/connection/timeout failures; endpoint/config cache isolation; sequential/concurrent unknown-key cooldown; actual rotation refresh; TTL failure/recovery; bad configuration; malformed headers/identity claims; real production dependencies through in-process FastAPI required/optional routes; and event-loop thread offloading.

Transport is controlled using HTTPX MockTransport while `_fetch_jwks`, verifier, signature library and dependency implementations remain real. Test keys exist only in memory. unittest assertions raise and make the command fail nonzero; subcases are not inflated into a claimed independent assertion total. No running HTTP service, external account or database is involved in the focused suite.

## Remaining limits and exact next live test

Full backend startup/test collection remains unverified; the isolated environment intentionally installs only auth dependencies. Existing audit test-fixture/import problems, rate-limit/proxy issues, issuer deployment configuration, live permissions, dispatch, scoring and Docker workspace defects are not fixed here. Cached key revocation can take up to TTL; there is no online session-revocation check. The serialized lock may delay other configurations during an outage, although it does not block the async event loop. Container-to-Auth reachability is unresolved.

Next, under explicit authorization, use one disposable Supabase student account (or an explicitly authorized existing test account), obtain its ES256 access token through actual Auth, keep it only in memory and submit it to a minimal HTTP route using production `get_current_user`. Assert returned subject matches the Auth user; run optional anonymous and invalid-token rejection controls. Do not log token/password/email. Repeat using a container-reachable JWKS URL while preserving the same exact issuer, and observe real fetch/rejection behavior. This first step need not touch application scoring or database rows. Database/API role validation is a separate subsequent gate. No account was created in this milestone.

## Final repository state

Intended modifications: `.env.example`, `backend/app/core/config.py`, `backend/app/core/security.py`. New focused test and this report are untracked. Pre-existing environment assessment remains untracked and unchanged. `.venv` is ignored and retained for reproducibility; no dependency files or generated packages are intended for commit. All changes remain unstaged, uncommitted and unpushed.
