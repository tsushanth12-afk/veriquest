# Database migration and permission gate assessment

Date: 2026-10-01, Asia/Calcutta. Repository: `C:\Users\tsush\Desktop\veriquest`, branch `main`, HEAD `7c7d1cd6062fcde09f06078830c1c490eb5b1675`. This is a read-only assessment and an **unexecuted implementation plan**, not permission certification.

## Outcome

**Implement permission hardening before applying/exposing the VeriQuest schema.** The disposable target was verified independently. PostgreSQL authentication and explicit read-only queries succeeded from Windows and two restricted Linux client containers. The database has **zero public application relations, no private schema, no VeriQuest roles, no application migration ledger, and zero Auth users/identities**. VeriQuest migrations are unapplied in the observed database; this is now execution evidence rather than a previous report's claim.

The actual default privileges grant newly created `public` tables broad rights to `anon`, `authenticated` and `service_role` when created by `postgres` or `supabase_admin`. Combining those defaults with migration 001 would expose ownership-only protected-field writes and submission insertion, and an entirely unprotected prerequisites table. These are **proposed-schema findings supported by live defaults**, not live attacks against nonexistent application tables.

Only this assessment document was created. No migration, seed, grant, schema change, account, role, profile or application row was created. Implementation, existing pending changes, and earlier reports were preserved. No application service, queue or worker daemon started. No commit/push/deployment occurred. The backend-security-coder skill guided the privilege boundary and fail-closed test plan; its optional implementation-playbook resource is absent, so detailed SQL design was derived directly from current source, catalogs and PostgreSQL documentation.

## 1. Target verification, credential handling and evidence

Verified before database access:

- `C:\Users\tsush\Desktop\veriquest-local-test\supabase\config.toml` declares project ID `veriquest-local-test`, API port 54321, PostgreSQL port 54322, major version 17, exposed schemas `public` and `graphql_public`, extra search path `public, extensions`, and disabled pooler.
- Docker labels on `supabase_db_veriquest-local-test` and the local REST/gateway containers identify the same project and exact work directory. The database is the existing `public.ecr.aws/supabase/postgres:17.11.0.002` image, with its project-specific persistent volume and `54322 -> 5432` mapping. Server version observed through SQL: 17.11.
- The REST container's actual safe environment fields agree: `PGRST_DB_SCHEMAS=public,graphql_public`, `PGRST_DB_EXTRA_SEARCH_PATH=public,extensions`, `PGRST_DB_ANON_ROLE=anon`.
- Existing ten project containers remain running; Vector and Logflare are absent. No hosted/alternate database was attempted.

Initial catalog access used the existing database container's local Unix-socket `postgres` identity, not an application credential. Every SQL batch began an explicit READ ONLY transaction and ended ROLLBACK; inventory batches also set local statement/lock timeouts. No Auth identifiers, email addresses, passwords, row contents, token strings, secret values, password verifiers or private evaluator content were selected.

For TCP connectivity, the verified database container's existing password was captured privately in an in-memory Python subprocess result. It was never inserted into a command argument, report or file. Windows used a temporary standard-library PostgreSQL wire client because the existing project venv has no asyncpg/psycopg/psycopg2/pg8000 and host psql was not found. The client implemented the server's authentication exchange, including SCRAM server-signature verification when used, and queried metadata only. Its startup options also set `default_transaction_read_only=on` and a statement timeout. This diagnostic is **not an asyncpg production-pool test**.

Linux clients used the already installed database image with `--pull never`, binary stdin containing the private password and read-only SQL, and an in-container PGPASSWORD variable consumed by psql. That transient process variable is a credential-bearing channel inside the temporary client; it was not supplied as Docker `-e`, stored in Docker configuration, inspected, logged or retained. Do not copy credentials into a future command-line DSN. Both clients were non-root, read-only-root, no capabilities, no-new-privileges, 128 MB memory and 32 PIDs, without a Docker socket or application mounts.

Actual TCP query result in all successful contexts: database `postgres`, SQL identity `postgres`, transaction read-only `on`, server 17.11, internal port 5432, public table count 0. Windows reached `127.0.0.1:54322`. Linux reached **`host.docker.internal:54322`**, verified on both `supabase_network_veriquest-local-test` and Docker's bridge network. Hostname reachability is distinct from choosing a runtime SQL role. JWT expected issuer remains `http://127.0.0.1:54321/auth/v1`; database/JWKS transport hostnames do not change it.

Read-only anonymous Data API checks acquired the local anonymous candidate privately from the gateway's **active `KONG_DECLARATIVE_CONFIG` path**, following the existing credential-acquisition approach in [auth_live_integration.py](C:/Users/tsush/Desktop/veriquest/tests/auth_live_integration.py). Decoding a candidate's role selected it; actual HTTP acceptance established gateway access. The account-creating harness was not run.

| Actual local HTTP request | Status / assertion | What it proves |
| --- | --- | --- |
| GET `/rest/v1/`, Accept-Profile public | 200; OpenAPI paths count 1 (root only) | No public application resource currently advertised |
| GET `/rest/v1/profiles?select=id&limit=0`, public | 404, PGRST205 | Profiles absent from current Data API schema cache |
| GET `/rest/v1/challenge_secrets?select=challenge_id&limit=0`, Accept-Profile private | 406, PGRST106 | Private schema not currently exposed through this Data API |

Three HTTP assertions passed. The last denial does **not** prove future private-table ACLs, absence of RPC/view leaks, or worker/API isolation.

## 2. Live structure and effective privilege inventory

Catalogs inspected: pg_namespace/class/tables/roles/auth_members/default_acl/policies/proc/trigger/event_trigger/extension/database/db_role_setting and information_schema.column_privileges. Only structure, privilege flags and counts were returned.

### Schemas and relations

