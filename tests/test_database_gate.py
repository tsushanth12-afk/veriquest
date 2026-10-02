"""Production runner/unit/source-contract tests. No database writes or live ACL claim."""
import copy
import hashlib
import json
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch,MagicMock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools import database_gate as gate
from tools import database_rehearsal as rehearsal


class DatabaseGateTests(unittest.TestCase):
    def test_isolation_rejects_network_ports_volumes_and_socket_binds(self):
        obj={'HostConfig':{'NetworkMode':'none','PortBindings':{},'ReadonlyRootfs':True,
             'CapDrop':['ALL'],'SecurityOpt':['no-new-privileges:true'],
             'Tmpfs':{'/tmp':'rw,noexec,nosuid'},'Memory':268435456,'PidsLimit':64},
             'NetworkSettings':{'Networks':{'none':{'IPAddress':'','GlobalIPv6Address':''}},'Ports':{}},
             'Config':{'User':'postgres'},'Mounts':[]}
        self.assertEqual(rehearsal.isolation_evidence(obj)['network_mode'],'none')
        for section,key,value in [('HostConfig','NetworkMode','bridge'),
                ('HostConfig','PortBindings',{'5432/tcp':[{'HostPort':'54322'}]}),
                ('HostConfig','ReadonlyRootfs',False),('HostConfig','CapDrop',[]),
                ('HostConfig','Memory',0),('HostConfig','PidsLimit',0),('Config','User','root')]:
            changed=copy.deepcopy(obj); changed[section][key]=value
            with self.assertRaises(gate.GateError):rehearsal.isolation_evidence(changed)
        for mount in [{'Type':'volume'},{'Type':'bind','Destination':'/var/run/docker.sock'}]:
            changed=copy.deepcopy(obj); changed['Mounts']=[mount]
            with self.assertRaises(gate.GateError):rehearsal.isolation_evidence(changed)

    def test_rehearsal_requires_exact_failure_reason_not_any_sql_error(self):
        result={'assertions':0,'sql_cases':[]}
        probe=rehearsal.SQLProbe('unused','isolated',result)
        for stderr in [b'ERROR: 42601: syntax error',b'ERROR: P0001: unrelated failure']:
            with patch.object(rehearsal.subprocess,'run',return_value=MagicMock(returncode=3,stdout=b'',stderr=stderr)):
                with self.assertRaises(gate.GateError):
                    probe('SELECT 1',label='expected rollback',error='P0001',marker='Intentional isolated rehearsal rollback')
        with patch.object(rehearsal.subprocess,'run',return_value=MagicMock(returncode=3,stdout=b'',
                stderr=b'ERROR: P0001: Intentional isolated rehearsal rollback')):
            probe('SELECT 1',label='expected rollback',error='P0001',marker='Intentional isolated rehearsal rollback')
        self.assertEqual(result['assertions'],1)

    def test_rehearsal_uses_actual_login_identity_and_private_stdin(self):
        result={'assertions':0,'sql_cases':[]}
        with patch.object(rehearsal.subprocess,'run',return_value=MagicMock(returncode=0,stdout=b't\n',stderr=b'')) as run:
            rehearsal.SQLProbe('docker','isolated',result)('SELECT session_user=current_user;',
                role='vq_worker',label='identity',expected='t')
        command=run.call_args.args[0]
        self.assertEqual(command[command.index('-U')+1],'vq_worker')
        self.assertEqual(command[command.index('-h')+1],'/tmp')
        self.assertNotIn('SELECT session_user=current_user;',command)
        self.assertIsInstance(run.call_args.kwargs['input'],bytes)

    def test_corrected_migrations_keep_owner_and_platform_boundaries(self):
        identity=(gate.ROOT/'supabase/migrations/005_profile_identity_gate.sql').read_text()
        self.assertLess(identity.index('RESET ROLE;'),identity.index('DROP TRIGGER on_auth_user_created'))
        self.assertLess(identity.index('DROP TRIGGER on_auth_user_created'),identity.index('SET LOCAL ROLE vq_owner;'))
        self.assertIn("session_user <> 'supabase_admin'",identity)
        self.assertNotIn('ALTER TABLE auth.users OWNER',identity)
        permission=(gate.ROOT/'supabase/migrations/004_permission_gate.sql').read_text()
        self.assertIn("IS DISTINCT FROM (CASE WHEN OLD.status='completed'",permission)

    def test_manifest_and_fixture_deferral(self):
        plan=gate.load_plan()
        self.assertEqual(tuple(x['version'] for x in plan['migrations']),gate.VERSIONS)
        self.assertEqual(plan['deferred'],['002'])
        self.assertNotIn('002_seed_demo_challenge',gate.apply_sql(plan))

    def test_changed_checksum_rejected(self):
        with patch.object(gate,'checksum',return_value='0'*64),self.assertRaises(gate.GateError):gate.load_plan()

    def test_unknown_partial_and_complete_tracking(self):
        plan=gate.load_plan();records={m['version']:m['sha256'] for m in plan['migrations']}
        self.assertEqual(gate.classify_state([],False,{},plan),'fresh')
        self.assertEqual(gate.classify_state(list(gate.TABLES),True,records,plan),'complete')
        for tables,ledger,rows in [(list(gate.TABLES),False,{}),([],True,{}),
                (list(gate.TABLES),True,dict(records,**{'002':'0'*64})),
                (list(gate.TABLES),True,dict(records,**{'001':'0'*64}))]:
            with self.assertRaises(gate.GateError):gate.classify_state(tables,ledger,rows,plan)

    def test_target_verification_rejects_wrong_labels_and_exposed_private(self):
        db={'Config':{'Labels':{'com.supabase.cli.project':'veriquest-local-test',
             'com.supabase.cli.workdir':gate.PROJECT}},'State':{'Running':True},
             'NetworkSettings':{'Ports':{'5432/tcp':[{'HostPort':'54322'}]}}}
        rest=copy.deepcopy(db);rest['Config']['Env']=['PGRST_DB_SCHEMAS=public,graphql_public']
        with patch.object(gate.subprocess,'run',return_value=MagicMock(stdout=json.dumps([db,rest]).encode())):
            self.assertEqual(gate.verify_target('docker'),db)
        for obj in [copy.deepcopy(rest),copy.deepcopy(rest)]:
            obj['Config']['Labels']['com.supabase.cli.project']='unrelated'
            with patch.object(gate.subprocess,'run',return_value=MagicMock(stdout=json.dumps([db,obj]).encode())):
                with self.assertRaises(gate.GateError):gate.verify_target('docker')
        rest['Config']['Env']=['PGRST_DB_SCHEMAS=public,private']
        with patch.object(gate.subprocess,'run',return_value=MagicMock(stdout=json.dumps([db,rest]).encode())):
            with self.assertRaises(gate.GateError):gate.verify_target('docker')

    def test_sql_transport_binary_and_errors_do_not_leak(self):
        with patch.object(gate.subprocess,'run',return_value=MagicMock(returncode=0,stdout=b'{}')) as run:
            self.assertEqual(gate.psql('docker','SELECT 1;'),'{}')
            self.assertIsInstance(run.call_args.kwargs['input'],bytes)
        with patch.object(gate.subprocess,'run',return_value=MagicMock(returncode=1,stderr=b'NEVER_LOG')):
            with self.assertRaises(gate.GateError) as exc:gate.psql('docker','SELECT 1;')
            self.assertNotIn('NEVER_LOG',str(exc.exception))

    def test_bootstrap_passwords_are_not_in_generated_sql(self):
        a='A'*40;b='B'*40
        sql=gate.bootstrap_sql(a,b)
        self.assertNotIn(a,sql);self.assertNotIn(b,sql)
        self.assertIn('SCRAM-SHA-256$',sql)
        self.assertIn("log_statement='none'",sql)
        with self.assertRaises(gate.GateError):gate.bootstrap_sql(a,a)
        with self.assertRaises(gate.GateError):gate.scram_verifier('short')

    def test_atomic_script_and_role_assertions_are_production(self):
        sql=gate.apply_sql(gate.load_plan())
        self.assertTrue(sql.startswith('BEGIN;'))
        self.assertTrue(sql.endswith('COMMIT;\n'))
        self.assertIn('pg_advisory_xact_lock',sql)
        self.assertIn('TRIGGER ON auth.users TO vq_owner',sql)
        self.assertIn('REVOKE TRIGGER ON auth.users FROM vq_owner',sql)
        self.assertNotIn('TRIGGER ON auth.users TO vq_api',sql)
        self.assertLess(sql.index('005: atomic'),sql.index('INSERT INTO private.schema_migrations'))
        self.assertIn('Intentional isolated rehearsal rollback',gate.apply_sql(gate.load_plan(),rehearsal_failure=True))

    def test_sql_contract_has_no_client_mutation_except_display(self):
        spec=json.loads((gate.ROOT/'tools/database_policy.json').read_text())
        for role in ['anon','authenticated']:
            for table,ops in spec['rights'][role].items():
                self.assertNotIn('INSERT',ops)
                if 'UPDATE' in ops:
                    self.assertEqual((role,table),('authenticated','public.profiles'))
                    self.assertEqual(set(ops['UPDATE']),{'display_name','bio','avatar_url'})
        self.assertNotIn('public.user_roles',spec['rights']['vq_worker'])
        self.assertNotIn('private_notes',spec['rights']['vq_worker']['private.challenge_secrets']['SELECT'])
        sql=(gate.ROOT/'supabase/migrations/004_permission_gate.sql').read_text()
        self.assertIn('DROP POLICY %I',sql)
        self.assertIn('REVOKE SELECT (%1$s)',sql)
        self.assertIn("status='queued' AND started_at IS NULL",sql)
        identity=(gate.ROOT/'supabase/migrations/005_profile_identity_gate.sql').read_text()
        self.assertIn("VALUES(NEW.id,'student')",identity)
        self.assertIn('ON CONFLICT (id) DO NOTHING',identity)
        self.assertNotIn("metadata->>'role'",identity)

    def test_fresh_preflight_refuses_unknown_namespaces_and_existing_users(self):
        base={'tables':[], 'ledger':False, 'private_exists':False, 'unexpected_relations':0,
              'public_helpers':0,'roles':[], 'auth_users':0,'uuid_ready':True}
        for change in ({'private_exists':True},{'unexpected_relations':1},{'public_helpers':1},
                       {'auth_users':1},{'uuid_ready':False}):
            with patch.object(gate,'psql',return_value=json.dumps(dict(base,**change))):
                with self.assertRaises(gate.GateError):gate.preflight('docker',gate.load_plan())
        with patch.object(gate,'psql',return_value=json.dumps(base)):
            self.assertEqual(gate.preflight('docker',gate.load_plan())['state'],'fresh')

    def test_write_capable_harnesses_refuse_without_opt_in(self):
        for file,args in [('tests/database_permission_live.py',[]),('tools/database_rehearsal.py',['--docker','unused'])]:
            spec=importlib.util.spec_from_file_location('isolated_gate_test',gate.ROOT/file)
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            with patch.object(sys,'argv',[file,*args]),patch.object(gate.subprocess,'run') as run:
                self.assertEqual(module.main(),2)
                run.assert_not_called()


if __name__=='__main__':unittest.main()
