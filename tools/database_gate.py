"""Local-only gate. Default plan/preflight are nonmutating; writes require explicit consent.

Passwords never belong in arguments/files. Bootstrap prompts privately. DDL is sent
by binary stdin to the verified local DB container, never a configurable hosted URL.
"""
import argparse
import base64
import getpass
import hashlib
import hmac
import json
import re
from pathlib import Path
import secrets
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PROJECT = r'C:\Users\tsush\Desktop\veriquest-local-test'
DB = 'supabase_db_veriquest-local-test'
VERSIONS = ('001', '003', '004', '005')
LOCK = 90431254322
TABLES = json.loads((ROOT/'tools/database_policy.json').read_text())['columns']


class GateError(RuntimeError):
    pass


def checksum(path):
    # Portable across Windows checkout CRLF and Linux checkout LF. No other normalization.
    return hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()


def load_plan():
    manifest = json.loads((ROOT/'tools/database_migrations.json').read_text())
    if tuple(x['version'] for x in manifest['migrations']) != VERSIONS or manifest['deferred'] != ['002']:
        raise GateError('Unexpected migration allow-list')
    listed = {x['file'] for x in manifest['migrations']} | {'002_seed_demo_challenge.sql'}
    if {p.name for p in (ROOT/'supabase/migrations').glob('*.sql')} != listed:
        raise GateError('Unknown migration files; review the manifest first')
    for item in manifest['migrations']:
        if '/' in item['file'] or '\\' in item['file']:
            raise GateError('Unsafe manifest path')
        if checksum(ROOT/'supabase/migrations'/item['file']) != item['sha256']:
            raise GateError('Reviewed migration checksum changed')
    if checksum(ROOT/'tools/database_policy.json') != manifest['policy_sha256']:
        raise GateError('Reviewed privilege specification changed')
    return manifest


def verify_target(docker):
    try:
        result = subprocess.run([docker,'inspect',DB,'supabase_rest_veriquest-local-test'],
                                capture_output=True,timeout=10,check=True)
        db, rest = json.loads(result.stdout)
        for obj in (db,rest):
            labels = obj['Config']['Labels']
            if (labels['com.supabase.cli.project'] != 'veriquest-local-test'
                    or labels['com.supabase.cli.workdir'].casefold() != PROJECT.casefold()
                    or not obj['State']['Running']):
                raise GateError('Wrong or stopped disposable project')
        if not any(p['HostPort']=='54322' for p in db['NetworkSettings']['Ports']['5432/tcp']):
            raise GateError('Wrong database port')
        env = dict(x.split('=',1) for x in rest['Config']['Env'] if '=' in x)
        if set(env['PGRST_DB_SCHEMAS'].split(',')) != {'public','graphql_public'}:
            raise GateError('Unexpected exposed API schemas')
        return db
    except Exception:
        raise GateError('Disposable target verification failed; no fallback allowed') from None


def psql(docker, sql, operator='supabase_admin'):
    proc = subprocess.run([docker,'exec','-i','-u','postgres',DB,'psql','-X','-q','-A','-t',
                           '-v','ON_ERROR_STOP=1','-U',operator,'-d','postgres'],
                          input=sql.encode(),capture_output=True,timeout=45)
    if proc.returncode:
        raise GateError('Local SQL gate failed; transaction aborted; private SQL diagnostics withheld')
    return proc.stdout.decode().strip()


def classify_state(tables, ledger, records, manifest):
    expected = {x['version']:x['sha256'] for x in manifest['migrations']}
    if not tables and not ledger and not records:
        return 'fresh'
    if set(tables) == set(TABLES) and ledger and records == expected:
        return 'complete'
    raise GateError('Partial, unknown or changed schema/ledger; no automatic repair')


