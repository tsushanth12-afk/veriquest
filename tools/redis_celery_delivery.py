"""Opt-in local real Redis/Celery delivery gate; never part of unit discovery.

Windows DPAPI intent precedes resource creation. Historical snapshots are immutable;
restart provenance is recorded separately after retained-volume/full-schema checks.
No secret in argv, Docker configuration, plaintext files or safe reports.
"""
import argparse
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import time
from uuid import UUID, uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import database_gate as gate
from tools import database_live_gate as private
from tools import database_live_resources as resources

LABEL = 'io.veriquest.delivery-gate'
VOLUME = 'supabase_db_veriquest-local-test'
VOLUME_CREATED = '2026-10-01T06:31:44Z'
ISSUER = 'http://127.0.0.1:54321/auth/v1'
CHECKS = ('api-package','worker-package','api-regression','worker-dispatch','worker-verdict')
LAUNCH = "import json,os,sys; c=json.loads(sys.stdin.buffer.readline()); os.environ.update(c['environment']); os.execvp(c['command'][0],c['command'])"


def decode_message(raw, expected_task, expected_args):
    """Assert the actual Kombu wire envelope, not a synthetic receipt."""
    message = json.loads(raw)
    headers = message['headers']
    args, kwargs, _embed = json.loads(base64.b64decode(message['body'], validate=True))
    task_id = str(UUID(headers['id']))
    if (headers['task'] != expected_task or args != expected_args or kwargs != {}
            or message['properties']['delivery_info']['routing_key'] != 'hdl_execution'):
        raise gate.GateError('Actual broker envelope disagrees with canonical task')
    return {'task_id': task_id, 'task': expected_task, 'queue': 'hdl_execution'}


def validate_intent(intent, target, manifest):
    resources.validate_plan(intent['resources'], target, manifest)
    nonce = intent['resources']['nonce']
    expected = {key: 'vq-delivery-'+key+'-'+nonce for key in ('redis','api','worker','probe','network')}
    expected_tags = {key: 'vq-delivery-'+key+':'+nonce for key in ('api','worker')}
    if (intent['format'] != 1 or intent['names'] != expected or intent['tags'] != expected_tags
            or intent['checks'] != {key:'vq-delivery-'+key+'-'+nonce for key in CHECKS}
            or intent['idempotency_keys'] != ['delivery-'+nonce+'-'+str(i) for i in range(3)]):
        raise gate.GateError('Invalid exact delivery intent')