| Schema | Owner | Table/view/foreign-relation count | Relevant observed property |
| --- | --- | ---: | --- |
| public | pg_database_owner | 0 | PUBLIC, anon/authenticated/service_role have USAGE, not CREATE |
| private | absent | 0 | No VeriQuest secrets or migration ledger |
| auth | supabase_admin | 27 | 16 tables have RLS; users and identities both count 0 |
| extensions | postgres | 2 views | Required UUID extension available |
| graphql_public | supabase_admin | 0 | One invoker placeholder function; schema exposed |
| graphql | supabase_admin | 0 | Schema present; not in REST exposed list |
| _realtime | postgres | 4 | Platform-owned, not VeriQuest |
| realtime | supabase_admin | 8 | One partitioned relation has RLS |
| storage | supabase_admin | 10 | All ten tables have RLS |
| supabase_functions | supabase_admin | 2 | Platform-owned |
| vault | supabase_admin | 2 | Includes decrypted_secrets view; anon/authenticated lack schema USAGE |
| pgbouncer | pgbouncer | 0 | Pooler disabled in project config |

No table has FORCE ROW LEVEL SECURITY in the inspected non-system inventory. `pg_policies` contains **zero policies globally**; RLS-enabled platform tables without policies remain distinct from application policies, which do not exist. No non-internal triggers exist on auth/public/private tables. Six enabled Supabase event triggers manage extension privileges and PostgREST DDL/drop notifications, not an observed application permission-hardening trigger.

`supabase_migrations.schema_migrations` is absent, and no `supabase_migrations` schema appeared. Auth's **82 internal migration records** are not VeriQuest migration history. All fourteen relations defined by migration 001 are absent (thirteen public tables plus private.challenge_secrets). The local CLI folder has no migrations directory or seed.sql; config nevertheless enables migrations/seeding and references `./seed.sql` for a future reset. Repository migrations are in a different folder and are not automatically applied by current API startup or Compose.

Extensions: uuid-ossp 1.1, pgcrypto 1.3, pg_stat_statements 1.11, supabase_vault 0.3.1, plpgsql 1.0. UUID functions are available: extensions.uuid_generate_v4 and pg_catalog.gen_random_uuid. The existing postgres search path includes public and extensions, so legacy unqualified UUID defaults currently resolve under that operator; a new owner/runtime role must not be assumed to inherit this setting.

### Roles and memberships

Sixteen non-pg roles were observed: anon, authenticated, authenticator, dashboard_user, pgbouncer, postgres, service_role, supabase_admin, supabase_auth_admin, supabase_etl_admin, supabase_functions_admin, supabase_privileged_role, supabase_read_only_user, supabase_realtime_admin, supabase_replication_admin, supabase_storage_admin.

- anon/authenticated: NOLOGIN, no superuser/role creation/DB creation/replication/BYPASSRLS, no role memberships. Database CONNECT/TEMP and public/auth/extensions/graphql_public USAGE are effective; database CREATE and public CREATE are denied.
- authenticator: LOGIN, NOINHERIT, no BYPASSRLS. Can SET ROLE anon/authenticated/service_role, without admin option. Do not grant this role application SQL-role memberships.
- postgres: LOGIN, not superuser in this installation, but BYPASSRLS/CREATEROLE/CREATEDB/REPLICATION and broad inherited roles including service_role and pg_read_all_data. It is an inspection/migration operator, **not** a suitable runtime application identity.
- service_role: BYPASSRLS; do not use it as a student or substitute for a narrow asyncpg role. supabase_admin is superuser/BYPASSRLS. Other platform roles retain platform-specific privileges; this plan does not repurpose or modify them.
- supabase_etl_admin and supabase_read_only_user also bypass RLS and inherit pg_read_all_data/monitor roles. Neither is a suitable least-privilege application reader.
- Storage/realtime roles can assume platform API roles. Twenty-five membership edges were inspected; no application vq_/veriquest roles exist.

Effective anon/authenticated/authenticator/service_role privileges on auth.users, auth.identities and auth.schema_migrations: SELECT/INSERT/UPDATE/DELETE/TRUNCATE all false. No application grants or column grants can be verified because application tables do not exist.

### Default privileges and callable objects

Twenty-seven default-ACL entries were inspected. Of direct relevance:

- For **both postgres and supabase_admin**, public future TABLE defaults grant anon/authenticated/service_role SELECT, INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER and MAINTAIN (`arwdDxtm`).
- Public future SEQUENCE defaults grant those roles SELECT/UPDATE/USAGE. Public future FUNCTION defaults explicitly grant EXECUTE to those roles; PostgreSQL's ordinary PUBLIC function-execute default also needs separate treatment.
- Other observed defaults cover platform storage/graphql/realtime/auth/extensions/functions schemas. Do not globally rewrite unrelated platform defaults.

Non-system function counts / security-definer counts: auth 4/0, extensions 55/0, graphql_public 1/0, pgbouncer 1/1, realtime 17/0, storage 19/0, supabase_functions 1/1, vault 5/2. There are **no public/private VeriQuest functions**. Auth helpers uid/jwt/role/email are invoker functions with effective client EXECUTE. graphql_public.graphql is invoker. Platform supabase_functions.http_request is a security-definer trigger function with fixed supabase_functions search path and client EXECUTE; no application trigger uses it. Vault's view is not an application-safe public view; its schema is inaccessible to anon/authenticated. This was a relevant catalog inventory, not an exhaustive audit of platform function bodies or hosted Supabase.

## 3. Actual application access paths and required SQL capabilities

The frontend currently uses Supabase SDK **Auth**, not `.from()`/`.rpc()` application-table operations. Application adapters call FastAPI. Independently, exposed public tables would still be reachable through PostgREST/GraphQL according to SQL grants and RLS; hiding a frontend call is not permission enforcement.

Sources: [challenge service](C:/Users/tsush/Desktop/veriquest/backend/app/challenges/service.py), [profile router](C:/Users/tsush/Desktop/veriquest/backend/app/profile/router.py), [submission service](C:/Users/tsush/Desktop/veriquest/backend/app/submissions/service.py), [admin router](C:/Users/tsush/Desktop/veriquest/backend/app/admin/router.py:28), [worker task](C:/Users/tsush/Desktop/veriquest/worker/tasks/hdl_task.py), [gamification SQL](C:/Users/tsush/Desktop/veriquest/backend/app/gamification/xp.py), [leaderboard router](C:/Users/tsush/Desktop/veriquest/backend/app/leaderboard/router.py), [database pool](C:/Users/tsush/Desktop/veriquest/backend/app/db/session.py).

