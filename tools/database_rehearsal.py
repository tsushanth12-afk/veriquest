"""Opt-in native SQL rehearsal: isolated tmpfs PG, never the Supabase target.

Calls production migration generators. Minimal Auth stubs do not prove Supabase
signup, event-trigger, PostgREST or application lifespan compatibility.
"""
import argparse
import json
from pathlib import Path
import re
import secrets
import subprocess
import sys
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.database_gate import load_plan, bootstrap_sql, apply_sql, GateError, TABLES

IMAGE = 'public.ecr.aws/supabase/postgres:17.11.0.002'


def isolation_evidence(obj):
    """Safe projection only: never emit Docker environment/config secrets."""
    host = obj['HostConfig']
    evidence = {
        'network_mode': host['NetworkMode'],
        'networks': list(obj['NetworkSettings']['Networks']),
        'network_addresses_absent': all(not n.get('IPAddress') and not n.get('GlobalIPv6Address')
                                       for n in obj['NetworkSettings']['Networks'].values()),
        'published_ports_absent': not host.get('PortBindings') and
            not any(obj['NetworkSettings'].get('Ports', {}).values()),
        'read_only_root': host['ReadonlyRootfs'],
        'cap_drop': host.get('CapDrop'),
        'security_options': host.get('SecurityOpt'),
        'mount_types': [m['Type'] for m in obj.get('Mounts', [])],
        'tmpfs_paths': sorted(host.get('Tmpfs', {})),
        'memory_bytes': host['Memory'], 'pids_limit': host['PidsLimit'],
        'user': obj['Config']['User'],
    }
    if not (evidence['network_mode'] == 'none' and evidence['networks'] == ['none']
            and evidence['network_addresses_absent'] and evidence['published_ports_absent']
            and evidence['read_only_root'] and evidence['cap_drop'] == ['ALL']
            and 'no-new-privileges:true' in evidence['security_options']
            and all(t == 'tmpfs' for t in evidence['mount_types'])
            and '/tmp' in evidence['tmpfs_paths'] and evidence['user'] == 'postgres'
            and 0 < evidence['memory_bytes'] <= 268435456 and 0 < evidence['pids_limit'] <= 64):
        raise GateError('Rehearsal isolation inspection failed')
    return evidence


class SQLProbe:
    """Actual local-socket login as the named role, not operator SET ROLE.

    Trust socket auth is confined to this network-none disposable cluster. This
    proves SQL authorization, not SCRAM/TCP authentication. Raw output/errors
    remain private; evidence records fixed labels, exit codes and SQLSTATE only.
    """
    def __init__(self, docker, name, result):
        self.docker, self.name, self.result = docker, name, result

    def __call__(self, text, *, role='supabase_admin', label, expected=None, error=None, marker=None):
        proc = subprocess.run([
            self.docker, 'exec', '-i', '-u', 'postgres', self.name, 'psql', '-h', '/tmp',
            '-X', '-q', '-A', '-t', '-v', 'ON_ERROR_STOP=1', '-v', 'VERBOSITY=verbose',
            '-U', role, '-d', 'postgres'], input=text.encode(), capture_output=True, timeout=60)
        stderr = proc.stderr.decode(errors='replace')
        match = re.search(r'ERROR:\s+([0-9A-Z]{5}):', stderr)
        code = match.group(1) if match else None
        record = {'label': label, 'role': role, 'exit_code': proc.returncode, 'sqlstate': code}
        self.result['sql_cases'].append(record)
        output = proc.stdout.decode().strip()
        passed = (proc.returncode != 0 and code == error and (marker is None or marker in stderr)) if error else (
            proc.returncode == 0 and (expected is None or output == expected))
        record['passed'] = passed
        if not passed:
            if 'precommit' in label or 'production apply' in label:
                # These scripts contain only reviewed migration SQL, never the
                # separately generated bootstrap SCRAM credentials.
                diagnostic = re.search(r'ERROR: ([^\r\n]+)', stderr)
                record['migration_error'] = diagnostic.group(1) if diagnostic else 'withheld'
                location = re.search(r'LINE (\d+):', stderr)
                record['line_number'] = int(location.group(1)) if location else None
            raise GateError('SQL assertion failed: ' + label + ' (SQLSTATE ' + str(code) + ')')
        self.result['assertions'] += 1
        return output

    def equal(self, text, expected, label, **kwargs):
        return self(text, expected=expected, label=label, **kwargs)

    def denied_unchanged(self, text, snapshot, label, *, role, error='42501', marker=None, prefix=''):
        before = self(snapshot, label=label + ': before')
        self(prefix + 'BEGIN; ' + text + '; COMMIT;', role=role, label=label,
             error=error, marker=marker)
        self.equal(snapshot, before, label + ': unchanged')


