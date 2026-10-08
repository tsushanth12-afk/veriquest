"""Runs inside the actual worker image. Outputs safe assertions, never raw HDL/logs."""
import json
import os
from pathlib import Path
import sys
import tempfile
import concurrent.futures
import multiprocessing
import signal
import time
import hashlib
import importlib.metadata
from unittest.mock import patch
from docker.models.containers import ContainerCollection

sys.path.insert(0, '/app')
import docker
from worker.execution.sandbox import DockerSandbox
from worker.execution.evaluator import parse_evaluation_result
from worker.execution.workspace import Workspace, ROOT, LABEL

ASSERTIONS = 0
INSPECTIONS = 0
PID_RECORD = Path('/tmp/vq-native-probe.pid')


def check(condition, message):
    global ASSERTIONS
    if not condition:
        raise AssertionError(message)
    ASSERTIONS += 1


def inspect_executor(container, sandbox):
    global INSPECTIONS
    container.reload()
    config = container.attrs['HostConfig']
    check(config['NetworkMode'] == 'none', 'executor network')
    check(config['ReadonlyRootfs'] and not config['Privileged'], 'executor rootfs/privilege')
    check(config['CapDrop'] == ['ALL'] and not config.get('CapAdd'), 'executor capabilities')
    check('no-new-privileges:true' in config['SecurityOpt'], 'executor no-new-privileges')
    check(container.attrs['Config']['User'] == '1000:1000', 'executor UID/GID')
    check(config['Memory'] == sandbox.memory_mb * 1048576 and config['MemorySwap'] == config['Memory'], 'memory/swap')
    check(config['NanoCpus'] == int(sandbox.cpu_limit * 1e9) and config['PidsLimit'] == sandbox.pids_limit, 'CPU/PID')
    check(config['Tmpfs']['/tmp'] == 'rw,noexec,nosuid,nodev,size=64m,mode=1777', 'bounded tmpfs')
    check(any(u['Name'] == 'fsize' and u['Hard'] == u['Soft'] == 67108864 for u in config['Ulimits']), 'per-file output artifact ceiling')
    check(config['LogConfig']['Type'] == 'none' and not container.attrs.get('LogPath'), 'daemon logging disabled')
    check(not config.get('PortBindings') and not config.get('Binds'), 'no host/socket binds/ports')
    mounts = config['Mounts']
    check(len(mounts) == 2 and all(m['Type'] == 'volume' for m in mounts), 'volume-only mounts')
    job = container.attrs['Config']['Labels'][LABEL]
    check({m['VolumeOptions']['Subpath'] for m in mounts} == {job + '/input', job + '/output'}, 'exact subpaths')
    check(next(m for m in mounts if m['Target'].endswith('input'))['ReadOnly'], 'input read-only')
    check(not next(m for m in mounts if m['Target'].endswith('output')).get('ReadOnly', False), 'output writable')
    INSPECTIONS += 1


def run_case(name, source, bench, expected, instrument=True, **profile):
    sandbox = DockerSandbox(**profile)
    create = ContainerCollection.create
    inspection_errors = []
    def inspected(collection, *args, **kwargs):
        container = create(collection, *args, **kwargs)  # REAL Docker; inspection only
        try:
            inspect_executor(container, sandbox)
        except Exception as error:
            inspection_errors.append(str(error) if isinstance(error, (AssertionError, KeyError)) else type(error).__name__)
            raise
        return container
    started = time.monotonic()
    if instrument:
        with patch.object(ContainerCollection, 'create', inspected):
            raw = sandbox.execute(source, bench)
    else:
        raw = sandbox.execute(source, bench)
    check(not inspection_errors, 'Docker inspection: ' + ', '.join(inspection_errors))
    result = parse_evaluation_result(raw)
    check(result['status'] == expected, name + ': unexpected verdict ' + result['status'] +
          ' phase=' + raw.get('failure_phase', 'none') + ' type=' + raw.get('failure_type', 'none'))
    if 'resource_job' in raw:
        check(raw['cleanup_success'] is True, name + ': cleanup')
        check(not (ROOT / raw['resource_job']).exists(), name + ': remaining workspace')
        check(not (ROOT / (raw['resource_job'] + '.json')).exists(), name + ': remaining record')
        try:
            sandbox.client.containers.get('vq-exec-' + raw['resource_job'])
        except docker.errors.NotFound:
            check(True, name + ': executor removed')
        else:
            check(False, name + ': remaining executor')
    if expected in ('accepted', 'wrong_answer'):
        check(raw.get('compile_exit_code') == raw.get('simulation_exit_code') == raw['exit_code'] == 0,
              name + ': real process evidence')
        check(raw['output_complete'] and not raw['output_truncated'], name + ': complete capture')
    return raw, dict(case=name, verdict=result['status'], compile=raw.get('compile_exit_code'),
        simulation=raw.get('simulation_exit_code'), exit=raw.get('exit_code'),
        complete=raw.get('output_complete'), truncated=raw.get('output_truncated'),
        retained_bytes=raw.get('retained_output_bytes'), cleanup=raw.get('cleanup_success'),
        max_transport_chunk_bytes=raw.get('max_transport_chunk_bytes'),
        rpc_events=raw.get('rpc_events'), resource_failure=raw.get('resource_failure'),
        total=result['tests_total'], passed=result['tests_passed'], failed=result['tests_failed'],
        elapsed_ms=round((time.monotonic() - started) * 1000))