| Journey / production function | Current transport and operations | Required trusted capability |
| --- | --- | --- |
| Anonymous catalog: get_published_challenges/get_challenge_by_slug | FastAPI optional auth; asyncpg SELECT published nonarchived challenges, LEFT JOIN progress with supplied verified subject or nil UUID | API SELECT public challenge fields and progress columns; anonymous clients need only public published catalog read if Data API access is retained |
| Own profile: get_profile/update_profile | Required auth; asyncpg SELECT own profile/progress/badges; rank and total counts read all profiles; PATCH only display_name/bio/avatar_url | API profile SELECT, display-column UPDATE, progress/badge reads; username currently not editable |
| History/poll: get_submission/get_user_submissions | asyncpg SELECT submissions with verified user_id predicate, join challenge title | API result/history SELECT; no direct student creation of rows |
| Submit: create_submission/record_publication_failure | asyncpg published challenge check; INSERT queued submission; progress attempt upsert; conditional dispatch-failure UPDATE | API input-column INSERT, narrow infrastructure-state UPDATE, limited progress INSERT/UPDATE required by current code |
| Staff CRUD/validation/publication | verify_admin then asyncpg challenge/secret SELECT, INSERT/UPDATE; lifecycle claim/failure/publish/unpublish UPDATE; audit INSERT/SELECT | API union includes private authoring access, trusted current DB-admin check, lifecycle fields, audit append/read; no role grants required |
| Worker _execute_hdl_submission | asyncpg submission/challenge SELECT; secrets SELECT; status/result/XP UPDATE | Worker private evaluator reads and result-column writes, not authoring/input edits |
| Worker award_xp/update_streak/check_quest_completion/check_badge_awards | asyncpg progress upsert/row lock/update, XP INSERT/aggregate SELECT, profile aggregate UPDATE, streak upsert/read, quest/badge definitions SELECT, user_badges INSERT | Worker SELECT/INSERT/UPDATE on exact accounting columns/tables; no role writes, DDL, table ownership or blanket administrative identity |
| Worker _validate_challenge | asyncpg pending challenge/secret SELECT; conditional validation_status/validated_at UPDATE; audit INSERT | Worker read official solution and bench, narrow validation-state update, append audit only |

Current API and worker use a static pool identity, not `SET LOCAL request.jwt.claims`/role per request. Existing auth.uid()-only policies will not authorize a new ordinary asyncpg SQL role by themselves. Define explicit **role-specific server RLS policies plus grants**; do not solve this by granting BYPASSRLS or using postgres. These server policies are intentional all-user service authority, not student row isolation. Their compromise blast radius and application predicates remain important.

The API currently uses one pool for public/student and admin handlers. Its minimal SQL role therefore includes that union, including private authoring access. The worker need not have private_notes/test_vector_config access, authoring writes, user_roles access, Auth access or audit-log reads. A separate admin API pool could further isolate secrets from student handlers, but is additional design work, not something the existing single-pool architecture already provides.

## 4. Findings and required corrections

### High: apply-time protected-field and forged-result exposure

[Migration 001 policies](C:/Users/tsush/Desktop/veriquest/supabase/migrations/001_initial_schema.sql:329) allow own-profile UPDATE without restricting columns and own-submission INSERT without limiting status/counts/XP/worker fields. Under the observed creator defaults, a valid student could satisfy RLS while assigning protected XP/level/streak/attempt/solved fields, or inserting a pregraded accepted result. Source constraints on nonnegative XP/status do not establish result authority. The API PATCH allowlist and trusted grader do not constrain direct PostgREST writes.

**Plan:** revoke table-wide and column-wide client mutations first; remove submissions_insert_own; grant authenticated only UPDATE(display_name,bio,avatar_url) on profiles if direct display editing is retained, with own-row UPDATE and SELECT policies. Never grant client INSERT/UPDATE/DELETE on submissions/results, progress, XP, streaks, user_badges, roles, challenges, secrets or audits. Student role rows are privileged data; API/worker never provision admin roles.

### High: prerequisites and unscoped profile data

challenge_prerequisites has no RLS and would receive broad public-table defaults. Clients could read draft relationships or mutate the curriculum. profiles_select_all permits all profile columns for any role with SELECT. quest_challenges_select_all similarly exposes draft challenge links, even when the challenge itself is hidden. Current challenge SELECT policy also lacks the API's is_archived=false filter.

**Plan:** RLS on prerequisites; client SELECT only where both challenges are published/nonarchived. Filter quest links by active quest and visible challenge. Restrict direct profile reads to own authenticated row; rankings already come through the authenticated API's explicit projections. Catalog policy must require published AND not archived. No direct client writes to curriculum. Prerequisite persistence in authoring remains unimplemented; permission hardening does not add product behavior.

### High: signed-role administrator shortcut

[verify_admin](C:/Users/tsush/Desktop/veriquest/backend/app/admin/router.py:28) immediately returns true when the verified JWT's role string is admin. The signature proves issuer origin, not a current grant in public.user_roles; revocation can remain ineffective until token expiry. Current local tokens normally carry authenticated; no live privilege bypass was attempted. `core/security.py:require_admin` itself only returns the authenticated user, not a DB authorization decision. Frontend isAdmin probes the backend list route, so it inherits this shortcut.

**Plan:** always query the trusted role table for the verified subject, deny on missing row or DB failure, and remove the JWT-role early return. Preserve signature/issuer/audience/UUID checks. User metadata, submitted IDs, role headers and frontend flags must never grant admin. Test a correctly signed token claiming admin **without** a database grant, and revocation while reusing a still-valid token. Do not add a student-callable role-grant RPC.

### High: inappropriate runtime credential defaults

Current Settings.database_url and both worker pool functions default to an administrative postgres identity. Current Compose loads the same optional root env into both processes. Live postgres has role/DB creation, BYPASSRLS and broad inherited privileges. A Supabase service API key is not a narrow SQL role; the backend setting supabase_service_key is not used by these asyncpg paths.

**Plan:** require separate privately provisioned API/worker DSNs, reject missing configuration rather than falling back to admin defaults, and explicitly map different process DATABASE_URL values. Runtime roles must not own tables/functions, bypass RLS, create DBs/roles, inherit/assume platform/owner roles, or access Auth users/vault. No credential values belong in examples or logs. db/session.py:init_db currently logs raw pool exceptions; worker exception logging also needs review for accidental DSN/detail disclosure in this configuration change.

### Medium: ACLs, RLS bypass surfaces and definer functions