def preflight(docker, manifest):
    names = ','.join("'"+x+"'" for x in TABLES)
    output = psql(docker,f"""BEGIN TRANSACTION READ ONLY; SET LOCAL statement_timeout='10s';
      SELECT pg_catalog.json_build_object(
        'tables',(SELECT coalesce(json_agg(n.nspname||'.'||c.relname),'[]') FROM pg_catalog.pg_class c
          JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname||'.'||c.relname IN ({names})),
        'ledger',pg_catalog.to_regclass('private.schema_migrations') IS NOT NULL,
        'private_exists',pg_catalog.to_regnamespace('private') IS NOT NULL,
        'unexpected_relations',(SELECT count(*) FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
          WHERE n.nspname IN ('public','private') AND c.relkind IN ('r','p','v','m','f')
            AND n.nspname||'.'||c.relname NOT IN ({names},'private.schema_migrations')),
        'public_helpers',(SELECT count(*) FROM pg_catalog.pg_proc p JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public'),
        'roles',(SELECT coalesce(json_agg(rolname),'[]') FROM pg_catalog.pg_roles WHERE rolname IN ('vq_owner','vq_api','vq_worker')),
        'auth_users',(SELECT count(*) FROM auth.users),
        'uuid_ready',pg_catalog.to_regprocedure('extensions.uuid_generate_v4()') IS NOT NULL);
      ROLLBACK;""")
    info = json.loads(output)
    records = {}
    if info['ledger']:
        records = dict(json.loads(psql(docker,"""BEGIN TRANSACTION READ ONLY;
          SELECT coalesce(json_agg(json_build_array(version,sha256)),'[]') FROM private.schema_migrations;
          ROLLBACK;""")))
    if 'public.profiles' in info['tables']:
        upgrade = json.loads(psql(docker,"""BEGIN TRANSACTION READ ONLY;
          SELECT json_build_object('missing_profiles',(SELECT count(*) FROM auth.users u LEFT JOIN public.profiles p ON p.id=u.id WHERE p.id IS NULL),
            'reserved_collisions',(SELECT count(*) FROM public.profiles WHERE pg_catalog.left(username,8)='vq_user_' AND username<>'vq_user_'||replace(id::text,'-','')),
            'invalid_display_rows',(SELECT count(*) FROM public.profiles WHERE char_length(display_name)>100 OR char_length(bio)>2000 OR char_length(avatar_url)>2048));
          ROLLBACK;"""))
        if any(upgrade.values()):
            raise GateError('Upgrade review required (counts only): '+json.dumps(upgrade))
    info['state'] = classify_state(info['tables'], info['ledger'], records, manifest)
    if info['unexpected_relations'] or info['public_helpers'] or (info['state']=='fresh' and info['private_exists']):
        raise GateError('Unknown application namespace objects; reviewed upgrade required')
    if info['state']=='fresh' and info['auth_users']:
        raise GateError('Existing Auth users need reviewed profile backfill; fresh runner refuses automatic backfill')
    if not info['uuid_ready']:
        raise GateError('Required platform UUID extension is absent; no automatic installation')
    return info


def scram_verifier(password, salt=None):
    if not isinstance(password,str) or not 32<=len(password)<=128 or any(not 33<=ord(c)<=126 for c in password):
        raise GateError('Runtime passwords must be distinct 32..128 printable nonspace ASCII characters')
    salt = secrets.token_bytes(16) if salt is None else salt
    salted = hashlib.pbkdf2_hmac('sha256',password.encode(),salt,4096)
    client = hmac.new(salted,b'Client Key',hashlib.sha256).digest()
    server = hmac.new(salted,b'Server Key',hashlib.sha256).digest()
    enc = lambda data:base64.b64encode(data).decode()
    return 'SCRAM-SHA-256$4096:'+enc(salt)+'$'+enc(hashlib.sha256(client).digest())+':'+enc(server)


def role_assertions():
    return """DO $$ BEGIN
      IF (SELECT count(*) FROM pg_catalog.pg_roles WHERE rolname IN ('vq_owner','vq_api','vq_worker'))<>3
        OR EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname IN ('vq_owner','vq_api','vq_worker')
          AND (rolsuper OR rolbypassrls OR rolcreatedb OR rolcreaterole OR rolreplication OR rolinherit
            OR rolcanlogin<>(rolname<>'vq_owner')))
        OR EXISTS (SELECT 1 FROM pg_catalog.pg_auth_members m JOIN pg_catalog.pg_roles r ON r.oid=m.member
          WHERE r.rolname IN ('vq_owner','vq_api','vq_worker'))
        OR EXISTS (SELECT 1 FROM pg_catalog.pg_auth_members m JOIN pg_catalog.pg_roles r ON r.oid=m.roleid
          JOIN pg_catalog.pg_roles u ON u.oid=m.member
          WHERE r.rolname IN ('vq_owner','vq_api','vq_worker')
            AND NOT (r.rolname='vq_owner' AND u.rolname='supabase_admin'))
      THEN RAISE EXCEPTION 'Role boundary assertion failed'; END IF;
    END $$;"""


