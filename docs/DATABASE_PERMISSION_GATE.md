# Local database permission gate

The disposable veriquest-local-test database now has tracked 001/003/004/005;
see docs/handoff/DATABASE_LIVE_PERMISSION_REPORT.md for actual live evidence and
limitations. Do not rerun fresh bootstrap/application on this completed target.
Historical 001/002/003 are unchanged. Write commands still require authorization.
Never run a Supabase reset, automatic seed, hosted fallback or manual ledger edit.

## Boundary and source

`tools/database_policy.json` is the exact table/column permission specification.
The migration grants and runner assertions match it. `004_permission_gate.sql`
removes all legacy application policies and table/column grants before granting
only reviewed commands. Every application table has RLS. Clients can read public
published/nonarchived curriculum, active definitions/visible links, or their own
private records. Only own display_name/bio/avatar_url updates are granted.

`vq_owner` is NOLOGIN/NOINHERIT, owns the application schema objects and the
private migration ledger, and intentionally bypasses its own non-FORCE RLS inside
the two narrowly coded SECURITY DEFINER triggers. Only the existing migration
operator supabase_admin receives owner membership. Neither runtime role nor
authenticator/client roles receive service/owner memberships.

`vq_api` and `vq_worker` are distinct LOGIN/NOINHERIT roles with no superuser,
BYPASSRLS, role/DB creation, replication, ownership or elevated membership.
Command-specific RLS grants static all-user service authority for exactly their
column ACLs. HTTP ownership/admin checks are still essential. The API pool includes
admin authoring access by current architecture; separating that pool is future work.
API insertion is queued-only without execution evidence/XP; failure updates are
queued/system_error only. A trigger prevents its progress upsert from inventing
completion. The worker can score, but cannot change input/identity, publish, author
secrets or read private notes/roles/audit history. Permissions do not prove grading
or accounting correctness.

Private helpers have fixed empty search_path, qualified references and no client
or runtime EXECUTE. Trigger execution is attached by the owner, not a client RPC.
Signup uses `vq_user_` plus all 32 UUID hex digits, bounded string display metadata
(100 chars, trimmed; malformed/empty -> Student), zero scoring and literal student
role. Idempotent conflict handling does not overwrite existing stats or role grants.
Display edit limits: name 100, bio 2000, avatar URL 2048 characters; null allowed.
Existing users/collisions/invalid display rows block the fresh installer rather than
silently backfilling, renaming or modifying identities.

## Nonmutating commands

In PowerShell at `C:\Users\tsush\Desktop\veriquest`:

```powershell
$databaseGateDocker = 'C:\Users\tsush\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe'
.venv/Scripts/python.exe -B tools/database_gate.py --docker $databaseGateDocker --mode plan
.venv/Scripts/python.exe -B tools/database_gate.py --docker $databaseGateDocker --mode preflight
.venv/Scripts/python.exe -B tests/test_database_gate.py
```

The exact local project/workdir, named DB/REST containers, host port 54322 and
exposed schemas public/graphql_public are checked. No user-supplied DSN or hosted
target exists. Preflight queries are explicit READ ONLY transactions with ROLLBACK,
returning structure/counts only. It fails on unknown/partial states, changed ledger
hashes, unexpected objects, existing users without profiles or reserved collisions.
The named platform operator uses a container-local Unix socket; if unavailable,
stop rather than guessing another privileged connection.

## Separately authorized rehearsal and application

First review the diff/manifest and separately authorize the isolated rehearsal.
It needs no snapshot of, or connection to, the existing disposable project.
A recoverable **local-only snapshot** is a separate prerequisite for later real
application; snapshot creation/restoration is not automated here. Never reset the
running project as recovery. Run the isolated rehearsal:

```powershell
.venv/Scripts/python.exe -B tools/database_rehearsal.py --docker $databaseGateDocker --authorize-isolated-rehearsal
```

This inspects the already-present PG17 image, refuses image-declared persistent
volumes, and runs its immutable local image ID (`--pull never`) in a unique
network-none/no-port container with non-root PostgreSQL and a tmpfs database. Its
minimal Auth/platform stubs are **not** real Supabase. It calls the production
bootstrap/apply/assertion generators. The expected injected precommit error must
match its exact SQLSTATE and message, not merely a nonzero exit. It checks no
application objects/ledger/temp Auth rights remain, then correct apply, tracked
replay and changed-checksum rejection. Replay compares schema definitions, column
ACLs/defaults and all application/ledger rows, including after fixture writes.
`tests/database_rehearsal_operations.py` prepares unchanged static SQL extracted
from production functions and executes native trigger, RLS/column boundary,
mixed-write, ON CONFLICT, RETURNING and row-lock cases. Denied writes are compared
against privileged before/after state digests. API/worker sessions actually log
in as their SQL roles; client proxies inherit only the respective Data API roles.
Socket trust auth and a controlled auth.uid() stub are not real Supabase logins
or PostgREST permission proof. Docker inspection validates isolation before and
after, and confirms the exact container is absent after finally cleanup.
See DATABASE_ISOLATED_REHEARSAL_REPORT.md in docs/handoff for executed evidence,
failed attempts/corrections and limitations. Treat any failure as a stop.