class DeliveryGate:
    def __init__(self, docker, directory):
        self.docker = docker
        self.directory = directory
        self.report = {'assertions': 0, 'http': [], 'commands': [], 'tasks': []}
        self.attachments = []
        self.intent = None

    def check(self, value, name):
        if not value:
            raise gate.GateError('Failed assertion: '+name)
        self.report['assertions'] += 1

    def call(self, args, stdin=None, timeout=45, allow_failure=False):
        proc = subprocess.run([self.docker, *args], input=stdin, capture_output=True, timeout=timeout)
        # Arguments are constructed without secrets. Never record stdout/diagnostics.
        self.report['commands'].append({'args': args, 'exit_code': proc.returncode})
        if proc.returncode and not allow_failure:
            raise gate.GateError('Docker operation failed: '+args[0]+'; private diagnostics withheld')
        return proc

    def inspect(self, name, kind='container'):
        proc = self.call([kind,'inspect',name], allow_failure=True)
        if proc.returncode == 0:
            return json.loads(proc.stdout)[0]
        diagnostics=proc.stderr.decode(errors='replace')
        if name in diagnostics and re.search(r'No such (?:object|container|image)|(?:network|volume).*not found',diagnostics,re.I):
            return None
        raise gate.GateError('Docker inspection unavailable; absence is unverified')

    def inventory(self):
        names = list(gate.TABLES)
        counts = ','.join("'"+n+"',(SELECT count(*) FROM "+n+")" for n in names)
        return json.loads(gate.psql(self.docker, 'BEGIN TRANSACTION READ ONLY; SET LOCAL statement_timeout=\'10s\'; SELECT json_build_object('+counts+",'auth_users',(SELECT count(*) FROM auth.users),'auth_identities',(SELECT count(*) FROM auth.identities),'auth_audit',(SELECT count(*) FROM auth.audit_log_entries)); ROLLBACK;"))

    def provenance(self, fresh):
        private.secure_directory(self.directory)
        manifest = gate.load_plan()
        target = gate.verify_target(self.docker)
        mounts = [m for m in target['Mounts'] if m['Destination']=='/var/lib/postgresql/data']
        self.check(len(mounts)==1 and mounts[0]['Type']=='volume' and mounts[0]['Name']==VOLUME, 'retained database volume mount')
        volume = self.inspect(VOLUME, 'volume')
        self.check(volume is not None and volume['CreatedAt']==VOLUME_CREATED
                   and volume['Labels'].get('com.supabase.cli.project')=='veriquest-local-test'
                   and volume['Labels'].get('com.docker.compose.project')=='veriquest-local-test'
                   and volume['Driver']=='local' and not volume.get('Options'), 'retained volume provenance')
        self.check(gate.preflight(self.docker, manifest)['state']=='complete', 'complete applied ledger')
        gate.psql(self.docker, 'BEGIN TRANSACTION READ ONLY;'+gate.assertions_sql()+'ROLLBACK;')
        original = private.read_sealed(self.directory/'snapshot.dpapi')
        self.check(original['project']=='veriquest-local-test' and original['manifest']==manifest
                   and original['image_id']==target['Image'], 'historical snapshot provenance')
        dump = base64.b64decode(original['database_dump'], validate=True)
        self.check(hashlib.sha256(dump).hexdigest()==original['dump_sha256'], 'historical archive checksum')
        readability = private.restore_readability(self.docker, dump)
        credentials = private.read_sealed(self.directory/'runtime-credentials.dpapi')
        self.check(credentials['api_password'] != credentials['worker_password'], 'separate retained credentials')
        state = self.inventory()
        if fresh:
            self.check(all(v==0 for k,v in state.items() if k!='auth_audit'), 'empty application and Auth baseline')
        import httpx
        with httpx.Client(trust_env=False,timeout=10) as client:
            self.check(client.get(ISSUER+'/health').status_code==200, 'actual Auth health')
            keys = client.get(ISSUER+'/.well-known/jwks.json')
            self.check(keys.status_code==200, 'actual JWKS transport')
            published = keys.json()['keys']
            self.check(len(published)==1 and published[0]['alg']=='ES256' and published[0]['kty']=='EC'
                       and published[0]['crv']=='P-256', 'expected signing metadata')
        auth = self.inspect('supabase_auth_veriquest-local-test')
        self.check(auth['Config']['Labels'].get('com.supabase.cli.project')=='veriquest-local-test'
                   and auth['Config']['Labels'].get('com.supabase.cli.workdir','').casefold()==gate.PROJECT.casefold(), 'Auth project identity')
        env = dict(x.split('=',1) for x in auth['Config']['Env'] if '=' in x)
        self.check(env.get('GOTRUE_JWT_ISSUER')==ISSUER, 'exact Auth issuer')
        # Append a new attestation, never edit historical snapshot metadata/pins.
        rebind = {'format':1,'project':'veriquest-local-test','old_container_id':original['container_id'],
                  'new_container_id':target['Id'],'image_id':target['Image'],'volume':VOLUME,
                  'volume_created':volume['CreatedAt'],'manifest':manifest,
                  'snapshot_ciphertext_sha256':hashlib.sha256((self.directory/'snapshot.dpapi').read_bytes()).hexdigest(),
                  'retained_state':state,'full_permission_assertions':True, 'archive_readability':readability}
        private.sealed_write(self.directory/('delivery-rebind-'+uuid4().hex+'.dpapi'), rebind)
        self.report['preflight'] = {'state':'complete','roles':3,'tables':14,'auth_users':state['auth_users'],
                                   'baseline_counts':state,'container_identity_changed':original['container_id']!=target['Id'],
                                   'immutable_snapshot_preserved':True,'separate_rebind_attestation':True,
                                   'volume_created':volume['CreatedAt'],'auth_health':200,'jwks_algorithm':'ES256'}
        return target, manifest, credentials

    def new_intent(self, target, manifest):
        plan = resources.new_plan(target, manifest)
        n = plan['nonce']
        intent = {'format':1,'resources':plan,
                  'names':{k:'vq-delivery-'+k+'-'+n for k in ('redis','api','worker','probe','network')},
                  'tags':{k:'vq-delivery-'+k+':'+n for k in ('api','worker')},
                  'checks':{k:'vq-delivery-'+k+'-'+n for k in CHECKS},
                  'idempotency_keys':['delivery-'+n+'-'+str(i) for i in range(3)]}
        validate_intent(intent,target,manifest)
        path = self.directory/('delivery-intent-'+uuid4().hex+'.dpapi')
        private.sealed_write(path,intent)
        validate_intent(private.read_sealed(path),target,manifest)
        self.intent = intent
        self.report['private_journal'] = str(path)

    def owned(self, obj):
        return obj['Config']['Labels'].get(LABEL)==self.intent['resources']['nonce']

    def isolation(self, name, api=False, probe=False):
        obj = self.inspect(name)
        host = obj['HostConfig']
        ports = host.get('PortBindings') or {}
        self.check(self.owned(obj) and host['ReadonlyRootfs'] and host['CapDrop']==['ALL']
                   and 'no-new-privileges:true' in host['SecurityOpt'] and host['PidsLimit']==64
                   and 0 < host['Memory'] <= 512*1024*1024 and not host['Privileged'], 'container restrictions '+('api' if api else 'probe' if probe else 'service'))
        self.check(not ports if not api else set(ports)=={'8000/tcp'} and all(p['HostIp']=='127.0.0.1' for p in ports['8000/tcp']), 'temporary port boundaries')
        self.check(set(obj['NetworkSettings']['Networks'])=={self.intent['names']['network']}, 'unique test network only')
        self.check(all(m['Type']=='bind' and not m['RW'] and m['Destination'].startswith('/gate/') for m in obj['Mounts'] if m['Type']!='tmpfs')
                   and not any('docker.sock' in m['Destination'] for m in obj['Mounts']), 'no socket or persistent volume')
        self.check(not any(x.startswith(('DATABASE_URL=','API_DATABASE_URL=','WORKER_DATABASE_URL=','SUPABASE_SERVICE_KEY=')) for x in obj['Config']['Env']), 'no runtime credentials in Docker config')
        self.report.setdefault('isolation',[]).append({'service':'api' if api else 'probe' if probe else 'redis_or_worker',
            'readonly':True,'cap_drop_all':True,'no_new_privileges':True,'pids':64,
            'memory_bytes':host['Memory'],'socket':False,'persistent_volumes':False,'loopback_port_only':api})
        return obj

    def flags(self, name):
        return ['--name',name,'--label',LABEL+'='+self.intent['resources']['nonce'],
                '--network',self.intent['names']['network'],'--read-only','--cap-drop','ALL',
                '--security-opt','no-new-privileges:true','--memory','512m','--cpus','1','--pids-limit','64',
                '--tmpfs','/tmp:rw,noexec,nosuid,size=32m','--log-opt','max-size=128k','--log-opt','max-file=1']

    def probe(self, capsule):
        name = self.intent['names']['probe']
        self.check(self.inspect(name) is None, 'probe name unused')
        args = ['create','-i',*self.flags(name),
                '--mount','type=bind,source='+str(ROOT/'tools')+',target=/gate/tools,readonly',
                '--mount','type=bind,source='+str(ROOT/'tests/redis_celery_delivery_probe.py')+',target=/gate/probe.py,readonly',
                self.intent['tags']['api'],'python','-B','/gate/probe.py']
        self.call(args)
        try:
            self.isolation(name,probe=True)
            proc = self.call(['start','-a','-i',name], json.dumps(capsule).encode(), timeout=60, allow_failure=True)
            result = json.loads(proc.stdout)
            if proc.returncode or result.get('failed'):
                raise gate.GateError('Private '+capsule['mode']+' probe failed: '+result.get('failure_type','unknown'))
            return result
        finally:
            obj = self.inspect(name)
            if obj and self.owned(obj):
                self.call(['rm','-f',name])

    def service(self, role, environment):
        name = self.intent['names'][role]
        tag = self.intent['tags'][role]
        command = self.inspect(tag,'image')['Config']['Cmd']
        ports = ['-p','127.0.0.1::8000'] if role=='api' else []
        self.call(['create','-i',*self.flags(name),*ports,'--entrypoint','python',tag,'-B','-c',LAUNCH])
        self.isolation(name,api=role=='api')
        child = subprocess.Popen([self.docker,'start','-a','-i',name],stdin=subprocess.PIPE,
                                 stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        self.attachments.append(child)
        child.stdin.write(json.dumps({'environment':environment,'command':command}).encode()+b'\n')
        child.stdin.flush()
        child.stdin.close()

    def redis(self, *command):
        return self.call(['exec',self.intent['names']['redis'],'redis-cli','--raw',*command]).stdout.decode().strip()

    def empty_queue(self):
        return self.redis('LLEN','hdl_execution')=='0' and self.redis('HLEN','unacked')=='0'

    def wait(self, condition, label, timeout=40):
        end = time.monotonic()+timeout
        while time.monotonic()<end:
            if condition():
                self.check(True,label)
                return
            time.sleep(0.25)
        raise gate.GateError('Timed out: '+label)

    def message(self, task, args):
        self.check(self.redis('LLEN','hdl_execution')=='1', 'exactly one queued envelope')
        record = decode_message(self.redis('LINDEX','hdl_execution','0'),task,args)
        self.report['tasks'].append(record)
        return record

    def receipt(self, record):
        name = self.intent['names']['worker']
        def received():
            proc = self.call(['logs','--tail','150',name])
            logs = proc.stdout+proc.stderr
            match = (record['task']+'['+record['task_id']+'] received').encode()
            return match in logs
        self.wait(received,'actual worker received canonical task')
        record['actual_worker_received']=True

    def packaged_checks(self):
        checks=[]
        def flags(key):
            return ['run','--rm','--name',self.intent['checks'][key],
                    '--label',LABEL+'='+self.intent['resources']['nonce'],'--network','none',
                    '--read-only','--cap-drop','ALL','--security-opt','no-new-privileges:true',
                    '--memory','512m','--pids-limit','64','--tmpfs','/tmp:rw,noexec,nosuid,size=32m']
        for role in ('api','worker'):
            roots = [('app', ROOT/'backend/app')] if role=='api' else [('backend/app',ROOT/'backend/app'),('worker',ROOT/'worker')]
            expected={prefix+'/'+str(p.relative_to(root)).replace('\\','/'):gate.checksum(p)
                      for prefix,root in roots for p in root.rglob('*.py') if '__pycache__' not in p.parts}
            entry="import json,hashlib,pathlib; print(json.dumps({str(p.relative_to('/app')):hashlib.sha256(p.read_bytes().replace(b'\\r\\n',b'\\n')).hexdigest() for r in "+repr([x[0] for x in roots])+" for p in (pathlib.Path('/app')/r).rglob('*.py') if '__pycache__' not in p.parts}))"
            proc=self.call([*flags(role+'-package'),
                            self.intent['tags'][role],'python','-B','-c',entry])
            self.check(json.loads(proc.stdout)==expected,'actual packaged source hashes '+role)
            packages=['asyncpg','celery','kombu','redis','docker','pydantic','pydantic-settings']
            if role=='api': packages += ['fastapi','uvicorn','python-jose','cryptography','httpx','pytest']
            versions="import importlib.metadata as m,json,platform; print(json.dumps({'python':platform.python_version(),'packages':{p:m.version(p) for p in "+repr(packages)+"}}))"
            resolved=self.call([*flags(role+'-package'),self.intent['tags'][role],'python','-B','-c',versions])
            checks.append({'image':role,'image_id':self.inspect(self.intent['tags'][role],'image')['Id'],
                           'source_files_verified':len(expected),'versions':json.loads(resolved.stdout)})
        api=self.call([*flags('api-regression'),self.intent['tags']['api'],
                       'python','-B','-m','pytest','-p','no:cacheprovider','-q','tests'],timeout=60)
        self.report['api_regressions']=api.stdout.decode().strip()
        for file,key in (('test_worker_dispatch.py','worker-dispatch'),('test_verdict_integrity.py','worker-verdict')):
            mounts=[('tests/'+file,'tests/test.py')]
            if key=='worker-verdict':
                mounts += [(p,p) for p in ('tests/verdict_integrity_cases.json','src/evaluator/testbenchCatalog.ts',
                                          'supabase/migrations/002_seed_demo_challenge.sql')]
            bindings=[arg for source,dest in mounts for arg in ('--mount','type=bind,source='+str(ROOT/source)+',target=/app/'+dest+',readonly')]
            proc=self.call([*flags(key),*bindings,self.intent['tags']['worker'],'python','-B','/app/tests/test.py'],timeout=60)
            # Unit test output is credential-free; only persist totals, not raw failure diagnostics.
            output=proc.stdout+proc.stderr
            match=re.search(rb'Ran (\d+) tests?',output)
            self.check(match is not None and b'\nOK' in output,'production worker regression suite '+file)
            checks.append({'test':file,'passed_methods':int(match[1]),'exit_code':0})
        self.report['packaged_checks']=checks

    def run_live(self, credentials):
        import httpx
        spec=importlib.util.spec_from_file_location('permission_live', ROOT/'tests/database_permission_live.py')
        helpers=importlib.util.module_from_spec(spec); spec.loader.exec_module(helpers)
        setup=helpers.private_credentials(self.docker)
        plan=self.intent['resources']; names=self.intent['names']
        operator={'operator_dsn':helpers.dsn('supabase_admin',setup['operator_password']), 'plan':plan}
        self.operator=operator; self.service_key=setup['keys']['service_role']
        for role in ('api','worker'):
            self.report.setdefault('pool_checks',[]).append(self.probe({'mode':'runtime','role':'vq_'+role,
                'dsn':helpers.dsn('vq_'+role,credentials[role+'_password'])}))
        broker='redis://'+names['redis']+':6379/0'
        self.service('api',{'DATABASE_URL':helpers.dsn('vq_api',credentials['api_password']),
            'REDIS_URL':broker,'JWT_ISSUER':ISSUER,'JWT_JWKS_URL':'http://host.docker.internal:54321/auth/v1/.well-known/jwks.json',
            'JWT_ALGORITHMS':'ES256','JWT_AUDIENCE':'authenticated','TASK_PUBLISH_TIMEOUT_SECONDS':'2'})
        self.wait(lambda: self.inspect(names['api'])['State']['Running'], 'API container started')
        self.wait(lambda: bool(self.inspect(names['api'])['NetworkSettings']['Ports'].get('8000/tcp')), 'API loopback port assigned')
        port=self.inspect(names['api'])['NetworkSettings']['Ports']['8000/tcp'][0]['HostPort']
        self.report['api_port']=int(port)
        tokens=[]; account_ids=[]
        with httpx.Client(base_url='http://127.0.0.1:'+port,trust_env=False,timeout=15) as api, \
             httpx.Client(base_url='http://127.0.0.1:54321',trust_env=False,timeout=10) as auth:
            def healthy():
                try: return api.get('/health').status_code==200
                except httpx.TransportError: return False
            self.wait(healthy, 'full real API lifespan and HTTP health')
            ready=api.get('/ready'); self.check(ready.status_code==200 and ready.json()['database']=='connected' and ready.json()['redis']=='connected','real DB and Redis readiness')
            # Builds/startup may take minutes. Recheck independently immediately
            # before releasing the first Auth/database write, not just before build.
            target,manifest,_credentials=self.provenance(True)
            validate_intent(self.intent,target,manifest)
            public={'apikey':setup['keys']['anon']}
            for email in plan['emails'][:2]:
                password=secrets.token_urlsafe(40)
                signup=auth.post('/auth/v1/signup',headers=public,json={'email':email,'password':password,'data':{'vq_gate_run':plan['nonce']}})
                self.check(signup.status_code==200, 'actual disposable Auth signup')
                login=auth.post('/auth/v1/token?grant_type=password',headers=public,json={'email':email,'password':password})
                self.check(login.status_code==200, 'actual Supabase sign in')
                tokens.append(login.json()['access_token']); account_ids.append(login.json()['user']['id'])
                password=None
            self.report['fixture_setup']=self.probe({**operator,'mode':'grant'})
            def request(method,path,case,index=0,body=None,expected=200):
                response=api.request(method,path,headers={'authorization':'Bearer '+tokens[index]},json=body)
                data=response.json()
                self.report['http'].append({'case':case,'status':response.status_code,
                    'verdict':data.get('status'),'error':data.get('error',{}).get('code')})
                self.check(response.status_code==expected,'HTTP '+case)
                return data
            challenge_ids=[]
            for i in range(2):
                body={'slug':plan['slugs'][i],'title':'Permission gate fixture',
                      'description':'Disposable delivery-only fixture; NOT natively validated.',
                      'official_solution':'module fixture; endmodule',
                      'hidden_testbench':'' if i==0 else 'module fixture_tb; endmodule',
                      'execution_profile':{} if i==0 else {'timeout_ms':0}}
                data=request('POST','/api/v1/admin/challenges','create fixture '+str(i),1,body,201)
                challenge_ids.append(str(UUID(data['challenge_id'])))
            self.report['fixture_setup'].update(self.probe({**operator,'mode':'publish_fixture'}))
            body={'challenge_id':challenge_ids[0],'submitted_code':'module fixture; endmodule','idempotency_key':self.intent['idempotency_keys'][0]}
            submitted=request('POST','/api/v1/submissions','publish submission',body=body,expected=201)
            sid=str(UUID(submitted['submission_id']))
            self.check(submitted['status']=='queued','publication has no fabricated verdict')
            record=self.message('execute_hdl_submission',[sid]);record['submission_id']=sid
            self.service('worker',{'DATABASE_URL':helpers.dsn('vq_worker',credentials['worker_password']),
                                 'REDIS_URL':broker,'WORKER_CONCURRENCY':'1'})
            self.receipt(record)
            def final_result(sid):
                response=api.get('/api/v1/submissions/'+sid,headers={'authorization':'Bearer '+tokens[0]})
                return response.status_code==200 and response.json()['status']=='evaluator_not_configured'
            self.wait(lambda:final_result(sid),'exact row finalized by real worker')
            result=request('GET','/api/v1/submissions/'+sid,'owner durable result')
            self.check(result['error_code']=='MISSING_EVALUATOR' and result['xp_awarded']==0 and result['completed_at'] is not None,'truthful unscored evaluator failure')
            request('GET','/api/v1/submissions/'+sid,'nonowner polling denied',1,expected=404)
            self.wait(self.empty_queue,'first delivery acknowledged and queue drained')
            self.call(['pause',names['worker']])
            duplicate=request('POST','/api/v1/submissions','idempotent repeat',body=body,expected=201)
            self.check(duplicate['submission_id']==sid and duplicate['status']=='evaluator_not_configured' and self.empty_queue(),'repeat returns same row and does not republish')
            validation=request('POST','/api/v1/admin/challenges/'+challenge_ids[1]+'/validate','publish validation',1,expected=202)
            record=self.message('validate_challenge_task',[challenge_ids[1],account_ids[1]])
            self.check(record['task_id']==validation['task_id'],'validation response has actual wire task ID')
            self.call(['unpause',names['worker']]);self.receipt(record)
            def validation_final():
                data=api.get('/api/v1/admin/challenges/'+challenge_ids[1],headers={'authorization':'Bearer '+tokens[1]})
                return data.status_code==200 and data.json()['validation_status']=='validation_failed'
            self.wait(validation_final,'real validation task finalized failure')
            details=request('GET','/api/v1/admin/challenges/'+challenge_ids[1],'durable admin failure',1)
            self.check(details['validation_status']=='validation_failed' and not details['is_published'] and details['validated_at'] is None,'admin failure is not published or validated')
            self.wait(self.empty_queue,'validation acknowledged and queue drained')
            self.call(['pause',names['worker']]);self.call(['stop','--time','10',names['redis']])
            outage_body={**body,'idempotency_key':self.intent['idempotency_keys'][1]}
            started=time.monotonic()
            failure=request('POST','/api/v1/submissions','real unavailable broker',body=outage_body,expected=503)
            self.report['outage_elapsed_ms']=round((time.monotonic()-started)*1000,2)
            self.check(failure['error']['code']=='DISPATCH_FAILED','definite pre-send connection failure')
            match=re.search(r'submission_id=([0-9a-f-]{36})',failure['error']['message'])
            self.check(match is not None,'failure exposes safe pollable ID')
            failed_sid=str(UUID(match[1]))
            failed=request('GET','/api/v1/submissions/'+failed_sid,'persisted broker failure')
            self.check(failed['status']=='system_error' and failed['error_code']=='DISPATCH_FAILED'
                       and failed['completed_at'] is not None and failed['xp_awarded']==0,'definite nonpublication persisted truthfully')
            self.call(['start',names['redis']]);self.wait(lambda:self.redis('PING')=='PONG','temporary broker restored')
            self.check(self.empty_queue(),'failed publication left no message')
            recovered=request('POST','/api/v1/submissions','publish after broker restoration',body={**body,'idempotency_key':self.intent['idempotency_keys'][2]},expected=201)
            restored_sid=str(UUID(recovered['submission_id']))
            record=self.message('execute_hdl_submission',[restored_sid]);record['submission_id']=restored_sid
            self.call(['unpause',names['worker']]);self.receipt(record)
            self.wait(lambda:final_result(restored_sid),'subsequent real delivery finalized')
            result=request('GET','/api/v1/submissions/'+restored_sid,'durable result after restoration')
            self.check(result['error_code']=='MISSING_EVALUATOR' and result['xp_awarded']==0,'restoration did not fabricate grading success')
            self.wait(self.empty_queue,'all deliveries acknowledged and drained')
            state=self.probe({**operator,'mode':'state'})
            self.report['persisted_state']=state
            self.check(len(state['submissions'])==3 and state['no_awards'],'exact three rows and no XP or completion')
            self.check(sum(r['started'] and r['worker'] for r in state['submissions'])==2,'only delivered submissions have worker process evidence')
            self.check(any(a['details']=={'result':'execution_error','status':'validation_failed'} for a in state['audits']),'trusted persisted admin failure audit')
            network=self.inspect(names['network'],'network')
            expected={names[k] for k in ('api','worker','redis')}
            self.check({obj['Name'] for obj in network['Containers'].values()}==expected,'only task-created services in test network')
            self.report['network_membership_verified']=True
            # Record counts rather than raw Celery logs/arguments/account identity.
            proc=self.call(['logs',names['worker']])
            logs=proc.stdout+proc.stderr
            for task in self.report['tasks']:
                task['receipt_count']=logs.count((task['task']+'['+task['task_id']+'] received').encode())
                self.check(task['receipt_count']==1,'one observed receipt per task in this controlled run')
        tokens.clear();account_ids.clear();setup=None

    def cleanup(self):
        names=self.intent['names']; cleanup={'services':{},'queue_state':'unknown'}
        # Quiesce publishers FIRST; warm-stop worker only after broker acknowledgements.
        for key in ('api','worker'):
            obj=self.inspect(names[key])
            if obj:
                self.check(self.owned(obj),'exact owned service before shutdown')
                if obj['State'].get('Paused'): self.call(['unpause',names[key]])
                if obj['State']['Running']: self.call(['stop','--time','30',names[key]])
                stopped=self.inspect(names[key])
                self.check(not stopped['State']['Running'],'service actually stopped')
                cleanup['services'][key]={'stopped':True,'exit_code':stopped['State']['ExitCode']}
        redis=self.inspect(names['redis'])
        if redis and redis['State']['Running']:
            cleanup['queue_state']='drained' if self.empty_queue() else 'pending'
        # No live publishers/workers left. Remove the owned broker, including any
        # uncertain pending message, BEFORE deleting its exact fixture resources.
        for key in ('api','worker','redis','probe'):
            obj=self.inspect(names[key])
            if obj:
                self.check(self.owned(obj),'exact owned container before removal')
                self.call(['rm','-f',names[key]])
            self.check(self.inspect(names[key]) is None,'exact container absent')
        for name in self.intent['checks'].values():
            obj=self.inspect(name)
            if obj:
                self.check(self.owned(obj),'exact owned regression container')
                self.call(['rm','-f',name])
            self.check(self.inspect(name) is None,'exact regression container absent')
        for child in self.attachments:
            child.wait(timeout=10)
        if hasattr(self,'operator'):
            cleanup['fixtures']=self.probe({**self.operator,'mode':'cleanup','service_key':self.service_key})
        self.report['cleanup']=cleanup
        final=self.inventory()
        self.check(all(v==0 for k,v in final.items() if k!='auth_audit'),'independent final zero application and Auth counts')
        self.check(gate.preflight(self.docker,gate.load_plan())['state']=='complete','schema ledger and roles retained')
        gate.psql(self.docker,'BEGIN TRANSACTION READ ONLY;'+gate.assertions_sql()+'ROLLBACK;')
        cleanup['independent_final_counts']=final
        network=self.inspect(names['network'],'network')
        if network:
            self.check(network['Labels'].get(LABEL)==self.intent['resources']['nonce'] and not network['Containers'],'owned empty network')
            self.call(['network','rm',names['network']])
        self.check(self.inspect(names['network'],'network') is None,'exact network absent')
        for tag in self.intent['tags'].values():
            if self.inspect(tag,'image'):self.call(['image','rm',tag])
            self.check(self.inspect(tag,'image') is None,'temporary image tag absent')
        cleanup['completed']=True

    def execute(self, recover=None):
        target,manifest,credentials=self.provenance(not recover)
        if recover:
            path=Path(recover).resolve()
            self.check(path.parent==self.directory and re.fullmatch(r'delivery-intent-[0-9a-f]{32}\.dpapi',path.name),'exact recovery journal path')
            self.intent=private.read_sealed(path)
            validate_intent(self.intent,target,manifest)
            self.report['private_journal']=str(path)
        else:self.new_intent(target,manifest)
        names=self.intent['names']
        # Build the actual current Dockerfiles, not substitute application images.
        try:
            self.call(['build','--quiet','-t',self.intent['tags']['api'],'backend'],timeout=600)
            if not recover:
                self.call(['build','--quiet','-f','worker/Dockerfile','-t',self.intent['tags']['worker'],'.'],timeout=600)
                self.packaged_checks()
                self.call(['pull','redis:7-alpine'],timeout=180)
            if self.inspect(names['network'],'network') is None:
                self.call(['network','create','--label',LABEL+'='+self.intent['resources']['nonce'],names['network']])
            if recover:
                spec=importlib.util.spec_from_file_location('permission_live',ROOT/'tests/database_permission_live.py')
                helpers=importlib.util.module_from_spec(spec);spec.loader.exec_module(helpers)
                setup=helpers.private_credentials(self.docker)
                self.operator={'operator_dsn':helpers.dsn('supabase_admin',setup['operator_password']),'plan':self.intent['resources']}
                self.service_key=setup['keys']['service_role']
            else:
                self.call(['create',*self.flags(names['redis']),'--tmpfs','/data:rw,noexec,nosuid,size=16m',
                           '--user','65534:65534','--workdir','/tmp',
                           'redis:7-alpine','redis-server','--save','','--appendonly','no'])
                self.isolation(names['redis'])
                self.call(['start',names['redis']])
                self.wait(lambda:self.redis('PING')=='PONG','isolated real Redis ready')
                info=self.redis('INFO','server')
                self.report['redis_version']=re.search(r'redis_version:([^\r\n]+)',info)[1]
                self.run_live(credentials)
                self.report['passed']=True
        except Exception as exc:
            self.report['passed']=False
            self.report['failure_type']=type(exc).__name__
            self.report['blocker']=str(exc) if isinstance(exc,gate.GateError) else 'Private diagnostics withheld'
        finally:
            try:self.cleanup()
            except Exception as exc:
                self.report['passed']=False
                self.report['cleanup_failure_type']=type(exc).__name__
                self.report['cleanup_blocker']=str(exc) if isinstance(exc,gate.GateError) else 'Private diagnostics withheld'
            private.sealed_write(self.directory/('delivery-receipt-'+uuid4().hex+'.dpapi'),self.report)
        return self.report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--docker',required=True)
    parser.add_argument('--private-directory',required=True)
    parser.add_argument('--authorize-local-delivery-test',action='store_true')
    parser.add_argument('--recover-journal')
    args=parser.parse_args()
    if not args.authorize_local_delivery_test:
        print('Refused: explicit local delivery-test authorization required',file=sys.stderr)
        return 2
    try:
        directory=private.checked_directory(args.private_directory)
        result=DeliveryGate(args.docker,directory).execute(args.recover_journal)
        # Full nonsecret command ledger is retained in the encrypted receipt.
        # Keep the console summary useful and bounded.
        public={key:value for key,value in result.items() if key!='commands'}
        public['command_count']=len(result['commands'])
        print(json.dumps(public,indent=2))
        return 0 if result.get('passed',bool(args.recover_journal)) and not result.get('cleanup_failure_type') else 1
    except Exception as exc:
        print(json.dumps({'failed':True,'failure_type':type(exc).__name__,
            'blocker':str(exc) if isinstance(exc,gate.GateError) else 'Private diagnostics withheld'}))
        return 1


if __name__=='__main__': sys.exit(main())