def recover():
    # A timed-out Docker exec CLI may leave its process alive. Quiesce only the
    # exact recorded probe and its verified test subprocesses before deleting jobs.
    if PID_RECORD.exists():
        fd = os.open(PID_RECORD, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            value = os.read(fd, 32).decode('ascii')
        finally:
            os.close(fd)
        if not value.isdecimal() or len(value) > 10:
            raise ValueError('Invalid native probe PID record')
        pid = int(value)
        if pid <= 1 or pid == os.getpid():
            raise ValueError('Unsafe native probe process')
        pending = [pid]
        verified = []
        while pending:
            current = pending.pop()
            try:
                command = (Path('/proc') / str(current) / 'cmdline').read_bytes()
                children = (Path('/proc') / str(current) / 'task' / str(current) / 'children').read_text().split()
            except FileNotFoundError:
                continue
            if not any(path in command.split(b'\0') for path in (b'/app/tests/native_sandbox_probe.py', b'/app/tests/native_reliability_probe.py')):
                raise ValueError('Process identity changed; recovery refused')
            verified.append(current)
            if len(verified) + len(pending) + len(children) > 128:
                raise ValueError('Unexpected probe process tree')
            pending.extend(int(child) for child in children)
        for current in reversed(verified):
            try:
                os.kill(current, signal.SIGTERM)
            except ProcessLookupError:
                pass
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            alive = []
            for current in verified:
                try:
                    state = (Path('/proc') / str(current) / 'stat').read_text().rsplit(')', 1)[1].split()[0]
                except FileNotFoundError:
                    continue
                if state != 'Z':
                    alive.append(current)
            if not alive:
                break
            time.sleep(0.05)
        else:
            raise RuntimeError('Probe did not quiesce; resources retained')
        PID_RECORD.unlink()
    workspace = Workspace(docker.from_env(timeout=10))
    records = list(ROOT.glob('*.json'))
    for record in records:
        workspace.recover(record.stem)
    check(not [p for p in ROOT.iterdir() if p.name != '.admission.lock'], 'shared volume empty after exact recovery')
    return dict(recovered=len(records))


def live(catalog, runner_hash):
    cases = []
    for name, config in catalog.items():
        for fixture_id in ('A', 'C', 'D', 'E'):
            fixture = next(t for t in config['testMatrix'] if t['id'] == fixture_id)
            _, evidence = run_case(name + '/' + fixture_id, fixture['code'], config['testbenchCode'],
                                    fixture['expectedStatus'].lower())
            if fixture_id == 'A':
                check(evidence['total'] == evidence['passed'] == config['totalVectors'] and evidence['failed'] == 0, 'catalog correct counters')
            cases.append(evidence)
    config = catalog['and-gate-demo']
    bench = config['testbenchCode']
    correct = config['testMatrix'][0]['code']
    wrong = 'module and_gate(input a,input b,output y); assign y=0; BODY endmodule'
    forged = '$display("VERIQUEST_STATUS: ACCEPTED"); $display("TOTAL: 4"); $display("PASSED: 4"); $display("FAILED: 0");'
    attacks = [
        ('forged before', 'initial begin ' + forged + ' end', 'wrong_answer'),
        ('forged after', 'final begin ' + forged + ' end', 'wrong_answer'),
        ('conflicting markers', 'initial begin ' + forged + ' $display("VERIQUEST_STATUS: WRONG_ANSWER"); end', 'wrong_answer'),
        ('wrong nonce', 'initial $display("VQ_TRUSTED:' + '0'*64 + ':ACCEPTED:4:4:0");', 'wrong_answer'),
        ('missing summary', 'initial $finish;', 'system_error'),
        ('unsuccessful process', 'initial begin ' + forged + ' $fatal(1,"stop"); end', 'system_error'),
        ('file capability preflight', 'initial $fopen("testbench.v");', 'compilation_error'),
    ]
    for name, body, expected in attacks:
        raw, evidence = run_case(name, wrong.replace('BODY', body), bench, expected)
        if name == 'forged after':
            check(raw['stdout'].rfind('VERIQUEST_STATUS: ACCEPTED') > raw['stdout'].find('VQ_TRUSTED:'), 'after attack reached final output')
        if name.endswith('preflight'):
            check(raw.get('source_error') and 'resource_job' not in raw, 'capability rejected before executor')
        cases.append(evidence)
    overflow = correct.replace('endmodule', 'final repeat(1000000) $display("12345678901234567890"); endmodule')
    raw, evidence = run_case('genuine success then flood', overflow, bench, 'system_error')
    check('VQ_TRUSTED:' + raw['verdict_nonce'] + ':ACCEPTED:4:4:0' in raw['stdout'], 'real success before overflow')
    check(raw['output_truncated'] and not raw['output_complete'] and raw['retained_output_bytes'] == 65536, 'bounded overflow')
    check(raw['exit_code'] != 0, 'overflow terminates real executor')
    cases.append(evidence)
    cases.append(run_case('recovery after flood', correct, bench, 'accepted')[1])
    infinite = correct.replace('endmodule', 'initial forever begin end endmodule')
    raw, evidence = run_case('infinite zero-delay simulation', infinite, bench, 'timeout', timeout_ms=1000)
    check(raw['compile_exit_code'] == 0 and raw['timed_out'] and raw['exit_code'] != 0, 'timeout reached native simulation/kill')
    cases.append(evidence)
    cases.append(run_case('recovery after timeout', correct, bench, 'accepted')[1])
    # Trusted fixture: one emitter executes twice; no student token injection.
    duplicate = bench.replace('$display("VERIQUEST_STATUS: ACCEPTED");', 'repeat(2) $display("VERIQUEST_STATUS: ACCEPTED");')
    raw, evidence = run_case('trusted fixture duplicate summary', correct, duplicate, 'system_error')
    check(raw['compile_exit_code'] == raw['simulation_exit_code'] == 0, 'duplicate fixture reached simulation')
    check(raw['stdout'].count(raw['verdict_nonce']) == 2, 'duplicate trusted fixture reached intended condition')
    cases.append(evidence)
    for invalid in (None, '', ' ', 3, {}, []):
        raw, _ = run_case('invalid bench', correct, invalid, 'evaluator_not_configured')
        check('resource_job' not in raw, 'invalid bench before resource allocation')
    for profile in ({'timeout_ms': 0}, {'memory_mb': 257}, {'cpu_limit': 'nan'},
                    {'pids_limit': 65}, {'max_output_bytes': 65537}, {'timeout_ms': True}):
        try:
            DockerSandbox(**profile)
        except ValueError:
            check(True, 'invalid resource profile')
        else:
            check(False, 'invalid profile accepted')
    for bad in ('', '../unsafe', '/tmp/unsafe', 'missing-native-volume'):
        with patch.dict(os.environ, {'VQ_WORKSPACE_VOLUME': bad}):
            raw, _ = run_case('unsafe/missing volume', correct, bench, 'system_error')
            check('resource_job' not in raw, 'configuration rejection before files')
    raw, evidence = run_case('missing executor image', correct, bench, 'system_error', image='vq-native-missing:never-pull')
    check(raw['cleanup_success'], 'startup failure cleanup')
    cases.append(evidence)
    raw, evidence = run_case('actual executor startup failure', correct, bench, 'system_error',
                            image=os.environ['NATIVE_WORKER_IMAGE'])
    check(raw.get('failure_phase') == 'start' and raw['cleanup_success'], 'actual OCI start failure cleaned')
    cases.append(evidence)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(run_case, 'concurrent/' + str(i), correct if i == 0 else wrong.replace('BODY', ''),
                                  bench, 'accepted' if i == 0 else 'wrong_answer', instrument=False) for i in range(2)]
        results = [f.result() for f in futures]
        check(results[0][0]['resource_job'] != results[1][0]['resource_job'], 'unique concurrent jobs')
        check(results[0][0]['verdict_nonce'] != results[1][0]['verdict_nonce'], 'fresh concurrent tokens')
        cases.extend(result[1] for result in results)
    for i in range(3):
        cases.append(run_case('repeat/' + str(i), correct, bench, 'accepted')[1])
    workspace = Workspace(docker.from_env(timeout=10))
    a = workspace.create('task input A', 'task bench A')
    b = workspace.create('task input B', 'task bench B')
    try:
        # Actual executor OS permission/isolation probe (not student HDL).
        shell = 'test "$(id -u)" = 1000 && test -r /workspace/input/submission.v && ! touch /workspace/input/nope && touch /workspace/output/allowed && ! touch /root/nope && test ! -e /var/run/docker.sock && test ! -e /var/lib/veriquest/workspaces && test ! -e /workspace/' + b['job'] + ' && sha256sum /usr/local/bin/vq-run > /workspace/output/runner.sha256 && cat /sys/fs/cgroup/memory.max /sys/fs/cgroup/pids.max /sys/fs/cgroup/cpu.max > /workspace/output/cgroups && iverilog -V 2>/dev/null | head -1 > /workspace/output/iverilog.version'
        sandbox = DockerSandbox()
        container = workspace.client.containers.create(sandbox.image, name=a['container'],
            command=['sh', '-c', shell], user='1000:1000', mounts=workspace.mounts(a),
            network_disabled=True, network_mode='none', cap_drop=['ALL'], security_opt=['no-new-privileges:true'],
            read_only=True, mem_limit='64m', memswap_limit='64m', nano_cpus=500000000, pids_limit=16,
            tmpfs={'/tmp': 'rw,noexec,nosuid,nodev,size=64m,mode=1777'},
            labels={LABEL: a['job'], 'veriquest.sandbox.volume': workspace.volume,
                    'veriquest.sandbox.owner': workspace.owner}, log_config={'Type': 'none'})
        container.start()
        check(container.wait(timeout=10)['StatusCode'] == 0, 'nonroot permissions/cross-job access')
        check((ROOT / a['job'] / 'output/allowed').exists(), 'real shared storage output visibility')
        check((ROOT / a['job'] / 'output/runner.sha256').read_text().split()[0] == runner_hash, 'actual image runner hash')
        cgroups = (ROOT / a['job'] / 'output/cgroups').read_text().splitlines()
        check(cgroups == ['67108864', '16', '50000 100000'], 'actual Linux cgroup memory/PID/CPU ceilings')
        icarus_version = (ROOT / a['job'] / 'output/iverilog.version').read_text().strip()
        check(icarus_version.startswith('Icarus Verilog version'), 'actual Icarus version')
        check((ROOT / a['job'] / 'input/submission.v').stat().st_mode & 0o777 == 0o440, 'least input mode')
        # Root-level symlink/traversal are refused, not followed.
        try:
            workspace.recover('../unsafe')
        except ValueError:
            check(True, 'traversal rejected')
        (ROOT / a['job'] / 'output/compile.exit').symlink_to(ROOT / b['job'] / 'input/submission.v')
        check(workspace.stage_exit(a, 'compile.exit') is None, 'symlink stage evidence refused')
    finally:
        workspace.cleanup(a)
        workspace.cleanup(b)
    # Observable cleanup failure; transport/execution remains real.
    with patch.object(Workspace, 'cleanup', side_effect=OSError('controlled cleanup failure')):
        raw = DockerSandbox().execute(correct, bench)
    check(raw.get('cleanup_error') and not raw['output_complete'], 'cleanup failure observable')
    check(parse_evaluation_result(raw)['error_code'] == 'SANDBOX_CLEANUP_FAILED', 'cleanup failure cannot accept')
    workspace.recover(raw['resource_job'])
    # SIGTERM a test-only calling process after actual executor is running.
    def interrupted():
        DockerSandbox(timeout_ms=5000).execute(infinite, bench)
    child = multiprocessing.Process(target=interrupted)
    child.start()
    try:
        deadline = time.monotonic() + 10
        found = None
        while time.monotonic() < deadline:
            for journal in ROOT.glob('*.json'):
                record = json.loads(journal.read_text())
                try:
                    container = workspace.client.containers.get(record['container'])
                except docker.errors.NotFound:
                    continue
                if container.attrs['State']['Running']:
                    found = record
                    break
            if found:
                break
            time.sleep(0.05)
        check(found is not None, 'interruption executor reached running')
        child.terminate()
        child.join(timeout=5)
        check(not child.is_alive(), 'calling process interrupted')
        check((ROOT / (found['job'] + '.json')).exists(), 'durable exact intent survived interruption')
        workspace.recover(found['job'])
        check(not (ROOT / found['job']).exists(), 'interrupted resources recovered')
    finally:
        if child.is_alive():
            child.terminate()
            child.join(timeout=5)
    check(not [p for p in ROOT.iterdir() if p.name != '.admission.lock'], 'all workspaces and records removed')
    check(not workspace.client.containers.list(all=True, filters={'label': 'veriquest.sandbox.volume=' + workspace.volume}), 'all executors removed')
    cases.append(run_case('recovery after interruption', correct, bench, 'accepted')[1])
    return dict(assertions=ASSERTIONS, inspected_executors=INSPECTIONS, cases=cases,
                cgroup_observation=dict(memory_bytes=67108864, pids=16, cpu_quota=50000, cpu_period=100000),
                icarus_version=icarus_version,
                permissions='shared storage/read-only inputs/nonroot output/cross-job denial verified',
                interruption='SIGTERM caller while executor running; exact journal recovery succeeded')