def bootstrap_sql(api_password, worker_password):
    if api_password == worker_password:
        raise GateError('API and worker passwords must differ')
    verifiers = [scram_verifier(x) for x in (api_password,worker_password)]
    return f"""BEGIN; SET LOCAL log_statement='none'; SET LOCAL log_min_error_statement='panic';
      SELECT pg_catalog.pg_advisory_xact_lock({LOCK});
      DO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname IN ('vq_owner','vq_api','vq_worker'))
        THEN RAISE EXCEPTION 'Bootstrap roles already exist; no automatic rotation or repair'; END IF; END $$;
      CREATE ROLE vq_owner NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
      CREATE ROLE vq_api LOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD '{verifiers[0]}';
      CREATE ROLE vq_worker LOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD '{verifiers[1]}';
      GRANT vq_owner TO supabase_admin;
      GRANT CONNECT ON DATABASE postgres TO vq_api,vq_worker;
      {role_assertions()}
      COMMIT;"""


def assertions_sql():
    spec = json.loads((ROOT/'tools/database_policy.json').read_text())
    tests = []
    # Compare the installed policy set to the reviewed command/role identities.
    migration = (ROOT/'supabase/migrations/004_permission_gate.sql').read_text()
    policies = re.findall(r'CREATE POLICY (gate_\d+) ON (\w+)\.(\w+) FOR (SELECT|INSERT|UPDATE) TO (\w+)', migration)
    if len(policies) != 59:
        raise GateError('Unexpected reviewed policy set')
    expected_policies = ','.join("('%s','%s','%s','%s',ARRAY['%s']::name[])" % (schema,table,name,cmd,role)
                                 for name,schema,table,cmd,role in policies)
    tests.append(f"IF EXISTS (SELECT schemaname,tablename,policyname,cmd,roles FROM pg_catalog.pg_policies WHERE schemaname IN ('public','private') EXCEPT SELECT * FROM (VALUES {expected_policies}) v(s,t,p,c,r)) OR (SELECT count(*) FROM pg_catalog.pg_policies WHERE schemaname IN ('public','private'))<>59 THEN RAISE EXCEPTION 'Unexpected policy command/role set'; END IF;")
    for table, cols in spec['columns'].items():
        tests.append(f"IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_class WHERE oid='{table}'::regclass AND relrowsecurity AND pg_catalog.pg_get_userbyid(relowner)='vq_owner') THEN RAISE EXCEPTION 'Object ownership/RLS assertion failed'; END IF;")
        for role in ('anon','authenticated','service_role','vq_api','vq_worker'):
            ops = spec['rights'].get(role,{}).get(table,{})
            for operation in ('SELECT','INSERT','UPDATE','REFERENCES'):
                for col in cols:
                    expected = 'true' if col in ops.get(operation,[]) else 'false'
                    tests.append(f"IF pg_catalog.has_column_privilege('{role}','{table}','{col}','{operation}') <> {expected} THEN RAISE EXCEPTION 'Column permission assertion failed'; END IF;")
            for operation in ('DELETE','TRUNCATE','TRIGGER','MAINTAIN'):
                tests.append(f"IF pg_catalog.has_table_privilege('{role}','{table}','{operation}') THEN RAISE EXCEPTION 'Unexpected table privilege'; END IF;")
    return role_assertions()+"\nDO $$ BEGIN\n"+'\n'.join(tests)+"""
      IF EXISTS (SELECT 1 FROM pg_catalog.pg_policies WHERE schemaname IN ('public','private') AND roles @> ARRAY['public']::name[])
      THEN RAISE EXCEPTION 'Broad PUBLIC policy remains'; END IF;
      IF EXISTS (SELECT 1 FROM pg_catalog.pg_proc p JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace
        WHERE n.nspname='private' AND (pg_catalog.pg_get_userbyid(p.proowner)<>'vq_owner'
          OR p.proconfig IS DISTINCT FROM ARRAY['search_path=""']::text[]))
      THEN RAISE EXCEPTION 'Unsafe private function configuration'; END IF;
      IF (SELECT count(*) FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
          WHERE n.nspname IN ('public','private') AND c.relkind IN ('r','p','v','m','f'))<>15
        OR (SELECT count(*) FROM pg_catalog.pg_proc p JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='private')<>5
        OR pg_catalog.pg_get_userbyid((SELECT nspowner FROM pg_catalog.pg_namespace WHERE nspname='private'))<>'vq_owner'
      THEN RAISE EXCEPTION 'Unexpected application object set'; END IF;
      IF EXISTS (SELECT 1 FROM pg_catalog.pg_proc p JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace
          WHERE n.nspname='private' AND p.prosecdef<>(p.proname IN ('handle_new_user','invalidate_challenge_on_secret_change')))
      THEN RAISE EXCEPTION 'Unexpected helper security mode'; END IF;
      IF pg_catalog.to_regprocedure('public.handle_new_user()') IS NOT NULL
        OR pg_catalog.to_regprocedure('public.update_updated_at()') IS NOT NULL
        OR pg_catalog.to_regprocedure('private.handle_new_user()') IS NULL
      THEN RAISE EXCEPTION 'Unexpected exposed application helper'; END IF;
      IF EXISTS (SELECT 1 FROM pg_catalog.pg_roles r WHERE rolname IN ('anon','authenticated','service_role','vq_api','vq_worker')
        AND pg_catalog.has_table_privilege(r.oid,'private.schema_migrations','SELECT,INSERT,UPDATE,DELETE,TRUNCATE'))
      THEN RAISE EXCEPTION 'Migration ledger is not owner-only'; END IF;
      IF pg_catalog.pg_get_userbyid((SELECT relowner FROM pg_catalog.pg_class WHERE oid='private.schema_migrations'::regclass))<>'vq_owner'
      THEN RAISE EXCEPTION 'Migration ledger ownership assertion failed'; END IF;
      IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_default_acl d WHERE d.defaclrole='vq_owner'::regrole AND d.defaclnamespace=0 AND d.defaclobjtype='f')
        OR EXISTS (SELECT 1 FROM pg_catalog.pg_default_acl d CROSS JOIN LATERAL pg_catalog.aclexplode(d.defaclacl) a
          WHERE d.defaclrole='vq_owner'::regrole AND a.grantee<>d.defaclrole
            AND (d.defaclnamespace=0 OR d.defaclnamespace IN ('public'::regnamespace,'private'::regnamespace)))
      THEN RAISE EXCEPTION 'Unsafe application owner default privileges'; END IF;
      IF EXISTS (SELECT 1 FROM pg_catalog.pg_roles r WHERE rolname IN ('vq_api','vq_worker') AND
        (pg_catalog.has_schema_privilege(r.oid,'auth','USAGE') OR pg_catalog.has_schema_privilege(r.oid,'vault','USAGE') OR
         pg_catalog.has_schema_privilege(r.oid,'public','CREATE') OR pg_catalog.has_schema_privilege(r.oid,'private','CREATE')))
      THEN RAISE EXCEPTION 'Unexpected runtime schema privilege'; END IF;
      IF EXISTS (SELECT 1 FROM pg_catalog.pg_roles r WHERE rolname IN ('anon','authenticated','service_role') AND
        (pg_catalog.has_schema_privilege(r.oid,'private','USAGE') OR pg_catalog.has_schema_privilege(r.oid,'private','CREATE')))
      THEN RAISE EXCEPTION 'Private schema exposed to client'; END IF;
      IF EXISTS (SELECT 1 FROM pg_catalog.pg_roles r WHERE rolname IN ('vq_api','vq_worker') AND
        (EXISTS(SELECT 1 FROM pg_catalog.pg_class c WHERE c.relowner=r.oid) OR
         EXISTS(SELECT 1 FROM pg_catalog.pg_proc p WHERE p.proowner=r.oid)))
      THEN RAISE EXCEPTION 'Runtime role owns objects'; END IF;
      IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_trigger t WHERE t.tgrelid='auth.users'::regclass
        AND t.tgname='on_auth_user_created' AND t.tgenabled='O'
        AND t.tgfoid='private.handle_new_user()'::regprocedure AND NOT t.tgisinternal)
      THEN RAISE EXCEPTION 'Auth profile trigger assertion failed'; END IF;
      IF EXISTS (SELECT 1 FROM pg_catalog.pg_proc p JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace
        CROSS JOIN pg_catalog.pg_roles r WHERE n.nspname='private' AND r.rolname IN ('anon','authenticated','service_role','vq_api','vq_worker')
          AND pg_catalog.has_function_privilege(r.oid,p.oid,'EXECUTE'))
      THEN RAISE EXCEPTION 'Private helper executable by untrusted role'; END IF;
    END $$;
    """