RLS does not police columns, and does not govern TRUNCATE/REFERENCES. Supabase defaults include table-wide privileges beyond ordinary CRUD. No ordinary PostgREST TRUNCATE endpoint was observed; this is a SQL capability issue, not a claim that the HTTP API has a truncate route. A table owner or BYPASSRLS role escapes ordinary RLS. Default EXECUTE can expose future helper RPCs, and owner-executed views can defeat intended row policies. [PostgreSQL RLS semantics](https://www.postgresql.org/docs/17/ddl-rowsecurity.html).

Both proposed application security-definer triggers lack fixed search_path. Their current relation references are schema-qualified and current clients lack public CREATE; this review did not demonstrate a search-path exploit. Still, make their owners deliberate, pin an empty search_path and qualify referenced objects/functions. Revoke client EXECUTE; keep helpers in private where practical. Harden update_updated_at too. Any future exposed view must be security_invoker or an explicitly authorized safe projection, with tests of effective owner/RLS behavior. Do not expose a definer function returning secrets or writing results. [Secure definer functions](https://www.postgresql.org/docs/17/sql-createfunction.html).

### Medium: local network exposure

Observed Docker bindings are 0.0.0.0 and IPv6 all-addresses, not loopback-only, for DB/API/Studio/mail. Local config network restrictions are disabled. Firewall/LAN reachability was not tested. Keep this disposable environment private; later loopback binding/firewall changes require separate authorization. A successful loopback probe is not evidence that other hosts cannot reach the database.

## 5. Concrete least-privilege SQL design — DO NOT EXECUTE YET

### Ownership and role model

Preferred small change: dedicated **vq_owner NOLOGIN** for VeriQuest DDL/functions, **vq_api LOGIN** and **vq_worker LOGIN** with NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS and no privileged memberships. Use NOINHERIT as defense in depth; also verify SET ROLE memberships, since NOINHERIT alone does not prevent role switching. Only a controlled migration operator may assume vq_owner. Neither authenticator nor client roles may assume these service/owner roles.

Create roles/provision passwords privately in a separately authorized local bootstrap; never put passwords in SQL files or command arguments. vq_owner receives only the schema creation/ownership privileges needed for these application objects; platform Auth/storage/extensions ownership is untouched. Runtime roles need CONNECT on the local postgres database, schema USAGE on public/private as applicable, and the UUID default function's EXECUTE/extension USAGE if legacy defaults are retained. Grant **no sequence permissions** for the existing UUID-only schema. Verify required auth.uid helper access for client policies. Choose a safe role search_path and explicit qualification rather than inheriting the operator's settings.

Use the vq_owner identity consistently for CREATE. Observed postgres/supabase_admin defaults do not apply to objects created as a different role. Revoke any application-object grants inherited from the historical creator if upgrading an existing schema. Do not globally revoke platform tables/functions.

Schematic bootstrap/defaults (roles and schemas must already be explicitly provisioned):

```sql
-- Dedicated owner only: global function default first, not only schema-local.
ALTER DEFAULT PRIVILEGES FOR ROLE vq_owner
  REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC, anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES FOR ROLE vq_owner IN SCHEMA public
  REVOKE ALL ON TABLES FROM PUBLIC, anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES FOR ROLE vq_owner IN SCHEMA public
  REVOKE ALL ON SEQUENCES FROM PUBLIC, anon, authenticated, service_role;
-- Apply matching owner defaults in private; explicitly grant reviewed objects only.
REVOKE ALL ON SCHEMA private FROM PUBLIC, anon, authenticated, service_role;
GRANT USAGE ON SCHEMA private TO vq_api, vq_worker;
```

Default privilege changes affect only future objects of the named creator. A schema-local revoke cannot subtract a global default grant; handle PUBLIC function EXECUTE globally for the **dedicated owner**, and revoke on existing application functions explicitly. If continuing to CREATE as postgres instead, its observed schema-local defaults must also be corrected before creation; do not assume SET ROLE/inherited defaults are equivalent. [Default privilege rules](https://www.postgresql.org/docs/17/sql-alterdefaultprivileges.html).

### Client ACL and policy matrix

First REVOKE ALL on each of the fourteen **explicitly named application tables**, application functions and any existing column grants, from PUBLIC/anon/authenticated/service_role. Table-level revokes do not remove separate column grants. Do not use a shared-schema blanket revoke on unrelated platform objects. No DELETE/TRUNCATE/REFERENCES/TRIGGER/MAINTAIN/grant-option grants to clients or runtimes. [Table/column privilege rules](https://www.postgresql.org/docs/17/sql-grant.html).

| Object | anon | authenticated | Required client RLS |
| --- | --- | --- | --- |
| challenges | SELECT reviewed public columns | same | published AND NOT archived |
| challenge_prerequisites | SELECT id/challenge_id/prerequisite_id, or no grant if not exposed | same | both endpoints published/nonarchived |
| profiles | none | SELECT own row; UPDATE display_name/bio/avatar_url only | id=auth.uid(), USING and WITH CHECK, TO authenticated |
| submissions | none | SELECT own safe history/result columns only | user_id=auth.uid(); no INSERT policy |
| user_challenge_progress, xp_transactions, user_badges, streak_activity | none | SELECT own reviewed fields only | user_id=auth.uid() |
| user_roles | none | SELECT user_id/role only, own row if client needs it | user_id=auth.uid(); no client mutation |
| quests, badges | public definition SELECT only if retained | same | active-only, limited public fields (exclude badge rule_config unless deliberately public) |
| quest_challenges | SELECT only if retained | same | active quest AND published/nonarchived challenge |
| admin_audit_log | none | none, including users with an application admin grant | privileged FastAPI route only |
| private.challenge_secrets and all private helpers/ledger | none | none | schema USAGE denied plus object ACLs; RLS enabled as defense in depth |

An application admin is still an authenticated **client** role. Admin privileges operate through verified server routes, not table-wide PostgREST grants. Narrow direct safe display editing is the default recommendation; API-only display editing is also viable because the current UI calls the API, but decide/document it consistently in tests.

Replace, rather than merely supplement, broad legacy policies: permissive policies OR together. Example shape:

```sql
DROP POLICY profiles_select_all ON public.profiles;
DROP POLICY profiles_update_own ON public.profiles;
DROP POLICY submissions_insert_own ON public.submissions;
CREATE POLICY profiles_client_read ON public.profiles FOR SELECT
  TO authenticated USING (id = (SELECT auth.uid()));
CREATE POLICY profiles_client_edit ON public.profiles FOR UPDATE
  TO authenticated USING (id = (SELECT auth.uid()))
  WITH CHECK (id = (SELECT auth.uid()));
GRANT SELECT ON public.profiles TO authenticated; -- own rows only
GRANT UPDATE (display_name, bio, avatar_url) ON public.profiles TO authenticated;
-- Never GRANT UPDATE ON public.profiles to a client role.
```

No client can assign protected fields merely by satisfying ownership. Role policies must be TO explicit intended roles rather than PUBLIC. UUID/id/username/progress/audit timestamps remain server-generated/protected. Own SELECT may return a full own profile, but not another user's bio/history/metadata. The API's leaderboard projection remains independently authorized.

### Minimum runtime rights matching current SQL

Every runtime grant below also needs a command-specific RLS policy **TO that runtime role** on the target RLS-enabled table. Use USING(true)/WITH CHECK(true) only for the trusted service operations listed, not FOR ALL TO PUBLIC. Column ACLs restrict what those all-row policies can change. No runtime owner/BYPASSRLS shortcut. Owner-trigger execution is deliberately privileged and must be narrowly coded; do not add FORCE RLS blindly without defining how the trusted trigger inserts will remain authorized.

**vq_api:**

- SELECT profiles (current own-profile/rank/leaderboard SQL needs these fields), challenges/public metadata/lifecycle, progress, badge definitions/user badges, XP transaction fields for weekly/monthly ranks, safe submission/history fields, user_roles(user_id,role), and admin_audit_log. Private SELECT only challenge_id/official_solution/hidden_testbench/evaluator_type/execution_profile/private_notes required by current staff detail/preflight.
- UPDATE profiles(display_name,bio,avatar_url), not scoring/identity fields.
- INSERT submissions(id,user_id,challenge_id,status,submitted_code,idempotency_key,submitted_at); UPDATE only status/completed_at/error_code/public_message for dispatch-failure handling. Because API legitimately inserts literal queued, add an API INSERT WITH CHECK enforcing queued, absent execution evidence and zero awards; do not grant input insertion as a general pregraded-result capability. A command-specific API UPDATE check should allow only the source-required queued/system_error states; allow polling SELECT of all lifecycle states. Verify ON CONFLICT/WHERE/RETURNING SELECT needs, not just write columns.
- INSERT progress(user_id,challenge_id,status,attempts); UPDATE progress(status,attempts,updated_at) required by current create_submission. This API still has a trusted attempt-write capability; later accounting work should remove it when creation no longer increments attempts.
- INSERT/UPDATE the explicit challenge metadata and lifecycle fields used by create/update/validate/publish/unpublish, plus SELECT of IDs/state used by conditions/RETURNING. No challenge DELETE because no production route requires it.
- INSERT secrets(challenge_id,official_solution,hidden_testbench,evaluator_type,execution_profile,private_notes); UPDATE those mutable evaluator/notes fields, not ownership/id/timestamps. Trigger-generated updated_at is permitted without granting clients that column.
- INSERT audit(admin_user_id,action,target_type,target_id,details). No UPDATE/DELETE of audits, no user_roles INSERT/UPDATE/DELETE, no accounting-table writes beyond current progress attempt plumbing.

**vq_worker:**

- SELECT submissions(id,user_id,challenge_id,submitted_code,status) and challenge fields id/xp_reward/difficulty/is_published/validation_status needed for work/validation; private SELECT only challenge_id/official_solution/hidden_testbench/evaluator_type/execution_profile.
- UPDATE submissions(status,started_at,worker_id,completed_at,runtime_ms,simulation_ns,tests_total,tests_passed,tests_failed,error_code,public_message,compiler_output,xp_awarded); not id/user_id/challenge_id/submitted_code/idempotency_key/submitted_at. No INSERT/DELETE submissions.
- UPDATE challenges(validation_status,validated_at) only for pending unpublished validation, with a command-specific check restricting worker output to validated/validation_failed and is_published=false; no title/bench/solution/reward/publish writes.
- SELECT/INSERT progress fields used by upsert/locking/awards; UPDATE status/attempts/best_submission_id/completed_at/updated_at. SELECT these columns for expressions/conflict/locks.
- SELECT profiles scoring fields needed by aggregate expressions and badge checks; UPDATE xp/level/total_solved/easy_solved/medium_solved/hard_solved/total_attempts/current_streak/longest_streak. No username/bio/avatar/identity modification or profile INSERT.
- SELECT/INSERT xp_transactions(user_id,challenge_id,submission_id,amount,reason) plus read id/created_at for duplicate/aggregate queries. No ledger UPDATE/DELETE.
- SELECT/INSERT/UPDATE streak_activity only its user/date/type/count fields used by the source (count UPDATE for upsert); SELECT quest/challenge definition and badge rule fields required for awards; SELECT/INSERT user_badges(user_id,badge_id). No curriculum/badge-definition writes.
- INSERT audit(admin_user_id,action,target_type,target_id,details) for validation result; no audit SELECT/UPDATE/DELETE, no user_roles/Auth/vault access.

No server read policy should accidentally depend on request JWT claims that the current pools do not set. Static SQL-role all-row access leaves HTTP ownership/admin checks essential. Further request-scoped DB identity or a separate admin SQL pool is a later defense-in-depth option, not claimed by this minimal plan. A compromised worker can still exercise its required scoring rights; permissions cannot prove correct XP algorithms or trusted execution.

## 6. Migration, profile and fixture implementation plan

Proposed affected files only; none were edited:

1. New reviewed `supabase/migrations/004_permission_gate.sql`: explicit application ACL/RLS/ownership/function hardening, dedicated owner defaults, runtime grant matrix and denial of future automatic public exposure for owner-created objects.
2. New `supabase/migrations/005_profile_identity_gate.sql`: replace signup trigger/helper with hardened identity provisioning and constraints; explicit authorized existing-user handling. Avoid modifying previously applied historical migration checksums in other environments.
3. A small reviewed migration runner/manifest and database-gate runbook, e.g. `tools/database_gate.py` and `docs/DATABASE_PERMISSION_GATE.md`: verified local target, allowlisted script hashes, stop-on-error transaction, tracked versions/checksums, safe credential transport, no automatic seeds/reset. New live permission harness calling actual Auth/PostgREST/API and direct role connections; no mocked permissions counted as live.
4. `backend/app/admin/router.py:verify_admin` plus focused tests: always DB-backed admin authorization, including signed-role/revocation cases.
5. `backend/app/core/config.py`, `backend/app/db/session.py`, `worker/tasks/hdl_task.py`, `docker-compose.yml`, `.env.example`: require explicit distinct service database credentials/configuration, safe pool-error reporting; preserve JWT issuer/JWKS separation and Redis publisher contract. Configure separate API_DATABASE_URL/WORKER_DATABASE_URL inputs that become the respective process DATABASE_URL values; host-run API can still use its explicit DATABASE_URL. No shared administrative default fallback.
6. Only if constraints are strengthened for display lengths/types, `backend/app/profile/router.py`/schemas and tests should return truthful validation errors for rejected edits, rather than silently reporting an update for a nonexistent profile. No XP algorithm change.

### Ordering, transaction and tracking

- Privately verify target again and authorize a recoverable local snapshot before changing anything. Record metadata/counts only. The observed database is empty of application objects/users, but platform schema/data must be preserved. Never use `supabase db reset` as a rollback shortcut.
- Bootstrap owner/runtime roles and database/schema privileges under separately authorized operator access. Role/password provisioning is tracked separately from schema changes; credentials are not migration content. No application role should inherit operator/platform authority.
- Schema dependency order: 001 initial; 002 depends on 001 but is a **development data fixture**, not a schema prerequisite; 003 depends on 001; 004 after structural 001/003; 005 after profiles/user_roles exist. Current README lists only 001/002 and omits 003.
- Recommended safe new-environment manifest: **001 -> 003 -> 004 -> 005 in one explicit transaction**, intentionally defer 002. Record 002 as deferred fixture, not falsely applied. Use one consistent version/checksum ledger in private, owner-only; do not manually fabricate Supabase CLI migration history. If adopting CLI tracking instead, review/import its exact naming/seed rules and avoid accidentally executing 002 as a standard automatic migration. This requires an explicit runner choice before application; no CLI reset or copying scripts into the running local project was performed.
- Ensure extension resolution for legacy UUID defaults under the migration identity (controlled `pg_catalog,public,extensions` search path for legacy script), then pin hardened function paths. Extension already exists; CREATE EXTENSION IF NOT EXISTS does not relocate it. Prefer qualified UUID defaults or built-in pg_catalog.gen_random_uuid for future objects.
- Stop on any SQL error; no autocommitted partial sequence. Insert checksum/version records within the same transaction as changes. Run structural/ACL assertions before COMMIT. The permissive intermediate 001 state must never become visible in a separate committed/exposed interval. Serialize the runner and detect wrong schema/checksum/partial-application state before proceeding.
- Do not reconnect as runtime roles until ACL/RLS/function changes have committed and catalog assertions pass. A failed transaction must leave application objects/ledger unapplied; separately created bootstrap roles may remain and need a specifically scoped cleanup decision. PostgreSQL logs/connection operational metadata can persist; this assessment did not alter them.

### Profile identity design

Current public.handle_new_user reads untrusted username/display_name metadata or email local-part, then inserts a unique username. Empty/duplicate usernames or equal email local-parts can abort signup. Metadata can provide problematic values; existing schema lacks useful display-length/counter/result-consistency bounds. There is no backfill or automatic student role row in 001.

Recommended replacement: private, fixed-empty-search-path SECURITY DEFINER signup helper owned by the dedicated trusted owner (or an even narrower NOLOGIN trigger owner). Fully qualify relations and built-ins; revoke client EXECUTE. Attach to auth.users AFTER INSERT. Generate a reserved deterministic username from the **full Auth UUID**, never from role metadata or an untrusted requested username; retain a bounded display name as presentation only. Provision only a literal student role if student role rows are retained. No metadata key, including role/is_admin/app-like objects inside raw_user_meta_data, may produce an admin/moderator grant or initial XP.

Define username length/canonical-case/reserved-namespace rules and preflight collisions for upgrades. Do not silently rename/merge an existing profile. Preserve existing profile stats when handling an existing UUID; idempotent backfill must never overwrite scoring or roles. Current Auth user count is 0, so existing-user backfill is **currently empty**, not generally unnecessary. A future upgrade needs a reviewed missing-profile count/collision plan and operator-approved backfill. Do not make runtime roles able to insert arbitrary profiles.

Basic constraints should bound allowed display fields and retain nonnegative/positive invariants. Additional solved/attempt count nonnegative constraints are worthwhile; reconciliation-sensitive cross-counter/XP equalities belong to the accounting milestone after existing-data review. Database profile/role creation for an Auth user must be atomic with signup; genuine infrastructure failure should reject honestly, not produce a fabricated frontend profile success.

### Seed truthfulness

[002_seed_demo_challenge.sql](C:/Users/tsush/Desktop/veriquest/supabase/migrations/002_seed_demo_challenge.sql) sets is_published=true, validation_status=published and timestamps without executing the official solution. This is a fixture, not native validation evidence. Its upsert can also update secrets and trigger invalidation after updating public metadata, so replay is not a reliable publication workflow.

Default plan: do not run 002 during permission setup. If a demo is subsequently authorized, load the fixture as an **unpublished draft** with no validated_at/published_at, using an explicit reviewed fixture command or later corrective migration; run genuine queued native validation before publication. Do not rewrite an already applied seed migration in an unknown environment. A later real wrong-job transport checkpoint can distinguish worker receipt/configuration failure from actual graded success; native workspace repair remains required for accepted grading.

## 7. Later live acceptance matrix and recovery

Separate authorization required: reviewed migration application, role/password provisioning, two disposable student accounts A/B and one administrator C, targeted test fixtures, temporary API/queue processes as needed. No live student permission assertion is possible today because accounts and application schema are absent and creation is prohibited in this task.

Use actual Supabase Auth-issued tokens, actual PostgREST/API responses and fresh direct SQL connections **as each limited login role**, not a postgres connection merely labeled as a worker. SQL `SET ROLE`/controlled request.jwt.claims checks are useful supplements, not substitutes for HTTP sessions or actual login credentials. Assert outcomes and unchanged protected rows/counts privately; never print test identities/tokens/passwords. All harness assertions must fail nonzero.

1. **Migration/ACL gate:** assert tracked checksums, all fourteen intended objects/constraints, owners, role flags/memberships, schema/table/column/function/default ACLs, expected policies, hardened helpers/trigger, no private API exposure. Fresh apply succeeds; repeat is tracked no-op; changed checksum rejected. In a separately authorized disposable rehearsal, inject a mid-transaction error and prove no partial objects/ledger; do not inject failure into the existing project without a recovery boundary.
2. **Profile provisioning:** A/B/C each create exactly one UUID-linked zero-progress profile; distinct full-UUID usernames even with identical requested username/email local-part; empty/oversized/malformed metadata handled by documented fallback/validation. Metadata role=admin cannot grant admin. If testing existing-user backfill, explicitly create/authorize a pre-schema fixture in a separate rehearsal, then verify missing-profile repair preserves any preexisting legitimate stats. Account creation/confirmation failures must be truthful.
3. **Anonymous catalog:** only published nonarchived metadata/public samples visible through PostgREST and FastAPI; draft/archived/private/other-user profile/history/role reads denied or empty as specified. Prerequisite and quest links must not reveal draft challenge IDs. Requests using Accept-Profile private remain rejected. API responses and advertised OpenAPI/GraphQL fields never include solutions/hidden benches.
4. **Own profile editing:** A can read A and edit only A display_name/bio/avatar_url via both configured allowed paths. A cannot change A XP/level/streak/attempt/solved/id/username/timestamps/role, including a mixed safe+protected payload; direct SQL/PostgREST write must fail atomically, not partially update the safe field. A cannot read or edit B's profile except explicitly projected leaderboard information. API's existing protected-only PATCH no-op behavior must be documented; regardless of HTTP wording, protected state must remain unchanged.
5. **Submissions/results:** direct A INSERT of queued or accepted/pregraded submissions denied, as are UPDATE counts/status/XP/worker_id and DELETE. Actual authenticated API creates a server-owned queued row only for A and a public permitted challenge; supplied B IDs/role headers do not select identity. B cannot read/poll A; A cannot change authoritative results via PostgREST/RPC. An unknown ID may yield 404/empty without revealing ownership. Successful worker finalization is a separate native execution gate.
6. **Progress/ledger/roles:** A/B cannot INSERT/UPDATE/DELETE/TRUNCATE progress, XP ledger, streak, badge awards, roles or audits. Test protected-write attempts even with correct own user_id. No client can GRANT/SET ROLE to owner/API/worker/platform roles, create tables/functions/triggers, grant itself admin, or invoke private/public definer helpers. Check actual role privileges and controlled SQL-denial tests; do not rely on RLS alone for TRUNCATE. Test exposed RPCs/GraphQL where available, not just frontend adapters.
7. **Administrator authority:** C gets its admin row only through explicit operator provisioning; current DB check permits staff routes. A/B receive 403 for list/detail/create/update/validate/publish/unpublish/audit. A signed admin-role token with no DB grant must still fail. Revoking C's grant must block C's still-valid token. Application admin C remains unable to mutate protected user/scoring/roles or read secrets directly through PostgREST; authorized staff API may read/edit challenge secrets. Existing publication prerequisites remain enforced, without claiming revision-safe lifecycle.
8. **API SQL-role boundary:** actual vq_api login can execute every current source operation with its required columns/conflict/RETURNING/triggers. It cannot insert nonqueued/pregraded rows, write XP/result counts/profile scoring fields/roles, delete ledger/audit, create/alter/drop objects, disable RLS, access Auth/vault or assume elevated roles. Its legitimate authoring access remains application-authorized; verify unprivileged HTTP users cannot obtain it. Infrastructure-failure persistence remains permitted and truthful.
9. **Worker SQL-role boundary:** actual vq_worker login can read necessary private evaluator fields, claim/update execution result columns and perform current award/streak/badge SQL in a targeted rollback fixture. It cannot read private_notes/Auth/vault/roles/audit history, alter student input/user ownership, publish or edit curriculum/secrets/rewards, create submissions/profiles, delete audit/ledger or elevate SQL roles. Its validation update succeeds only for the pending unpublished case. Test JSONB returned types using real asyncpg once available; this does not fix the separate badge JSON/accounting defect.
10. **Post-failure isolation/recovery:** rejected writes leave row values unchanged; wrong credentials/roles fail closed. Schema/ACL failure never starts application scoring. A failed migration rolls back without marking applied; retain reviewed snapshot and targeted rollback/reapply runbook. Do not use a broad reset, hosted fallback or unreviewed reverse migration. Verify a safe request still succeeds after denial; stop only task-created services.

Cleanup later must track the exact resource IDs created by the test run, privately. Stop its services; delete only its submissions/progress/awards/ledger/links/challenges/role grants/audit fixtures in reviewed FK order using the cleanup operator, then delete disposable Auth accounts. admin_audit_log.admin_user_id and user_roles.granted_by lack cascading profile deletion and can block administrator-account cleanup; handle only test-created dependent rows explicitly before account deletion. Production audit retention is not to be weakened for test convenience. Verify residual counts against the pre-test baseline, report failures, and leave Supabase/platform data running/intact. A rollback-only SQL-role test does not cover HTTP transactions; HTTP-created resources need explicit cleanup.

## 8. Actual commands, results and limitations

`$D` = `C:\Users\tsush\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe`. Inline probes were transmitted in memory using `.venv/Scripts/python.exe -B -` or a PowerShell SQL variable; no probe source/secret files were created. Angle-bracket bodies below denote the in-memory SQL/assertion bodies described in this report, not hidden credentials or saved scripts.

| Executed command/check | Exit/result |
| --- | --- |
| git status --short; git rev-parse HEAD; git branch --show-current; source/instruction/report reads | main at baseline; 13 tracked modifications and 10 existing untracked files before report; no staged files; no AGENTS found in checked repository/ancestors/local target |
| `$D ps --filter name=veriquest-local-test --format '{{.Names}} {{.Image}} {{.Ports}}'`, inspect named DB/REST/gateway containers with safe output projection | 0 after permission escalation; verified project labels/workdir/images/ports/schema env; first sandbox attempt was access denied and did not run Docker |
| `<inventory SQL> \| $D exec -i -u postgres supabase_db_veriquest-local-test psql -X -v ON_ERROR_STOP=1 -P pager=off -d postgres` | 0 for each of three read-only batches; BEGIN/READ ONLY, metadata/counts, ROLLBACK observed |
| `.venv/Scripts/python.exe -B -c <driver module availability>`; host Get-Command psql | Python 0: four database drivers absent; no host psql found; no installation |
| `.venv/Scripts/python.exe -B - <host wire-auth + initial Linux probe>` | Windows authenticated read-only query passed; combined script exited 1 when Linux psql returned 2; temporary client absent |
| `.venv/Scripts/python.exe -B - <Linux default-network diagnostic retry>` | 2; server password-authentication error category only, private details withheld; client absent |
| `.venv/Scripts/python.exe -B - <binary-stdin Linux project/bridge assertions>` | 0; both Linux authenticated read-only queries matched expected six metadata values; both --rm clients absent |
| Linux subprocess command, each final client | `$D run --rm --pull never -i --name vq-db-gate-linux-<project-or-bridge>-20261001 --network <project-network-or-bridge> --read-only --cap-drop ALL --security-opt no-new-privileges:true --memory 128m --pids-limit 32 --user 65534:65534 --entrypoint sh <existing database image> -c <read stdin password privately; export PGPASSWORD/PGCONNECT_TIMEOUT/PGOPTIONS; exec psql -X -w -h host.docker.internal -p 54322 -U postgres -d postgres -v ON_ERROR_STOP=1 -At>`; no secret arguments |
| Private anonymous-key acquisition diagnostic attempts | Initial environment-key assumption and hardcoded inactive gateway file parsing each stopped with exit 1/no HTTP request. Corrected by reading active KONG_DECLARATIVE_CONFIG as in existing harness; no configuration change |
| `.venv/Scripts/python.exe -B - <active-path anonymous Data API assertions>` | 0: actual 200/404/406, PGRST205/PGRST106 and 3 assertions passed |
| `$D ps -a --filter name=vq-db-gate --format '{{.Names}} {{.Status}}'` | 0; no task containers remain |
| `$D ps --filter name=veriquest-local-test --format '{{.Names}} {{.Status}}'` | 0; existing ten Supabase containers still running |
| Preservation SHA256 baseline / final comparison; git diff --check | Verified after report creation; existing pending files/reports unchanged; whitespace check passes (LF/CRLF informational warnings) |

Failed Linux attempts were traced to Windows text-mode subprocess stdin changing LF to CRLF, making the Linux shell read a carriage return as part of the password. Binary stdin removed that transport defect. This did not require a password or PostgreSQL setting change. Temporary client cleanup succeeded for all attempts. No image was built/pulled; existing database image retained. A few initial source paths/globs did not match the real layout; corrected to singular profile/router.py and frontend client.ts. Those failed lookups are not test passes.

Verified **by execution:** exact local target, actual migration/schema/user absence, effective platform/default ACLs and role attributes, prerequisites/search path, host/Linux read-only authenticated PostgreSQL connectivity, anonymous Data API structure/schema exposure, scoped cleanup. Verified **by source:** current API/worker operations, unsafe future application policies and admin shortcut, seed publication without execution, runtime admin defaults and absence of application migration startup. **Not verified:** application student/admin permissions, restricted runtime logins, profile triggers, migration rollback/application, real asyncpg pool readiness, queued worker/native grading, accounting, revision lifecycle or production deployment.

## 9. Decisions and exact next task

Default engineering recommendation: implement the source-only permission/identity migration and configuration changes above, add production-calling/live-capable tests, review the full SQL and migration runner **before separately authorizing application**. Do not combine this with XP formula/quest ledger repair, outbox/idempotency/claim/finalization, Docker workspace changes or version-bound challenge validation; those remain their own release gates.

Decisions genuinely needed before live application:

1. Authorize the disposable snapshot, role/password provisioning, reviewed transactional migration application and three disposable test identities. Current authorization is assessment only.
2. Select migration tracking: recommended explicit allowlisted transactional runner with owner-only private checksum ledger and **deferred fixture 002**, or an independently reviewed Supabase CLI promotion path that handles that fixture safely. No automatic reset/seed.
3. Confirm whether direct own display-field PostgREST edits should remain allowed (recommended narrow optional compatibility surface) or whether all edits must be API-only. Neither may allow protected writes.
4. Explicitly provision only the disposable administrator for the test; do not identify or promote an existing real user. Current count is zero. Later production administrator grant/revocation and audit-retention policy require operator ownership.

No infrastructure install is demonstrated necessary for SQL probes. Existing environment is usable for later controlled permission tests, but it is **not schema/permission ready**. Local port exposure needs a separate containment decision if this environment persists on a reachable network.

## Final repository state

Nothing staged, committed or pushed. The thirteen tracked modifications and ten preexisting untracked files are preserved; this report adds **one** untracked file. Existing tracked diff remains 13 files, 209 insertions and 211 deletions. All thirty-three distinct preexisting pending/report files in the preservation baseline were checked by SHA256 after report creation.

Tracked modifications: .env.example; backend/app/admin/router.py; backend/app/core/config.py; backend/app/core/rate_limit.py; backend/app/submissions/router.py; backend/app/submissions/service.py; backend/tests/conftest.py; backend/tests/test_schemas.py; backend/tests/test_security.py; tests/test_verdict_integrity.py; worker/celeryconfig.py; worker/execution/sandbox.py; worker/tasks/hdl_task.py.

Untracked preserved: .dockerignore; backend/.dockerignore; backend/app/core/task_contract.py; backend/app/core/task_publisher.py; backend/tests/test_dispatch.py; docs/BACKEND_TASK_PUBLICATION.md; docs/handoff/BACKEND_STARTUP_DISPATCH_ASSESSMENT.md; docs/handoff/BACKEND_STARTUP_DISPATCH_REMEDIATION_REPORT.md; tests/test_worker_dispatch.py; worker/execution/profile.py. New assessment: docs/handoff/DATABASE_PERMISSION_GATE_ASSESSMENT.md.