def baseline(catalog):
    client = docker.from_env(timeout=10)
    workspace = Workspace(client)
    record = workspace.reserve()
    with tempfile.TemporaryDirectory(prefix='vq_native_repro_') as local:
        path = Path(local)
        (path / 'probe').write_text('task-only')
        assert (path.stat().st_mode & 0o777) == 0o700
        # --mount semantics deliberately prevent the old -v auto-creation of a
        # stray daemon host directory. This probes real daemon path resolution,
        # not a full call to the old sandbox (which would create host residue).
        try:
            client.containers.create(os.environ['EXECUTION_IMAGE'], command=['true'],
                name=record['container'], labels={LABEL: record['job'],
                    'veriquest.sandbox.volume': workspace.volume, 'veriquest.sandbox.owner': workspace.owner},
                mounts=[docker.types.Mount('/probe', local, type='bind', read_only=True)],
                network_disabled=True, user='1000:1000')
        except docker.errors.APIError as error:
            assert 'bind source path does not exist' in str(error)
        else:
            raise AssertionError('Worker-only path unexpectedly visible to daemon')
        finally:
            workspace.cleanup(record)
    import inspect
    return dict(baseline='daemon rejected worker-private bind source; worker temp mode 0700',
                docker_sdk=docker.__version__, mount_signature=str(inspect.signature(docker.types.Mount)))