For the current empty disposable project only, after separate explicit approval:

```powershell
.venv/Scripts/python.exe -B tools/database_gate.py --docker $databaseGateDocker --mode bootstrap --authorize-local-write
.venv/Scripts/python.exe -B tools/database_gate.py --docker $databaseGateDocker --mode apply --authorize-local-write
.venv/Scripts/python.exe -B tools/database_gate.py --docker $databaseGateDocker --mode preflight
```

Bootstrap privately prompts for distinct 32..128 nonspace printable ASCII passwords.
Store them in your password manager, not this repository/terminal history. It sends
only generated SCRAM verifiers through binary stdin, captures diagnostics privately
and turns off statement/error-statement logging in that transaction before role DDL.
Verifiers remain sensitive DB authentication material. Existing roles cause refusal,
not password rotation. The operator remains privileged; runtimes never get its secret.

Apply executes **001 -> 003 -> 004 -> 005** in one transaction, serialized by an
advisory transaction lock. 002 is explicitly deferred and never recorded as applied.
Canonical LF SHA256 hashes pin reviewed SQL and the column specification. Unknown
SQL files/changed hashes fail closed. The owner receives temporary schema/DB create
and Auth schema USAGE/TRIGGER/REFERENCES(id) privileges to install the FK/trigger;
these are revoked before commit. Existing UUID functions resolve under a controlled
legacy installation search_path. Runtime roles receive none of these Auth powers.
005 uses the trusted supabase_admin operator only to replace the platform-owned
Auth trigger (DROP requires table ownership); application functions/tables remain
vq_owner-owned. Auth table ownership is never transferred. The actual Supabase
operator/event-trigger compatibility still requires the separately authorized gate.

The owner-only private ledger, exact checksums, role flags/memberships, object/RLS
ownership, every column privilege including denied ones, denied table powers,
59 policy command/role identities, helper configuration/EXECUTE, defaults and Auth
trigger are asserted before COMMIT. Failure aborts the transaction; bootstrap roles
may remain separately, but no permissive intermediate schema is committed. Do not
remove/recreate roles or fabricate tracking; investigate using private diagnostics.
A completed identical ledger produces an asserted no-op. This runner deliberately
does not upgrade a historical untracked deployment. That needs a reviewed transfer,
collision/backfill/data cleanup plan rather than auto-repair.

## Runtime configuration

Host-run API and worker need different process-local DATABASE_URL values, with
username vq_api and vq_worker respectively. Supply passwords privately and percent-
encode URI components. No admin fallback exists. Settings redact DATABASE_URL and
hide invalid input; connection/cleanup errors have safe messages and no raw driver
traceback. Startup verifies the connected role's actual limitations/ownership.

Compose uses **API_DATABASE_URL** and **WORKER_DATABASE_URL** inputs mapped to each
service's DATABASE_URL. Its optional `.env.api.local` and `.env.worker.local` files
are ignored and separate: do not put either counterpart's password/admin API key in
them. Root `.env` is interpolation input, no longer injected wholesale. Keep these
private inputs outside tracked configuration and do not publish `docker compose
config` output or Docker process inspection (runtime DSNs are necessarily process
secrets). `.env.example` intentionally leaves password-bearing fields blank.

Safe nonsecret container Auth settings for the current local project:

```dotenv
JWT_ISSUER=http://127.0.0.1:54321/auth/v1
JWT_JWKS_URL=http://host.docker.internal:54321/auth/v1/.well-known/jwks.json
JWT_ALGORITHMS=ES256
JWT_AUDIENCE=authenticated
REDIS_URL=redis://redis:6379/0
```

Host JWKS transport instead uses 127.0.0.1. Container PostgreSQL transport uses
host.docker.internal:54322 only after reachability/limited login is verified; issuer
is unchanged. Compose is not started by this gate. Existing PUBLIC TEMP/platform
function permissions are not globally rewritten: service roles must never create
application objects, and arbitrary SQL execution remains a serious compromise.

## Separately authorized real permission harness

Build the actual current API image, then (only after the migration gate succeeds):

```powershell
& $databaseGateDocker build -t vq-db-permission-api-test backend
$privateRecovery = 'C:\Users\tsush\AppData\Local\VeriQuest\recovery\live-ee7fe07f5535490f89728348b707c83d'
.venv/Scripts/python.exe -B tools/database_live_gate.py --docker $databaseGateDocker --phase live --private-directory $privateRecovery --image vq-db-permission-api-test --authorize-live-database-gate
```

It verifies target/complete ledger/ACL assertions first and prompts privately for
the two runtime passwords. Operator/local API keys are acquired privately from the
verified project. Only a captured binary stdin capsule passes secrets to a restricted
temporary Linux API-image container; no Docker socket, published port or secret env
args. It compares every packaged backend Python source hash with the current reviewed
working tree before database/account writes. It creates A/B/C with real Auth, signs in, explicitly grants C admin through the
operator, and starts the **actual API app with its real limited pool and lifespan**
on container loopback. No mocked HTTP auth/DB/limiter/publisher is used. A deliberately
unavailable broker tests truthful failure persistence, not successful queue delivery.

