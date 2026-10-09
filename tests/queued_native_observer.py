"""Passive test-worker profiling only. Never replace functions/dependencies/results.

Mounted as sitecustomize in the task worker only. Reports fixed metadata, not HDL,
trusted benches, nonces, credentials, SQL values or arbitrary exception messages.
"""
import json
import re
import sys
from uuid import UUID


def identity():
    from celery import current_task
    r = current_task.request
    return {'task_id': str(UUID(r.id)), 'submission_id': str(UUID(r.args[0]))}


def emit(kind, data):
    import logging
    logging.getLogger('veriquest.native_observer').warning('VQ_NATIVE_%s %s', kind, json.dumps(data, separators=(',', ':')))


def safe_result(raw):
    fields = ('compile_exit_code', 'simulation_exit_code', 'exit_code', 'timed_out',
              'output_complete', 'output_truncated', 'cleanup_success', 'cleanup_error',
              'diagnostics_truncated', 'retained_output_bytes', 'max_transport_chunk_bytes',
              'oom_killed', 'pid_limit_events', 'memory_limit_events', 'workspace_free_bytes')
    result = {k: raw.get(k) for k in fields if type(raw.get(k)) in (int, bool, type(None))}
    job = raw.get('resource_job')
    result['job'] = job if isinstance(job, str) and re.fullmatch('[a-f0-9]{32}', job) else None
    from worker.execution.diagnostics import PHASES
    result['failure_phase'] = raw.get('failure_phase') if raw.get('failure_phase') in PHASES else None
    categories = {'timeout', 'transport_error', 'not_found', 'daemon_error', 'io_error', 'invalid_metadata', 'internal_error'}
    result['failure_type'] = raw.get('failure_type') if raw.get('failure_type') in categories else None
    result['rpc_events'] = [{k: e[k] for k in ('phase','start_ms','elapsed_ms','deadline_ms','outcome','category') if k in e}
                            for e in (raw.get('rpc_events') or [])[:96] if e.get('phase') in PHASES]
    text = raw.get('stdout', '')
    nonce = raw.get('verdict_nonce', '')
    result['legacy_accepted_seen'] = 'VERIQUEST_STATUS: ACCEPTED' in text
    result['trusted_record_count'] = text.count('VQ_TRUSTED:' + nonce + ':') if re.fullmatch('[a-f0-9]{64}', nonce) else 0
    return result


def install():
    import docker
    from worker.execution.workspace import ROOT
    seen = set()
    def profile(frame, event, arg):
        name = frame.f_code.co_name
        if name not in {'verify_executor','_execute_docker','award_xp','update_streak','check_quest_completion','check_badge_awards'}:
            return
        filename = frame.f_code.co_filename.replace('\\', '/')
        try:
            ids = identity()
            if filename.endswith('/worker/execution/workspace.py') and name == 'verify_executor' and event == 'return':
                c = frame.f_locals['container']; h = c.attrs['HostConfig']; cfg = c.attrs['Config']
                emit('CREATE', {**ids, 'job': cfg['Labels']['veriquest.sandbox.job'], 'container_id': c.id,
                    'user': cfg['User'], 'network': h['NetworkMode'], 'readonly': h['ReadonlyRootfs'],
                    'privileged': h['Privileged'], 'caps': h['CapDrop'], 'cap_add': h.get('CapAdd'),
                    'security': h['SecurityOpt'], 'memory': h['Memory'], 'swap': h['MemorySwap'],
                    'cpu': h['NanoCpus'], 'pids': h['PidsLimit'], 'tmpfs': h['Tmpfs'],
                    'log': h['LogConfig']['Type'], 'binds': bool(h.get('Binds')), 'ports': bool(h.get('PortBindings')),
                    'ulimits': h.get('Ulimits'), 'mounts': h['Mounts']})
            elif filename.endswith('/worker/execution/sandbox.py') and name == '_execute_docker' and event == 'return' and isinstance(arg, dict):
                result = safe_result(arg); job = result['job']
                if job:
                    result['workspace_absent'] = not (ROOT/job).exists() and not (ROOT/(job+'.json')).exists()
                    try: frame.f_locals['self'].client.containers.get('vq-exec-'+job)
                    except docker.errors.NotFound: result['executor_absent'] = True
                    else: result['executor_absent'] = False
                emit('RESULT', {**ids, **result})
            elif filename.endswith('/backend/app/gamification/xp.py') and event == 'call':
                key = (ids['task_id'], name)
                if key not in seen:
                    seen.add(key); emit('ACCOUNTING', {**ids, 'step': name, 'observed_call': True})
        except Exception:
            # Missing evidence fails host assertions; never alter production calls.
            pass
    def trace(frame, event, arg):
        if not frame.f_code.co_filename.replace('\\','/').endswith('/backend/app/gamification/xp.py'):
            return None
        if event == 'exception' and arg[0].__name__ not in {'StopIteration','StopAsyncIteration','GeneratorExit'}:
            try:
                error = arg[1]; code = getattr(error,'sqlstate',None)
                emit('ACCOUNTING_ERROR', {**identity(), 'step': frame.f_code.co_name,
                    'failure_type': type(error).__name__,
                    'sqlstate': code if isinstance(code,str) and re.fullmatch('[A-Z0-9]{5}',code) else None})
            except Exception: pass
        return trace
    sys.setprofile(profile)
    sys.settrace(trace)


def workspace_probe(recover):
    import docker
    from worker.execution.workspace import Workspace, ROOT, VOLUME_OPTIONS, WORKSPACE_BYTES
    w = Workspace(docker.from_env(timeout=10)); records = list(ROOT.glob('*.json'))
    if recover:
        for record in records: w.recover(record.stem)
    return {'bounded_bytes': WORKSPACE_BYTES, 'volume_options': VOLUME_OPTIONS,
            'records': len(list(ROOT.glob('*.json'))),
            'leftovers': len([p for p in ROOT.iterdir() if p.name != '.admission.lock']),
            'recovered': len(records) if recover else 0}


if __name__ == 'sitecustomize':
    install()
elif __name__ == '__main__':
    try: print(json.dumps(workspace_probe('--recover' in sys.argv)))
    except Exception as e:
        print(json.dumps({'failed': type(e).__name__})); sys.exit(1)