def apply_sql(manifest, *, rehearsal_failure=False):
    # Advisory lock and ledger check are repeated IN the transaction: preflight is not a lock.
    expected = ','.join("('"+m['version']+"','"+m['sha256']+"')" for m in manifest['migrations'])
    script = f"""BEGIN; SET LOCAL log_statement='none'; SET LOCAL log_min_error_statement='panic';
      SET LOCAL statement_timeout='30s'; SET LOCAL lock_timeout='5s';
      SELECT pg_catalog.pg_advisory_xact_lock({LOCK});
      {role_assertions()}
      SELECT pg_catalog.to_regclass('private.schema_migrations') IS NOT NULL AS complete \\gset
      \\if :complete
        DO $$ BEGIN
          IF (SELECT count(*) FROM private.schema_migrations)<>4 OR EXISTS(
            SELECT version,sha256 FROM private.schema_migrations EXCEPT SELECT * FROM (VALUES {expected}) x(version,sha256))
          THEN RAISE EXCEPTION 'Partial or changed ledger'; END IF;
        END $$;
      \\else
        DO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
          WHERE n.nspname IN ('public','private') AND c.relkind IN ('r','p','v','m','f'))
          OR EXISTS(SELECT 1 FROM auth.users)
          THEN RAISE EXCEPTION 'Unknown schema or existing users need reviewed upgrade/backfill'; END IF; END $$;
        GRANT CREATE ON SCHEMA public TO vq_owner;
        GRANT CREATE ON DATABASE postgres TO vq_owner;
        GRANT USAGE ON SCHEMA extensions,auth TO vq_owner;
        GRANT TRIGGER ON auth.users TO vq_owner;
        GRANT REFERENCES (id) ON auth.users TO vq_owner;
        SET LOCAL ROLE vq_owner;
        SET LOCAL search_path=pg_catalog,public,extensions;
        ALTER DEFAULT PRIVILEGES FOR ROLE vq_owner REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;
    """
    for item in manifest['migrations']:
        script += '\n'+(ROOT/'supabase/migrations'/item['file']).read_text()+'\n'
    script += """
        CREATE TABLE private.schema_migrations(version text PRIMARY KEY,sha256 text NOT NULL CHECK(length(sha256)=64),applied_at timestamptz NOT NULL DEFAULT pg_catalog.now());
        REVOKE ALL ON private.schema_migrations FROM PUBLIC,anon,authenticated,service_role,vq_api,vq_worker;
        RESET ROLE;
        REVOKE CREATE ON DATABASE postgres FROM vq_owner;
        REVOKE CREATE ON SCHEMA public FROM vq_owner;
        REVOKE USAGE ON SCHEMA auth FROM vq_owner;
        REVOKE TRIGGER ON auth.users FROM vq_owner;
        REVOKE REFERENCES (id) ON auth.users FROM vq_owner;
        GRANT USAGE ON SCHEMA extensions TO vq_api,vq_worker;
    """
    for m in manifest['migrations']:
        script += f"INSERT INTO private.schema_migrations(version,sha256) VALUES('{m['version']}','{m['sha256']}');\n"
    script += '\\endif\n'+assertions_sql()
    if rehearsal_failure:
        script += "DO $$ BEGIN RAISE EXCEPTION 'Intentional isolated rehearsal rollback'; END $$;\n"
    return script+'COMMIT;\n'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--docker',required=True)
    parser.add_argument('--mode',choices=['plan','preflight','bootstrap','apply'],default='plan')
    parser.add_argument('--authorize-local-write',action='store_true')
    args=parser.parse_args()
    try:
        manifest=load_plan(); verify_target(args.docker)
        if args.mode=='plan':
            print(json.dumps({'mode':'plan','sequence':list(VERSIONS),'deferred':['002'],'writes':False})); return
        info=preflight(args.docker,manifest)
        if args.mode=='preflight':
            if info['state']=='complete': psql(args.docker,'BEGIN TRANSACTION READ ONLY;'+assertions_sql()+'ROLLBACK;')
            print(json.dumps({'mode':'preflight','state':info['state'],'role_count':len(info['roles']),
                              'application_table_count':len(info['tables']),'auth_user_count':info['auth_users'],'writes':False})); return
        if not args.authorize_local_write:
            raise GateError('Write mode requires separate authorization and --authorize-local-write')
        if args.mode=='bootstrap':
            if info['state']!='fresh' or info['roles']: raise GateError('Bootstrap requires verified empty application state and absent roles')
            api=getpass.getpass('Private API password (32..128 nonspace ASCII characters): ')
            worker=getpass.getpass('Different private worker password: ')
            psql(args.docker,bootstrap_sql(api,worker)); api=worker=None
        else:
            if set(info['roles'])!={'vq_owner','vq_api','vq_worker'}: raise GateError('Reviewed role bootstrap required')
            psql(args.docker,apply_sql(manifest))
        print(json.dumps({'mode':args.mode,'success':True,'deferred':['002']}))
    except Exception as exc:
        print('Database gate failed: '+(str(exc) if isinstance(exc,GateError) else 'private diagnostics withheld'),file=sys.stderr)
        return 1
    return 0


if __name__=='__main__': sys.exit(main())