def state_snapshot_sql():
    # OIDs, ACLs, constraints, triggers, policies and fixtures/ledger must remain
    # identical after tracked replay. Only a digest is compared, not printed.
    rows = ','.join("(SELECT jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text) FROM " + table + " t)"
                    for table in TABLES)
    return """SELECT md5(jsonb_build_array(
      (SELECT jsonb_agg(to_jsonb(c) ORDER BY c.oid) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname IN ('public','private')),
      (SELECT jsonb_agg(to_jsonb(p) ORDER BY p.oid) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname IN ('public','private')),
      (SELECT jsonb_agg(to_jsonb(t) ORDER BY t.oid) FROM pg_trigger t),
      (SELECT jsonb_agg(to_jsonb(c) ORDER BY c.oid) FROM pg_constraint c),
      (SELECT jsonb_agg(to_jsonb(p) ORDER BY p.oid) FROM pg_policy p),
      (SELECT jsonb_agg(to_jsonb(m) ORDER BY version) FROM private.schema_migrations m),
      (SELECT jsonb_agg(to_jsonb(a) ORDER BY a.attrelid,a.attnum) FROM pg_attribute a
        JOIN pg_class c ON c.oid=a.attrelid JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname IN ('public','private')),
      (SELECT jsonb_agg(to_jsonb(d) ORDER BY d.oid) FROM pg_default_acl d),
      """ + rows + ")::text);"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--docker', required=True)
    parser.add_argument('--authorize-isolated-rehearsal', action='store_true')
    args = parser.parse_args()
    if not args.authorize_isolated_rehearsal:
        print('Refused: isolated rehearsal needs separate write authorization', file=sys.stderr)
        return 2
    name = 'vq-db-rehearsal-' + uuid4().hex
    result = {'container': name, 'isolated_platform_stubs': True, 'assertions': 0,
              'sql_cases': [], 'cleanup': False, 'failed': False}
    created = False

    def docker(*command):
        proc = subprocess.run([args.docker, *command], capture_output=True, timeout=60)
        if proc.returncode:
            raise GateError('Isolated Docker operation failed; private diagnostics withheld')
        return proc.stdout

    def check(condition, label):
        if not condition:
            raise GateError('Isolated state assertion failed: ' + label)
        result['assertions'] += 1

    try:
        manifest = load_plan()
        image = json.loads(docker('image', 'inspect', IMAGE))[0]
        # Never silently create an image-declared anonymous persistent volume.
        check(not image['Config'].get('Volumes'), 'image declares no persistent volumes')
        result['image_id'] = image['Id']
        result['migration_hashes'] = {m['version']: m['sha256'] for m in manifest['migrations']}
        created = True
        docker('run', '-d', '--pull', 'never', '--name', name, '--network', 'none', '--read-only',
               '--cap-drop=ALL', '--security-opt=no-new-privileges:true', '--memory=256m',
               '--pids-limit=64', '--user', 'postgres', '--tmpfs',
               '/tmp:rw,noexec,nosuid,size=160m,mode=1777', '--entrypoint', 'sleep', image['Id'], 'infinity')
        result['isolation_before'] = isolation_evidence(json.loads(docker('inspect', name))[0])
        check(True, 'Docker isolation before database creation')
        docker('exec', '-u', 'postgres', name, 'sh', '-c',
               'initdb -D /tmp/rehearsal --auth-local=trust --auth-host=reject >/dev/null && '
               'pg_ctl -D /tmp/rehearsal -o "-k /tmp -c listen_addresses= -c unix_socket_directories=/tmp" '
               '-l /tmp/server.log -w start >/dev/null')
        sql = SQLProbe(args.docker, name, result)
        sql('CREATE ROLE supabase_admin LOGIN SUPERUSER;', role='postgres', label='stub operator')
        sql("""CREATE ROLE anon NOLOGIN; CREATE ROLE authenticated NOLOGIN;
          CREATE ROLE service_role NOLOGIN BYPASSRLS;
          CREATE SCHEMA auth; CREATE SCHEMA vault; CREATE SCHEMA extensions;
          CREATE EXTENSION "uuid-ossp" SCHEMA extensions;
          CREATE TABLE auth.users(id uuid PRIMARY KEY,email text,raw_user_meta_data jsonb);
          CREATE FUNCTION auth.uid() RETURNS uuid LANGUAGE sql STABLE AS
           'SELECT nullif(current_setting(''request.jwt.claim.sub'',true),'''')::uuid';
          GRANT USAGE ON SCHEMA auth,public,extensions TO anon,authenticated,service_role;
          REVOKE CREATE ON SCHEMA public FROM PUBLIC;
          ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public
            GRANT ALL ON TABLES TO anon,authenticated,service_role;
        """, label='minimal platform stubs')
        result['postgres_version'] = sql('SHOW server_version;', label='PostgreSQL version')
        sql.equal("SHOW listen_addresses;", '', 'no PostgreSQL TCP listener')
        sql(bootstrap_sql(secrets.token_urlsafe(40), secrets.token_urlsafe(40)), label='production bootstrap')
        sql(apply_sql(manifest, rehearsal_failure=True), label='injected precommit failure',
            error='P0001', marker='Intentional isolated rehearsal rollback')
        sql.equal("SELECT count(*) FROM pg_tables WHERE schemaname IN ('public','private');", '0', 'rollback tables')
        sql.equal("SELECT to_regnamespace('private') IS NULL AND to_regclass('public.profiles') IS NULL;", 't', 'rollback schema and ledger')
        sql.equal("""SELECT NOT has_table_privilege('vq_owner','auth.users','TRIGGER')
          AND NOT has_column_privilege('vq_owner','auth.users','id','REFERENCES')
          AND NOT has_schema_privilege('vq_owner','public','CREATE')
          AND NOT has_schema_privilege('vq_owner','auth','USAGE')
          AND NOT has_database_privilege('vq_owner','postgres','CREATE')
          AND NOT EXISTS(SELECT 1 FROM pg_trigger WHERE tgrelid='auth.users'::regclass AND NOT tgisinternal);""",
          't', 'rollback temporary grants and Auth trigger')
        sql(apply_sql(manifest), label='fresh production apply and structural ACL assertions')
        sql.equal('SELECT count(*) FROM private.schema_migrations;', '4', 'fresh ledger')
        before = sql(state_snapshot_sql(), label='before tracked repeat')
        sql(apply_sql(manifest), label='tracked repeat and ACL assertions')
        sql.equal(state_snapshot_sql(), before, 'repeat is structural and data no-op')
        changed = json.loads(json.dumps(manifest))
        changed['migrations'][0]['sha256'] = '0' * 64
        sql(apply_sql(changed), label='checksum mismatch rejection', error='P0001', marker='Partial or changed ledger')
        sql.equal(state_snapshot_sql(), before, 'checksum rejection leaves original state')
        # Load by path: do not depend on tests being a Python package.
        import importlib.util
        spec = importlib.util.spec_from_file_location('rehearsal_operations',
            Path(__file__).resolve().parents[1] / 'tests/database_rehearsal_operations.py')
        operations = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(operations)
        operations.run_operations(sql)
        before = sql(state_snapshot_sql(), label='before populated repeat')
        sql(apply_sql(manifest), label='populated tracked repeat')
        sql.equal(state_snapshot_sql(), before, 'populated repeat unchanged')
        result['isolation_after'] = isolation_evidence(json.loads(docker('inspect', name))[0])
        check(True, 'Docker isolation after role operations')
    except Exception as exc:
        result['failed'] = True
        result['failure'] = str(exc) if isinstance(exc, GateError) else 'Private diagnostics withheld'
    finally:
        if created:
            try:
                proc = subprocess.run([args.docker, 'rm', '-f', name], capture_output=True, timeout=30)
                inspected = subprocess.run([args.docker, 'inspect', name], capture_output=True, timeout=10)
                absent = inspected.returncode != 0 and b'no such' in (inspected.stderr + inspected.stdout).lower()
                result['cleanup'] = proc.returncode == 0 and absent
                result['cleanup_evidence'] = {'remove_exit': proc.returncode,
                                              'inspect_exit': inspected.returncode,
                                              'exact_container_absent': absent}
            except Exception:
                result['cleanup'] = False
    print(json.dumps(result, indent=2))
    return 1 if result['failed'] or not result['cleanup'] else 0


if __name__ == '__main__':
    sys.exit(main())