The local container password is only a candidate for the supabase_admin TCP login;
the harness verifies that privileged SQL identity before creating any account. If
that login is unavailable, it stops without falling back to postgres or a runtime
role. Arrange privately authorized operator transport before retrying. Its current
TCP login passed during the live gate; recheck it each time rather than assuming it.

Assertions cover profile provisioning/metadata, real PostgREST own safe edits,
protected/mixed writes and unchanged values, client result/progress/role denials,
other-user isolation, hidden/draft/archived links, current DB admin grant/revocation,
actual limited SQL logins/column ACLs/forbidden statements, current submission
INSERT/duplicate/upsert/failure SQL, worker private reads/result/award/lock/streak/
quest/badge/audit SQL in rollback fixtures, validation transition rights and ledger.
Fixture publication and worker scoring statements are **permission fixtures only**,
not native simulator validation/accounting certification. The signed admin-claim test
remains generated-key/unit coverage; live metadata and grant revocation are separate.

Every failed assertion exits nonzero. Finally stops only its HTTP service and removes
its recorded FK-dependent fixtures before deleting its exact disposable Auth IDs;
the outer wrapper removes only its unique container. Cleanup failures are explicit.
Normal cleanup uses the same exact-resource recovery implementation below. Never
delete by a broad vq prefix or reset the project. GraphQL and hosted/deployed behavior
remain separate; do not equate the live fixture gate with production readiness.

## Private intent journals and recovery (follow-up)

The Windows private driver rechecks target/container identity, complete ledger,
manifest and full permission assertions, and the current-user/SYSTEM directory ACL.
It DPAPI-seals an immutable resource plan, flushes/fsyncs and decrypts/readbacks it
BEFORE launching a writer. Journal filenames are independent of account-name nonces.
Plans contain exact emails and metadata markers for Auth-generated IDs, exact slugs
for API-generated challenge IDs (including the expected-denied creation), and UUIDs
for quests, badge definitions, XP, awards and streak fixtures. No secrets/identities
are printed. Resource credentials retain the existing encrypted private mechanism.

The Linux harness requires --journal on the host CLI; do not launch it with an
ad-hoc resource capsule. The host validates/decrypts the journal and sends it privately
through stdin only after inspecting its read-only/no-port/no-socket container.
Direct fixture/runtime SQL is timed by safe operation/table labels, never values;
statement bounds are 10s, lock bounds 1500ms, idle-in-transaction bounds 10s, without
changing role defaults, grants or production pool implementation. Controlled probes
use smaller local cutoffs. The actual HTTP API still uses its unmodified pool/lifespan.

For a separately authorized recovery of one journal (use the exact path returned by
that run, never an arbitrary directory glob):

```powershell
.venv/Scripts/python.exe -B tools/database_live_gate.py --docker $databaseGateDocker --phase recover --private-directory $privateRecovery --journal '<exact private journal path>' --image vq-db-permission-api-test --authorize-live-database-gate
```

Recovery refuses while the original writer container exists. Inspect and stop only
that exact owned writer before recovering; never stop Supabase. Lookups use equality
against the sealed exact emails/slugs/UUIDs, verify markers, and refuse drift. One
bounded transaction deletes audit/XP/submission dependencies before challenges,
quests and badges. Only then does supported Auth administration delete resolved
accounts, with 404 absence verification. A failure retains the journal and reports
safe type/SQLSTATE; there is no write-retry loop. Repeating recovery resolves absent
resources as a no-op and cannot search/delete another run by prefix. SQL rollback
protects partial fixture deletion; Auth deletion is necessarily outside that SQL
transaction and can be resumed from the same immutable intent.

Controlled test flags --interrupt-point signup_response, challenge_response, and
populated_fixtures deliberately call os._exit(86), bypassing finally. This is expected
NONZERO output, not a successful permission run. They test post-response/pre-ID-retain
windows and committed populated fixtures; recovery must follow before another live
run. Read-only counts and sentinel/platform checks must independently verify cleanup.

Keep journals/receipts until recovery is independently confirmed. A killed process
does not necessarily cancel an already in-flight Supabase request. These tested
post-response points do not establish recovery quiescence for an unknown in-flight
Auth request, host/Docker death, power loss, or crash during recovery. Exact intent
remains discoverable if a late creation commits; absence is an observed result, not
a distributed cancellation guarantee. Do not erase journals or blindly restart.
Read docs/handoff/DATABASE_PERMISSION_FOLLOWUP_REPORT.md for the tested points and
remaining gates. Snapshot restoration and existing LAN exposure remain unresolved.

XP reconciliation/quest duplicate awards, crash-safe jobs/outbox, native Docker
workspace execution and revision-bound challenge lifecycle remain later milestones.
