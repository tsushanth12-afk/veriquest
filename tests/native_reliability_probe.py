"""Fixed real-Docker matrix; no database/queue. Stress commands are TRUSTED fixtures."""
import concurrent.futures
import json
import os
from pathlib import Path
import sys
import time
from unittest.mock import patch
sys.path.insert(0, '/app')
sys.path.insert(0, '/app/tests')
import docker
from docker.models.containers import ContainerCollection
import native_sandbox_probe as helpers
from worker.execution.sandbox import DockerSandbox
from worker.execution.evaluator import parse_evaluation_result
from worker.execution.workspace import Workspace, ROOT, WORKSPACE_BYTES


def evaluate(config, fixture_id, name, stress=None):
    fixture = next(item for item in config['testMatrix'] if item['id'] == fixture_id)
    profile = dict(memory_mb=64, cpu_limit='0.25', timeout_ms=5000)
    if stress == 'memory':
        profile.update(memory_mb=32, timeout_ms=2000)
    if stress == 'pids':
        profile.update(pids_limit=16, timeout_ms=2000)
    if stress in ('file', 'workspace'):
        profile.update(memory_mb=256, timeout_ms=3000)
    sandbox = DockerSandbox(**profile)
    original = ContainerCollection.create
    inspections = []
    def create(collection, *args, **kwargs):
        # Production configuration/transport unchanged. Only the fixed, trusted
        # post-grading stress command is substituted; never student shell input.
        commands = {
            'memory': 'head -c 67108864 /dev/zero | tail -c 67108864 > /dev/null',
            'pids': '(i=0; while [ "$i" -lt 64 ]; do sleep 5 & i=$((i+1)); done; wait)',
            'file': 'dd if=/dev/zero of=/workspace/output/stress.one bs=1048576 count=80',
            'workspace': 'for i in 1 2 3; do dd if=/dev/zero of=/workspace/output/stress.$i bs=1048576 count=48 || break; done',
        }
        if stress:
            command = '/usr/local/bin/vq-run; initial=$?; [ "$initial" -eq 0 ] || exit "$initial"; ' + commands[stress]
            command += '; code=$?; while read -r key value; do [ "$key" != max ] || printf "%s" "$value" > /workspace/output/pids.events; done < /sys/fs/cgroup/pids.events; exit "$code"'
            command = command.removesuffix('; exit "$code"') + '; while read -r key value; do [ "$key" != oom_kill ] || printf "%s" "$value" > /workspace/output/memory.events; done < /sys/fs/cgroup/memory.events; exit "$code"'
            kwargs['command'] = ['sh', '-c', command]
        container = original(collection, *args, **kwargs)
        helpers.inspect_executor(container, sandbox)
        inspections.append(container.id)
        return container
    started = time.monotonic()
    # Global instrumentation is only used for serial/trusted stress cases.
    if stress:
        with patch.object(ContainerCollection, 'create', create):
            raw = sandbox.execute(fixture['code'], config['testbenchCode'])
    else:
        raw = sandbox.execute(fixture['code'], config['testbenchCode'])
    parsed = parse_evaluation_result(raw)
    expected = 'resource_limit' if stress else fixture['expectedStatus'].lower()
    clean = raw.get('cleanup_success') is True
    if raw.get('resource_job'):
        clean = clean and not (ROOT/raw['resource_job']).exists() and not (ROOT/(raw['resource_job']+'.json')).exists()
    return dict(case=name, expected=expected, verdict=parsed['status'], matched=parsed['status']==expected,
                cleanup=clean, elapsed_ms=round((time.monotonic()-started)*1000,3), budgets=profile,
                compile=raw.get('compile_exit_code'), simulation=raw.get('simulation_exit_code'),
                exit=raw.get('exit_code'), complete=raw.get('output_complete'),
                resource_failure=raw.get('resource_failure'), oom_killed=raw.get('oom_killed'),
                pid_limit_events=raw.get('pid_limit_events'), workspace_free_bytes=raw.get('workspace_free_bytes'),
                memory_limit_events=raw.get('memory_limit_events'),
                failure_phase=raw.get('failure_phase'), failure_type=raw.get('failure_type'),
                rpc_events=raw.get('rpc_events',[]), diagnostic_truncated=raw.get('diagnostics_truncated',False),
                inspected_stress_executors=len(inspections))


def run(catalog, mode):
    cases=[]
    if mode=='serial':
        for round_id in range(2):
            for name,config in catalog.items():
                for fixture in ('A','C'):
                    cases.append(evaluate(config,fixture,f'serial/{round_id}/{name}/{fixture}'))
    elif mode=='concurrent':
        for wave in range(2):
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
                futures=[pool.submit(evaluate,config,'A',f'concurrent/{wave}/{name}') for name,config in catalog.items()]
                cases.extend(f.result() for f in futures)
    elif mode=='overlap':
        for name,config in catalog.items():
            for fixture in ('A','C'):
                cases.append(evaluate(config,fixture,f'overlap/{name}/{fixture}'))
    elif mode=='stress':
        for stress in ('memory','pids','file','workspace'):
            cases.append(evaluate(catalog['and-gate-demo'],'A','trusted/'+stress,stress=stress))
            cases.append(evaluate(catalog['and-gate-demo'],'A','recovery/'+stress))
        workspace=Workspace(docker.from_env(timeout=10))
        records=[workspace.reserve() for _ in range(4)]
        try:
            cases.append(evaluate(catalog['and-gate-demo'],'A','admission-full'))
            cases[-1]['expected']='resource_limit'
            cases[-1]['matched']=cases[-1]['verdict']=='resource_limit' and cases[-1]['resource_failure']=='admission'
        finally:
            for record in records:
                workspace.cleanup(record)
        cases.append(evaluate(catalog['and-gate-demo'],'A','recovery/admission'))
    else:
        raise ValueError('Unknown fixed matrix mode')
    leftovers=[p.name for p in ROOT.iterdir() if p.name!='.admission.lock']
    failed=[case['case'] for case in cases if not case['matched'] or not case['cleanup'] or case['diagnostic_truncated']]
    if leftovers:
        failed.append('workspace cleanup')
    return dict(mode=mode,count=len(cases),failed=failed,cases=cases,workspace_limit_bytes=WORKSPACE_BYTES,
                supported_concurrency=4, inspected_stress_executors=sum(c['inspected_stress_executors'] for c in cases))


if __name__=='__main__':
    try:
        with helpers.PID_RECORD.open('x',encoding='ascii') as file:
            os.chmod(helpers.PID_RECORD,0o600)
            file.write(str(os.getpid())); file.flush(); os.fsync(file.fileno())
        payload=json.load(sys.stdin)
        result=run(payload['catalog'],sys.argv[1])
        print(json.dumps(result))
        raise SystemExit(1 if result['failed'] else 0)
    except Exception as error:
        print(json.dumps({'failed':type(error).__name__,'reason':'private diagnostics withheld'}),file=sys.stderr)
        raise SystemExit(1) from None
    finally:
        if helpers.PID_RECORD.exists() and helpers.PID_RECORD.read_text()==str(os.getpid()):
            helpers.PID_RECORD.unlink()
