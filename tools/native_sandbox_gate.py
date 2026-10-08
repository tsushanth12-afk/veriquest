"""Opt-in, no-database native sandbox gate using the actual Dockerfiles.

Only safe resource identities/results are recorded. No HDL, token or daemon logs
are emitted. The worker has privileged daemon access; executors must not have it.
"""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile
import uuid
import hashlib
import os

ROOT = Path(__file__).resolve().parents[1]
LABEL = 'veriquest.native-gate'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--docker', required=True)
    parser.add_argument('--authorize-native-test', action='store_true')
    parser.add_argument('--baseline', action='store_true')
    parser.add_argument('--reliability', action='store_true')
    parser.add_argument('--checks-only', action='store_true')
    args = parser.parse_args()
    if not args.authorize_native_test:
        parser.error('Explicit native test authorization required')
    run = uuid.uuid4().hex
    plan = dict(run=run, worker='vq-native-worker-' + run,
                volume='vq-native-workspaces-' + run,
                worker_image='vq-native-worker:' + run,
                executor_image='vq-native-executor:' + run)
    directory = Path(tempfile.mkdtemp(prefix='vq-native-intent-'))
    journal = directory / 'resources.json'
    with journal.open('x', encoding='utf-8') as handle:
        json.dump(plan, handle)
        handle.flush()
        os.fsync(handle.fileno())
    print('RESOURCE_INTENT ' + str(journal), flush=True)
    ledger = []
    probe_results = []
    wasm = None

    def docker(*argv, data=None, limit=300):
        completed = subprocess.run([args.docker, *argv], input=data, capture_output=True,
                                   text=True, timeout=limit, cwd=ROOT)
        ledger.append(dict(command=list(argv), exit=completed.returncode))
        if completed.returncode:
            try:
                safe_result = json.loads(completed.stdout)
                if isinstance(safe_result, dict) and 'cases' in safe_result:
                    probe_results.append(safe_result)
            except ValueError:
                pass
            if 'native_sandbox_probe.py' in ' '.join(argv):
                for line in completed.stderr.splitlines():
                    try:
                        diagnostic = json.loads(line)
                        if set(diagnostic) <= {'failed', 'reason'}:
                            print('PROBE_DIAGNOSTIC ' + json.dumps(diagnostic), flush=True)
                    except ValueError:
                        pass
            raise RuntimeError('Docker step failed: ' + argv[0])
        return completed.stdout

    failure = None
    result = None
    try:
        if docker('context', 'show').strip() != 'desktop-linux' or docker('info', '--format', '{{.OSType}}').strip() != 'linux':
            raise RuntimeError('Expected local Docker Desktop Linux context')
        docker('build', '--quiet', '-t', plan['worker_image'], '-f', 'worker/Dockerfile', '.')
        docker('build', '--quiet', '-t', plan['executor_image'], 'execution')
        docker('volume', 'create', '--label', LABEL + '=' + run,
               '--opt', 'type=tmpfs', '--opt', 'device=tmpfs', '--opt', 'o=size=134217728,mode=0700', plan['volume'])
        docker('run', '-d', '--name', plan['worker'], '--label', LABEL + '=' + run,
               '--network', 'none', '--read-only', '--memory', '512m', '--cpus', '1',
               '--pids-limit', '128', '--security-opt', 'no-new-privileges:true',
               '--cap-drop', 'ALL', '--cap-add', 'CHOWN', '--cap-add', 'FOWNER', '--cap-add', 'DAC_OVERRIDE',
               '--tmpfs', '/tmp:rw,nosuid,noexec,size=64m',
               '--mount', 'type=bind,source=/var/run/docker.sock,target=/var/run/docker.sock',
               '--mount', 'type=volume,source=' + plan['volume'] + ',target=/var/lib/veriquest/workspaces',
               '--mount', 'type=bind,source=' + str(ROOT / 'tests') + ',target=/app/tests,readonly',
               '--mount', 'type=bind,source=' + str(ROOT / 'src/evaluator/testbenchCatalog.ts') + ',target=/app/src/evaluator/testbenchCatalog.ts,readonly',
               '--mount', 'type=bind,source=' + str(ROOT / 'supabase/migrations/002_seed_demo_challenge.sql') + ',target=/app/supabase/migrations/002_seed_demo_challenge.sql,readonly',
               '-e', 'VQ_WORKSPACE_VOLUME=' + plan['volume'],
               '-e', 'EXECUTION_IMAGE=' + plan['executor_image'],
               '-e', 'NATIVE_WORKER_IMAGE=' + plan['worker_image'],
               '--log-driver', 'none', plan['worker_image'], 'sleep', 'infinity')
        # Node imports the existing server catalog; capture privately, never print.
        catalog = subprocess.run(['node', '--experimental-strip-types', '--input-type=module', '-e',
            "import {TESTBENCH_CATALOG as c} from './src/evaluator/testbenchCatalog.ts'; console.log(JSON.stringify(c));"],
            capture_output=True, text=True, cwd=ROOT, timeout=30)
        if catalog.returncode:
            raise RuntimeError('Catalog export failed')
        if not args.baseline:
            for test in ('test_verdict_integrity.py', 'test_worker_dispatch.py', 'test_native_workspace.py', 'test_native_diagnostics.py'):
                docker('exec', plan['worker'], 'python', '-B', '/app/tests/' + test)
                print('PACKAGED_REGRESSION ' + test + ' exit=0', flush=True)
            docker('exec', plan['worker'], 'python', '-B', '-m', 'pip', 'check')
        hashes = {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest()
                  for folder in ('worker', 'backend/app') for path in (ROOT / folder).rglob('*.py')}
        payload = json.dumps(dict(catalog=json.loads(catalog.stdout), hashes=hashes,
            runner_hash=hashlib.sha256((ROOT / 'execution/run.sh').read_bytes().replace(b'\r\n', b'\n')).hexdigest()))
        if args.checks_only:
            result = {'checks_only': True}
        else:
            output = docker('exec', '-i', plan['worker'], 'python', '-B', '/app/tests/native_sandbox_probe.py',
                            '--baseline' if args.baseline else '--live', data=payload, limit=180)
            result = json.loads(output)
            probe_results.append(result)
            print('NATIVE_GATE '+json.dumps({k:result.get(k) for k in ('assertions','inspected_executors','packaged_source_files')}), flush=True)
            if args.reliability:
                for mode in ('serial','concurrent','overlap','stress'):
                    if mode=='overlap':
                        wasm = subprocess.Popen(['node','--experimental-strip-types','tests/verdict_integrity.test.mjs','--python',str(ROOT/'.venv/Scripts/python.exe')],
                                                cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
                    step = json.loads(docker('exec','-i',plan['worker'],'python','-B','/app/tests/native_reliability_probe.py',mode,data=payload,limit=180))
                    probe_results.append(step)
                    print('MATRIX '+json.dumps({key:step[key] for key in ('mode','count','failed','supported_concurrency')}),flush=True)
                    if mode=='overlap':
                        stdout, stderr=wasm.communicate(timeout=180)
                        if wasm.returncode:
                            raise RuntimeError('WASM suite failed; private diagnostics withheld')
                        print('WASM exit=0 '+next(line for line in stdout.splitlines() if line.startswith('PASS:')),flush=True)
                        probe_results.append(dict(wasm_exit=0,summary=next(line for line in stdout.splitlines() if line.startswith('PASS:'))))
                        wasm=None
    except Exception as error:
        failure = type(error).__name__ + ': ' + str(error)
        print('GATE_FAILED ' + failure, flush=True)
    finally:
        if wasm is not None:
            wasm.terminate()
            try:
                wasm.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                wasm.kill(); wasm.communicate(timeout=10)
        # Independent exact label inspection; a daemon error is NOT absence.
        cleanup = []
        try:
            names = docker('ps', '-a', '--filter', 'label=' + LABEL + '=' + run,
                           '--format', '{{.Names}}').splitlines()
            for name in names:
                if name != plan['worker']:
                    raise RuntimeError('Unexpected task container')
                # Production recovery validates exact per-job records and labels.
                docker('exec', name, 'python', '-B', '/app/tests/native_sandbox_probe.py', '--recover')
                docker('rm', '-f', name)
            metadata = json.loads(docker('volume', 'inspect', plan['volume']))[0]
            if metadata['Labels'].get(LABEL) != run:
                raise RuntimeError('Volume identity mismatch')
            if docker('ps', '-a', '--filter', 'volume=' + plan['volume'], '--format', '{{.ID}}').strip():
                raise RuntimeError('Workspace still mounted; retaining intent')
            docker('volume', 'rm', plan['volume'])
            for tag in (plan['worker_image'], plan['executor_image']):
                docker('image', 'rm', tag)
            cleanup.append('exact containers/volume/image tags removed')
        except Exception as error:
            failure = failure or 'Cleanup failed: ' + type(error).__name__
            cleanup.append('incomplete; retain exact intent')
        journal.with_name('result.json').write_text(json.dumps(
            dict(plan=plan, commands=ledger, result=result, probe_results=probe_results, failure=failure, cleanup=cleanup), indent=2), encoding='utf-8')
        print('CLEANUP ' + '; '.join(cleanup), flush=True)
    return 1 if failure else 0


if __name__ == '__main__':
    raise SystemExit(main())