if __name__ == '__main__':
    try:
        if '--recover' in sys.argv:
            print(json.dumps(recover()))
        else:
            with PID_RECORD.open('x', encoding='ascii') as handle:
                os.chmod(PID_RECORD, 0o600)
                handle.write(str(os.getpid()))
                handle.flush()
                os.fsync(handle.fileno())
            payload = json.load(sys.stdin)
            for path, expected in payload['hashes'].items():
                check(hashlib.sha256((Path('/app') / path).read_bytes().replace(b'\r\n', b'\n')).hexdigest() == expected,
                      'packaged source hash')
            result = baseline(payload['catalog']) if '--baseline' in sys.argv else live(payload['catalog'], payload['runner_hash'])
            result['packaged_source_files'] = len(payload['hashes'])
            result['dependencies'] = dict(python=sys.version.split()[0], docker=docker.__version__)
            result['dependencies'].update({name: importlib.metadata.version(name) for name in ('celery', 'asyncpg', 'pydantic')})
            print(json.dumps(result))
    except Exception as error:
        print(json.dumps(dict(failed=type(error).__name__, reason=str(error) if isinstance(error, AssertionError) else 'private diagnostics withheld')), file=sys.stderr)
        raise SystemExit(1) from None
    finally:
        if '--recover' not in sys.argv and PID_RECORD.exists() and PID_RECORD.read_text() == str(os.getpid()):
            PID_RECORD.unlink()
