"""Opt-in real queued native gate; credentials/intents/receipts private DPAPI.

Actual packaged commands and dependencies. No grading retry or accounting change.
Profiling observations are paired with an independent Docker daemon event stream.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import secrets
import subprocess
import sys
import threading
import time
from uuid import UUID, uuid4
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.redis_celery_delivery import DeliveryGate, LABEL, ISSUER, LAUNCH, CHECKS,decode_message
from tools import database_gate as gate, database_live_gate as private, database_live_resources as resources


def validate_intent(intent,target,manifest):
    resources.validate_plan(intent['resources'],target,manifest)
    n=intent['resources']['nonce']
    if (intent.get('format')!=1 or type(intent.get('reward')) is not int or intent.get('reward')!=1
        or intent['names']!={k:'vq-queued-native-'+k+'-'+n for k in ('api','worker','redis','probe','network','workspace')}
        or intent['tags']!={k:'vq-queued-native-'+k+':'+n for k in ('api','worker','redis','executor')}
        or intent['checks']!={k:'vq-queued-native-'+k+'-'+n for k in CHECKS+('workspace',)}
        or intent['keys']!=['queued-native-'+n+'-'+str(i) for i in range(6)]
        or type(intent.get('redis_base_present')) is not bool):
        raise gate.GateError('Invalid exact queued-native intent')


def observations(logs):
    result=[]
    for line in logs.decode(errors='replace').splitlines():
        m=re.search(r'VQ_NATIVE_(CREATE|RESULT|ACCOUNTING_ERROR|ACCOUNTING) (\{.*)',line)
        if m:
            data,_=json.JSONDecoder().raw_decode(m[2]);result.append({'kind':m[1],**data})
    return result


def worker_capabilities_valid(host):
    added=host.get('CapAdd')
    return isinstance(added,list) and all(isinstance(c,str) for c in added) and {
        c.removeprefix('CAP_') for c in added}=={'CHOWN','FOWNER','DAC_OVERRIDE'} and host.get('CapDrop')==['ALL']


def monitored_publication(line):
    """Decode Redis MONITOR quoting, retaining only this isolated canonical queue.

    The returned wire envelope stays in bounded private memory and is checked by
    the existing actual Kombu parser. Never print/store the whole monitor stream.
    """
    quoted=re.findall(r'"(?:\\.|[^"\\])*"',line)
    if not quoted or json.loads(quoted[0]).upper()!='LPUSH':return None
    if len(quoted)<2 or json.loads(quoted[1])!='hdl_execution':return None
    if len(quoted)!=3:raise gate.GateError('Malformed canonical Redis publication')
    return json.loads(quoted[2])


class QueuedGate(DeliveryGate):
    def __init__(self,docker,directory):
        super().__init__(docker,directory)
        self.events=[];self.events_overflow=False;self.event_process=None;self.event_thread=None
        self.publications=[];self.monitor_process=None;self.monitor_thread=None;self.monitor_overflow=False

    def inspect(self,name,kind='container'):
        p=self.call([kind,'inspect',name],allow_failure=True)
        if p.returncode==0:return json.loads(p.stdout)[0]
        text=p.stderr.decode(errors='replace')
        if name in text and re.search(r'No such (?:object|container|image|volume|network)|(?:network|volume).*not found',text,re.I):return None
        raise gate.GateError('Docker inspection unavailable; absence is unverified')

    def new_intent(self,target,manifest):
        plan=resources.new_plan(target,manifest);n=plan['nonce']
        intent={'format':1,'reward':1,'resources':plan,
            'names':{k:'vq-queued-native-'+k+'-'+n for k in ('api','worker','redis','probe','network','workspace')},
            'tags':{k:'vq-queued-native-'+k+':'+n for k in ('api','worker','redis','executor')},
            'checks':{k:'vq-queued-native-'+k+'-'+n for k in CHECKS+('workspace',)},
            'keys':['queued-native-'+n+'-'+str(i) for i in range(6)],
            'redis_base_present':self.inspect('redis:7-alpine','image') is not None}
        validate_intent(intent,target,manifest)
        path=self.directory/('queued-native-intent-'+uuid4().hex+'.dpapi')
        private.sealed_write(path,intent)
        validate_intent(private.read_sealed(path),target,manifest)
        self.intent=intent;self.report['private_journal']=str(path)

    def probe(self,capsule):
        name=self.intent['names']['probe'];self.check(self.inspect(name) is None,'probe name unused')
        self.call(['create','-i',*self.flags(name),
            '--mount','type=bind,source='+str(ROOT/'tools')+',target=/gate/tools,readonly',
            '--mount','type=bind,source='+str(ROOT/'tests/queued_native_probe.py')+',target=/gate/probe.py,readonly',
            self.intent['tags']['api'],'python','-B','/gate/probe.py'])
        try:
            self.isolation(name,probe=True)
            p=self.call(['start','-a','-i',name],json.dumps(capsule).encode(),timeout=60,allow_failure=True)
            result=json.loads(p.stdout)
            if p.returncode or result.get('failed'):
                self.report['probe_failure']={'mode':capsule['mode'],**result}
                raise gate.GateError('Private probe failed: '+capsule['mode']+' '+result.get('failure_type','unknown'))
            return result
        finally:
            obj=self.inspect(name)
            if obj and self.owned(obj):self.call(['rm','-f',name])

    def service(self,role,environment):
        if role!='worker':return super().service(role,environment)
        name=self.intent['names']['worker'];tag=self.intent['tags']['worker']
        command=self.inspect(tag,'image')['Config']['Cmd']
        self.call(['create','-i',*self.flags(name),'--cap-add','CHOWN','--cap-add','FOWNER','--cap-add','DAC_OVERRIDE',
            '--mount','type=bind,source=/var/run/docker.sock,target=/var/run/docker.sock',
            '--mount','type=volume,source='+self.intent['names']['workspace']+',target=/var/lib/veriquest/workspaces',
            '--mount','type=bind,source='+str(ROOT/'tests/queued_native_observer.py')+',target=/gate/sitecustomize.py,readonly',
            '--entrypoint','python',tag,'-B','-c',LAUNCH])
        obj=self.inspect(name);h=obj['HostConfig'];mounts=obj['Mounts']
        self.check(self.owned(obj) and h['ReadonlyRootfs'] and not h['Privileged'] and h['CapDrop']==['ALL']
            and worker_capabilities_valid(h) and 'no-new-privileges:true' in h['SecurityOpt']
            and h['Memory']==536870912 and h['PidsLimit']==64 and not h.get('PortBindings'),'actual worker isolation/limits')
        self.check(len(mounts)==3 and any(m['Destination']=='/var/lib/veriquest/workspaces' and m['Type']=='volume'
            and m['Name']==self.intent['names']['workspace'] and m['RW'] for m in mounts)
            and any(m['Destination']=='/var/run/docker.sock' and m['Type']=='bind' for m in mounts)
            and any(m['Destination']=='/gate/sitecustomize.py' and not m['RW'] for m in mounts),'exact worker workspace/socket/observer')
        self.check(set(obj['NetworkSettings']['Networks'])=={self.intent['names']['network']}
            and not any(e.startswith(('DATABASE_URL=','API_DATABASE_URL=','WORKER_DATABASE_URL=')) for e in obj['Config']['Env']), 'network and private runtime credential boundary')
        self.report['worker_boundary']={'memory':h['Memory'],'pids':64,'concurrency':1,'socket_privileged_authority':True}
        p=subprocess.Popen([self.docker,'start','-a','-i',name],stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        self.attachments.append(p)
        env={**environment,'PYTHONPATH':'/gate:/app','PYTHONDONTWRITEBYTECODE':'1'}
        p.stdin.write(json.dumps({'environment':env,'command':command}).encode()+b'\n');p.stdin.flush();p.stdin.close()

    def workspace_probe(self,recover=False):
        name=self.intent['checks']['workspace']
        self.check(self.inspect(name) is None,'workspace check name unused')
        args=['run','--rm','--name',name,'--label',LABEL+'='+self.intent['resources']['nonce'],
            '--network','none','--read-only','--cap-drop','ALL','--cap-add','CHOWN','--cap-add','FOWNER','--cap-add','DAC_OVERRIDE',
            '--security-opt','no-new-privileges:true','--memory','128m','--pids-limit','32','--tmpfs','/tmp:rw,noexec,nosuid,size=16m',
            '--mount','type=bind,source=/var/run/docker.sock,target=/var/run/docker.sock',
            '--mount','type=volume,source='+self.intent['names']['workspace']+',target=/var/lib/veriquest/workspaces',
            '--mount','type=bind,source='+str(ROOT/'tests/queued_native_observer.py')+',target=/gate/observer.py,readonly',
            '-e','VQ_WORKSPACE_VOLUME='+self.intent['names']['workspace'],self.intent['tags']['worker'],'python','-B','/gate/observer.py']
        if recover:args.append('--recover')
        result=json.loads(self.call(args,timeout=60).stdout)
        self.check(result.get('bounded_bytes')==134217728 and result.get('records')==result.get('leftovers')==0,'actual bounded workspace and exact cleanup')
        return result

    def start_events(self):
        args=['events','--since',str(int(time.time())),'--filter','type=container',
            '--filter','label=veriquest.sandbox.volume='+self.intent['names']['workspace'],'--format','{{json .}}']
        self.event_process=subprocess.Popen([self.docker,*args],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True)
        def collect():
            for line in self.event_process.stdout:
                try:
                    e=json.loads(line);a=e['Actor'];labels=a['Attributes'];job=labels.get('veriquest.sandbox.job')
                    if labels.get('veriquest.sandbox.volume')!=self.intent['names']['workspace'] or not isinstance(job,str) or not re.fullmatch('[a-f0-9]{32}',job):continue
                    if len(self.events)>=256:self.events_overflow=True;continue
                    self.events.append({'job':job,'container_id':a['ID'],'action':e['Action'],'time_nano':e.get('timeNano'),
                        'exit_code':labels.get('exitCode') if e['Action']=='die' else None})
                except (KeyError,TypeError,ValueError):self.events_overflow=True
        self.event_thread=threading.Thread(target=collect,daemon=True);self.event_thread.start()
        self.report['daemon_event_command']=args

    def start_broker_monitor(self):
        ready=threading.Event()
        args=['exec',self.intent['names']['redis'],'redis-cli','--raw','MONITOR']
        self.monitor_process=subprocess.Popen([self.docker,*args],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True)
        def collect():
            for line in self.monitor_process.stdout:
                if line.strip()=='OK':ready.set();continue
                try:
                    raw=monitored_publication(line)
                    if raw is not None:
                        if len(self.publications)>=16 or len(raw.encode())>65536:self.monitor_overflow=True
                        else:self.publications.append(raw)
                except (ValueError,TypeError):self.monitor_overflow=True
        self.monitor_thread=threading.Thread(target=collect,daemon=True);self.monitor_thread.start()
        self.check(ready.wait(5),'actual Redis MONITOR subscription acknowledged before publication')
        self.report['broker_observer']={'command':args,'ready':True,'max_messages':16,'max_envelope_bytes':65536}

    def message(self,task,args):
        expected=len(self.report['tasks'])+1
        self.wait(lambda:len(self.publications)>=expected,'real LPUSH observed',timeout=5)
        self.check(len(self.publications)==expected and not self.monitor_overflow,'exact single canonical publication observed')
        record=decode_message(self.publications[-1],task,args)
        self.report['tasks'].append(record)
        return record

    def stop_events(self):
        if self.monitor_process:
            self.monitor_process.terminate()
            try:self.monitor_process.wait(timeout=5)
            except subprocess.TimeoutExpired:self.monitor_process.kill();self.monitor_process.wait(timeout=5)
            self.monitor_thread.join(timeout=2);self.monitor_process.stdout.close();self.monitor_process=None
        self.report['observed_publication_count']=len(self.publications);self.report['broker_observer_overflow']=self.monitor_overflow
        if self.event_process:
            self.event_process.terminate()
            try:self.event_process.wait(timeout=5)
            except subprocess.TimeoutExpired:self.event_process.kill();self.event_process.wait(timeout=5)
            self.event_thread.join(timeout=2);self.event_process.stdout.close();self.event_process=None
        self.report['daemon_events']=list(self.events);self.report['event_overflow']=self.events_overflow

    def task_done(self,record):
        p=self.call(['logs',self.intent['names']['worker']]);text=p.stdout+p.stderr
        return (record['task']+'['+record['task_id']+'] succeeded').encode() in text

    def native_evidence(self,record):
        p=self.call(['logs',self.intent['names']['worker']])
        entries=[r for r in observations(p.stdout+p.stderr) if r['task_id']==record['task_id']]
        self.report.setdefault('native_observations',[]).extend(entries)
        created=[r for r in entries if r['kind']=='CREATE'];results=[r for r in entries if r['kind']=='RESULT']
        self.check(len(created)==len(results)==1,'one actual native invocation observed')
        c=created[0];r=results[0]
        self.check(c['job']==r['job'] and c['submission_id']==r['submission_id']==record['submission_id'],'task/submission/executor correlation')
        self.check(c['user']=='1000:1000' and c['network']=='none' and c['readonly'] and not c['privileged']
            and c['caps']==['ALL'] and not c['cap_add'] and not c['binds'] and not c['ports']
            and c['log']=='none' and 'no-new-privileges:true' in c['security'],'actual executor no socket/isolation')
        self.check(c['memory']==c['swap']==67108864 and c['cpu']==250000000 and c['pids']==64
            and c['tmpfs']['/tmp']=='rw,noexec,nosuid,nodev,size=64m,mode=1777'
            and any(u['Name']=='fsize' and u['Hard']==u['Soft']==67108864 for u in c['ulimits']),'actual executor budgets')
        mounts=c['mounts'];self.check(len(mounts)==2,'only two executor mounts')
        for suffix,ro in [('input',True),('output',False)]:
            m=next(m for m in mounts if m['Target']=='/workspace/'+suffix)
            self.check(m['Type']=='volume' and m['Source']==self.intent['names']['workspace']
                and m['VolumeOptions']['Subpath']==c['job']+'/'+suffix and m.get('ReadOnly',False)==ro,'actual exact volume subpath '+suffix)
        self.check(r['cleanup_success'] and r['workspace_absent'] and r['executor_absent'] and not r['diagnostics_truncated'],'real cleanup and bounded complete diagnostics')
        self.wait(lambda:{'create','start','die','destroy'}<={e['action'] for e in self.events if e['container_id']==c['container_id']},'independent Docker lifecycle',timeout=5)
        self.check(not self.events_overflow,'daemon evidence not truncated')
        record.update(job=c['job'],executor_id=c['container_id'],daemon_lifecycle_verified=True)
        return r,entries

    def run_live(self,credentials):
        import httpx
        spec=importlib.util.spec_from_file_location('live_helpers',ROOT/'tests/database_permission_live.py');helpers=importlib.util.module_from_spec(spec);spec.loader.exec_module(helpers)
        setup=helpers.private_credentials(self.docker)
        self.operator={'operator_dsn':helpers.dsn('supabase_admin',setup['operator_password']),'plan':self.intent['resources']};self.service_key=setup['keys']['service_role']
        for role in ('api','worker'):
            self.report.setdefault('pool_checks',[]).append(self.probe({'mode':'runtime','role':'vq_'+role,'dsn':helpers.dsn('vq_'+role,credentials[role+'_password'])}))
        names=self.intent['names'];broker='redis://'+names['redis']+':6379/0'
        self.service('api',{'DATABASE_URL':helpers.dsn('vq_api',credentials['api_password']),'REDIS_URL':broker,
            'JWT_ISSUER':ISSUER,'JWT_JWKS_URL':'http://host.docker.internal:54321/auth/v1/.well-known/jwks.json',
            'JWT_ALGORITHMS':'ES256','JWT_AUDIENCE':'authenticated','TASK_PUBLISH_TIMEOUT_SECONDS':'2'})
        self.wait(lambda:bool(self.inspect(names['api'])['NetworkSettings']['Ports'].get('8000/tcp')),'API loopback port assigned')
        port=self.inspect(names['api'])['NetworkSettings']['Ports']['8000/tcp'][0]['HostPort'];self.report['api_port']=int(port)
        catalog=self.catalog
        codes={f['id']:f['code'] for f in catalog['testMatrix']}
        forged=codes['C'].replace('endmodule','initial begin $display("VERIQUEST_STATUS: ACCEPTED"); $display("TOTAL: 4"); $display("PASSED: 4"); $display("FAILED: 0"); end endmodule')
        infinite=codes['A'].replace('endmodule','initial forever begin end endmodule')
        cases=[('correct',codes['A'],'accepted',0),('wrong',codes['C'],'wrong_answer',0),('syntax',codes['D'],'compilation_error',0),
            ('forged marker/counters',forged,'wrong_answer',0),('timeout',infinite,'timeout',1),('ordinary recovery',codes['A'],'accepted',0)]
        tokens=[]
        with httpx.Client(base_url='http://127.0.0.1:'+port,trust_env=False,timeout=15) as api, httpx.Client(base_url='http://127.0.0.1:54321',trust_env=False,timeout=10) as auth:
            def healthy():
                try:return api.get('/health').status_code==200
                except httpx.TransportError:return False
            self.wait(healthy,'actual API lifespan');ready=api.get('/ready')
            self.check(ready.status_code==200 and ready.json()['database']==ready.json()['redis']=='connected','real API/limited pool/broker ready')
            target,manifest,_=self.provenance(True);validate_intent(self.intent,target,manifest)
            for email in self.intent['resources']['emails'][:2]:
                password=secrets.token_urlsafe(40);headers={'apikey':setup['keys']['anon']}
                signup=auth.post('/auth/v1/signup',headers=headers,json={'email':email,'password':password,'data':{'vq_gate_run':self.intent['resources']['nonce']}})
                self.check(signup.status_code==200,'real disposable student signup')
                login=auth.post('/auth/v1/token?grant_type=password',headers=headers,json={'email':email,'password':password})
                self.check(login.status_code==200,'real Supabase signin');tokens.append(login.json()['access_token']);password=None
            fixture=self.probe({**self.operator,'mode':'setup','fixture':{'solution':codes['A'],'bench':catalog['testbenchCode']}});self.report['fixture_setup']=fixture
            self.start_broker_monitor();self.start_events();worker_started=False
            for index,(name,source,expected,challenge) in enumerate(cases):
                body={'challenge_id':fixture['challenge_ids'][challenge],'submitted_code':source,'idempotency_key':self.intent['keys'][index]}
                response=api.post('/api/v1/submissions',headers={'authorization':'Bearer '+tokens[0]},json=body);data=response.json()
                self.report['http'].append({'case':'submit '+name,'status':response.status_code,'verdict':data.get('status')})
                self.check(response.status_code==201 and data.get('status')=='queued','real HTTP publication '+name)
                sid=str(UUID(data['submission_id']));task=self.message('execute_hdl_submission',[sid]);task.update(case=name,submission_id=sid)
                if not worker_started:
                    self.service('worker',{'DATABASE_URL':helpers.dsn('vq_worker',credentials['worker_password']),'REDIS_URL':broker,
                        'WORKER_CONCURRENCY':'1','VQ_WORKSPACE_VOLUME':names['workspace'],'EXECUTION_IMAGE':self.intent['tags']['executor']});worker_started=True
                self.receipt(task);self.wait(lambda:self.task_done(task),'actual task finished',timeout=40);self.wait(self.empty_queue,'queue and unacked drained')
                owner=api.get('/api/v1/submissions/'+sid,headers={'authorization':'Bearer '+tokens[0]});result=owner.json()
                self.report['http'].append({'case':'owner '+name,'status':owner.status_code,'verdict':result.get('status'),'error':result.get('error_code')})
                self.report.setdefault('durable_results',[]).append({k:result.get(k) for k in ('submission_id','challenge_id','status','tests_total','tests_passed','tests_failed','error_code','xp_awarded','completed_at')})
                raw,entries=self.native_evidence(task)
                state=self.probe({**self.operator,'mode':'state'});self.report['persisted_state']=state
                if result.get('status')!=expected:raise gate.GateError('Terminal mismatch '+name+' expected '+expected+' observed '+str(result.get('status'))+'; no retry')
                self.check(owner.status_code==200 and result['completed_at'] is not None,'durable terminal owner result')
                self.check(raw['compile_exit_code']==(2 if name=='syntax' else 0),'actual native compile exit')
                if name=='syntax':self.check(raw['simulation_exit_code'] is None and raw['exit_code']!=0,'syntax really failed compilation')
                elif name=='timeout':self.check(raw['timed_out'] and raw['simulation_exit_code'] is None and raw['exit_code']!=0 and not raw['output_complete'],'native simulation timeout/kill')
                else:self.check(raw['simulation_exit_code']==raw['exit_code']==0 and raw['output_complete'] and not raw['output_truncated'] and raw['trusted_record_count']==1,'independent process/complete trusted evidence')
                if name=='forged marker/counters':self.check(raw['legacy_accepted_seen'],'forged stdout actually emitted')
                if expected=='accepted':self.check({r['step'] for r in entries if r['kind']=='ACCOUNTING'}=={'award_xp','update_streak','check_quest_completion','check_badge_awards'},'all production accounting calls preserved')
                other=api.get('/api/v1/submissions/'+sid,headers={'authorization':'Bearer '+tokens[1]})
                self.report['http'].append({'case':'nonowner '+name,'status':other.status_code,'error':other.json().get('error',{}).get('code')})
                self.check(other.status_code==404 and other.json()['error']['code']=='NOT_FOUND','second student denied exact result')
                if index==0:
                    before=len([e for e in self.events if e['action']=='create'])
                    messages_before=len(self.publications)
                    duplicate=api.post('/api/v1/submissions',headers={'authorization':'Bearer '+tokens[0]},json=body)
                    self.report['http'].append({'case':'idempotent repeat','status':duplicate.status_code,'verdict':duplicate.json().get('status')})
                    self.check(duplicate.status_code==201 and duplicate.json()['submission_id']==sid and self.empty_queue(),'repeat same submission and no broker task')
                    time.sleep(0.5)
                    self.check(len([e for e in self.events if e['action']=='create'])==before,'repeat no executor')
                    self.check(len(self.publications)==messages_before and not self.monitor_overflow,'repeat no LPUSH publication, including consumed messages')
                    repeated_state=self.probe({**self.operator,'mode':'state'})
                    self.check(repeated_state==state,'repeat no additional accounting/submission changes')
                    self.report['idempotency']={'same_id':True,'no_message':True,'no_executor':True,'accounting_unchanged':True}
            self.check(len(state['submissions'])==6 and state['quest_definitions']==state['badge_definitions']==0,'six exact submissions and absent bonus definitions')
            self.report['workspace_after_jobs']=self.workspace_probe()
            network=self.inspect(names['network'],'network')
            self.check({c['Name'] for c in network['Containers'].values()}=={names[k] for k in ('api','worker','redis')},'only task services in unique bridge')
            p=self.call(['logs',names['worker']]);logs=p.stdout+p.stderr
            for task in self.report['tasks']:
                task['receipt_count']=logs.count((task['task']+'['+task['task_id']+'] received').encode())
                self.check(task['receipt_count']==1,'one receipt in this bounded run')
        tokens.clear()

    def cleanup(self):
        names=self.intent['names'];self.report['native_quiescence']={}
        for role in ('api','worker'):
            obj=self.inspect(names[role])
            if obj:
                self.check(self.owned(obj),'exact service before quiescence')
                if obj['State'].get('Paused'):self.call(['unpause',names[role]])
                if obj['State']['Running']:self.call(['stop','--time','30',names[role]])
                stopped=self.inspect(names[role]);self.check(not stopped['State']['Running'],'publisher/worker actually stopped')
                self.report['native_quiescence'][role]={'stopped':True,'exit_code':stopped['State']['ExitCode']}
        redis=self.inspect(names['redis'])
        if redis and redis['State']['Running']:
            self.report['quiesced_queue']={'queued':int(self.redis('LLEN','hdl_execution')),'unacked':int(self.redis('HLEN','unacked'))}
        volume=self.inspect(names['workspace'],'volume')
        if volume:
            self.check(volume.get('Labels',{}).get(LABEL)==self.intent['resources']['nonce'],'exact owned workspace label')
            self.report['workspace_cleanup']=self.workspace_probe(recover=True)
            self.check(not self.call(['ps','-a','--filter','volume='+names['workspace'],'--format','{{.ID}}']).stdout.strip() or
                all(not self.inspect(names[role])['State']['Running'] for role in ('worker',) if self.inspect(names[role])), 'no active workspace user after quiescence')
            # Remove stopped worker before unmounting the tmpfs. Other executor
            # references must be absent; do not force-delete a mounted volume.
            worker=self.inspect(names['worker'])
            if worker:
                self.check(self.owned(worker),'owned stopped worker');self.call(['rm',names['worker']])
            self.check(not self.call(['ps','-a','--filter','volume='+names['workspace'],'--format','{{.ID}}']).stdout.strip(),'no remaining volume references')
            self.call(['volume','rm',names['workspace']]);self.check(self.inspect(names['workspace'],'volume') is None,'exact workspace absent')
        self.stop_events()
        super().cleanup()
        if not self.intent['redis_base_present'] and self.inspect('redis:7-alpine','image'):
            self.check(not self.call(['ps','-a','--filter','ancestor=redis:7-alpine','--format','{{.ID}}']).stdout.strip(),'task-pulled Redis tag unused')
            self.call(['image','rm','redis:7-alpine'])

    def execute(self,recover=None):
        self.check(self.call(['context','show']).stdout.strip()==b'desktop-linux' and self.call(['info','--format','{{.OSType}}']).stdout.strip()==b'linux','intended Docker Linux engine')
        target,manifest,credentials=self.provenance(not recover)
        if recover:
            p=Path(recover).resolve();self.check(p.parent==self.directory and re.fullmatch('queued-native-intent-[0-9a-f]{32}\\.dpapi',p.name),'exact recovery journal path')
            self.intent=private.read_sealed(p);validate_intent(self.intent,target,manifest);self.report['private_journal']=str(p)
        else:self.new_intent(target,manifest)
        try:
            self.call(['build','--quiet','-t',self.intent['tags']['api'],'backend'],timeout=600)
            self.call(['build','--quiet','-f','worker/Dockerfile','-t',self.intent['tags']['worker'],'.'],timeout=600)
            if not recover:
                self.call(['build','--quiet','-t',self.intent['tags']['executor'],'execution'],timeout=600)
                self.packaged_checks()
                runner=self.call(['run','--rm','--network','none',self.intent['tags']['executor'],'sha256sum','/usr/local/bin/vq-run'])
                self.check(runner.stdout.decode().split()[0]==gate.checksum(ROOT/'execution/run.sh'),'actual packaged trusted runner hash')
                self.report['executor_image']=self.inspect(self.intent['tags']['executor'],'image')['Id']
                exported=subprocess.run(['node','--experimental-strip-types','--input-type=module','-e',
                    "import {TESTBENCH_CATALOG as c} from './src/evaluator/testbenchCatalog.ts'; console.log(JSON.stringify(c['and-gate-demo']));"],capture_output=True,cwd=ROOT,timeout=30)
                self.check(exported.returncode==0,'actual current catalog export');self.catalog=json.loads(exported.stdout)
                self.call(['pull','redis:7-alpine'],timeout=180);self.call(['tag','redis:7-alpine',self.intent['tags']['redis']])
            names=self.intent['names']
            if self.inspect(names['network'],'network') is None:self.call(['network','create','--label',LABEL+'='+self.intent['resources']['nonce'],names['network']])
            if recover:
                spec=importlib.util.spec_from_file_location('helpers',ROOT/'tests/database_permission_live.py');helpers=importlib.util.module_from_spec(spec);spec.loader.exec_module(helpers)
                setup=helpers.private_credentials(self.docker);self.operator={'operator_dsn':helpers.dsn('supabase_admin',setup['operator_password']),'plan':self.intent['resources']};self.service_key=setup['keys']['service_role']
            else:
                self.call(['volume','create','--label',LABEL+'='+self.intent['resources']['nonce'],'--opt','type=tmpfs','--opt','device=tmpfs','--opt','o=size=134217728,mode=0700',names['workspace']])
                self.call(['create',*self.flags(names['redis']),'--tmpfs','/data:rw,noexec,nosuid,size=16m','--user','65534:65534','--workdir','/tmp',
                    self.intent['tags']['redis'],'redis-server','--save','','--appendonly','no'])
                self.isolation(names['redis']);self.call(['start',names['redis']]);self.wait(lambda:self.redis('PING')=='PONG','actual isolated Redis ready')
                self.report['redis_version']=re.search(r'redis_version:([^\r\n]+)',self.redis('INFO','server'))[1]
                self.run_live(credentials);self.report['passed']=True
        except Exception as e:
            self.report.update(passed=False,failure_type=type(e).__name__,blocker=str(e) if isinstance(e,gate.GateError) else 'Private diagnostics withheld')
        finally:
            try:self.cleanup()
            except Exception as e:
                self.report.update(passed=False,cleanup_failure_type=type(e).__name__,cleanup_blocker=str(e) if isinstance(e,gate.GateError) else 'Private diagnostics withheld');self.stop_events()
            receipt=self.directory/('queued-native-receipt-'+uuid4().hex+'.dpapi');private.sealed_write(receipt,self.report);self.report['private_receipt']=str(receipt)
        return self.report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--docker',required=True);p.add_argument('--private-directory',required=True)
    p.add_argument('--authorize-local-queued-native',action='store_true');p.add_argument('--recover-journal');args=p.parse_args()
    if not args.authorize_local_queued_native:p.error('Explicit local queued-native authorization required')
    try:
        result=QueuedGate(args.docker,private.checked_directory(args.private_directory)).execute(args.recover_journal)
        public={k:v for k,v in result.items() if k not in ('commands','native_observations','daemon_events')}
        public['command_count']=len(result['commands']);public['native_observations']=len(result.get('native_observations',[]));public['daemon_event_count']=len(result.get('daemon_events',[]))
        print(json.dumps(public,indent=2));return 0 if result.get('passed',bool(args.recover_journal)) and not result.get('cleanup_failure_type') else 1
    except Exception as e:
        print(json.dumps({'failed':True,'failure_type':type(e).__name__,'blocker':str(e) if isinstance(e,gate.GateError) else 'Private diagnostics withheld'}));return 1


if __name__=='__main__':sys.exit(main())
