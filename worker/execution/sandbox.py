"""Native Icarus adapter. No host binds, synthetic grading, or silent cleanup."""
import logging
import os
import re
import threading
import time
from .profile import parse_execution_profile
from .verdict_protocol import prepare_testbench, validate_student_source
from .workspace import Workspace, WorkspaceCapacityError, ROOT
from .diagnostics import RpcTrace

logger = logging.getLogger('veriquest.sandbox')


class DockerSandbox:
    def __init__(self, image=None, timeout_ms=5000, memory_mb=256, cpu_limit='1.0',
                 pids_limit=64, max_output_bytes=65536):
        profile = parse_execution_profile(dict(timeout_ms=timeout_ms, memory_mb=memory_mb,
            cpu_limit=cpu_limit, pids_limit=pids_limit, max_output_bytes=max_output_bytes))
        self.image = image or os.environ.get('EXECUTION_IMAGE', 'veriquest-icarus:latest')
        self.timeout_s = profile['timeout_ms'] / 1000
        self.memory_mb = profile['memory_mb']
        self.cpu_limit = float(profile['cpu_limit'])
        self.pids_limit = profile['pids_limit']
        self.max_output_bytes = profile['max_output_bytes']
        output_ceiling = os.environ.get('MAX_OUTPUT_BYTES')
        if output_ceiling is not None:
            if not re.fullmatch(r'[1-9][0-9]{0,4}', output_ceiling) or int(output_ceiling) > 65536:
                raise ValueError('Invalid configured output ceiling')
            self.max_output_bytes = min(self.max_output_bytes, int(output_ceiling))
        self.client = None
        try:
            import docker
            self.client = docker.from_env(timeout=10)
            self.client.ping()
        except Exception:
            self.client = None
            logger.error('Docker unavailable; private diagnostics withheld')

    def execute(self, student_code, testbench):
        if not isinstance(testbench, str) or not testbench.strip():
            return dict(configuration_error=True, stdout='', stderr='Missing trusted testbench', exit_code=-1)
        try:
            if len(testbench.encode('utf-8')) > 65536:
                raise ValueError('Trusted testbench too large')
            trusted = prepare_testbench(testbench)
        except ValueError:
            return dict(configuration_error=True, stdout='', stderr='Invalid trusted testbench', exit_code=-1)
        try:
            if not isinstance(student_code, str) or not student_code.strip() or len(student_code.encode('utf-8')) > 65536:
                raise ValueError('Invalid source')
            validate_student_source(student_code, trusted['reserved'])
        except ValueError:
            return dict(source_error=True, stdout='', stderr='Unsupported HDL capability or invalid source', exit_code=-1)
        if not self.client:
            return self._execute_fallback(student_code, testbench)
        return self._execute_docker(student_code, trusted)

    def _execute_docker(self, student_code, trusted):
        raw = dict(stdout='', stderr='', exit_code=-1, timed_out=False,
                   output_complete=False, output_truncated=False, cleanup_success=False)
        workspace = record = None
        stream = None
        collector = None
        phase = 'workspace'
        allocation_started = False
        trace = RpcTrace()
        try:
            workspace = Workspace(self.client, trace=trace)
            allocation_started = True
            record = workspace.reserve()
            raw['resource_job'] = record['job']
            trace.call('workspace.populate', lambda: workspace.populate(record, student_code, trusted['code']), deadline_ms=None)
            trace.call('image.inspect', lambda: self.client.images.get(self.image))
            phase = 'container_create'
            container = trace.call('create', lambda: self.client.containers.create(image=self.image,
                name=record['container'], command=['/usr/local/bin/vq-run'],
                mounts=workspace.mounts(record), network_disabled=True, network_mode='none',
                mem_limit=f'{self.memory_mb}m', memswap_limit=f'{self.memory_mb}m',
                nano_cpus=int(self.cpu_limit * 1e9), pids_limit=self.pids_limit,
                security_opt=['no-new-privileges:true'], cap_drop=['ALL'],
                read_only=True, user='1000:1000',
                tmpfs={'/tmp': 'rw,noexec,nosuid,nodev,size=64m,mode=1777'},
                labels={'veriquest.sandbox.job': record['job'],
                        'veriquest.sandbox.volume': workspace.volume,
                        'veriquest.sandbox.owner': record['owner']},
                log_config={'Type': 'none'},
                ulimits=[{'Name': 'fsize', 'Soft': 67108864, 'Hard': 67108864}]))
            workspace.verify_executor(container, record)
            # Subscribe before start: no daemon logs, no lost fast-process output.
            phase = 'attach'
            stream = trace.call('attach', lambda: container.attach(stream=True, demux=True, logs=False))
            streams = [bytearray(), bytearray()]
            done = threading.Event()
            overflow = threading.Event()
            capture = {'complete': True, 'bytes': 0, 'max_frame': 0}

            def collect():
                started = time.monotonic()
                category = None
                try:
                    for pair in stream:
                        if not isinstance(pair, tuple) or len(pair) != 2:
                            raise ValueError('Invalid transport frame')
                        for index, chunk in enumerate(pair):
                            if chunk is None:
                                continue
                            if not isinstance(chunk, bytes):
                                raise ValueError('Invalid transport chunk')
                            capture['max_frame'] = max(capture['max_frame'], len(chunk))
                            remaining = self.max_output_bytes - capture['bytes']
                            streams[index].extend(chunk[:remaining])
                            capture['bytes'] += min(len(chunk), remaining)
                            if len(chunk) > remaining:
                                capture['complete'] = False
                                overflow.set()
                                return
                except Exception as error:
                    capture['complete'] = False
                    category = trace.category(error)
                finally:
                    trace.note('output_collection', started, round(self.timeout_s*1000),
                               'overflow' if overflow.is_set() else 'complete' if capture['complete'] else 'incomplete', category)
                    done.set()

            collector = threading.Thread(target=collect, daemon=True)
            collector.start()
            phase = 'start'
            deadline = time.monotonic() + self.timeout_s
            trace.call('start', container.start)
            remaining = deadline - time.monotonic()
            finished = remaining > 0 and trace.call('output_wait', lambda: done.wait(remaining), deadline_ms=round(remaining*1000))
            raw['timed_out'] = not finished and not overflow.is_set()
            if finished and not overflow.is_set() and capture['complete']:
                trace.call('inspect.after_output', container.reload)
                if container.attrs.get('State', {}).get('Running') is not False:
                    capture['complete'] = False  # clean EOF while process alive is not completeness evidence
            if not finished or overflow.is_set() or not capture['complete']:
                capture['complete'] = False
                try:
                    trace.call('kill', container.kill)
                except Exception:
                    trace.call('inspect.after_kill', container.reload)
                    if container.attrs.get('State', {}).get('Running'):
                        raise RuntimeError('Executor termination failed') from None
            waited = trace.call('wait', lambda: container.wait(timeout=3), deadline_ms=3000)
            phase = 'capture_completion'
            trace.call('stream.close', stream.close, deadline_ms=None)
            trace.call('collector.join', lambda: collector.join(timeout=2), deadline_ms=2000)
            if collector.is_alive():
                raise RuntimeError('Capture did not terminate')
            raw.update(stdout=streams[0].decode('utf-8', errors='replace'),
                stderr=streams[1].decode('utf-8', errors='replace'),
                exit_code=waited.get('StatusCode', -1),
                compile_exit_code=workspace.stage_exit(record, 'compile.exit'),
                simulation_exit_code=workspace.stage_exit(record, 'simulation.exit'),
                verdict_nonce=trusted['nonce'], expected_total=trusted['total'],
                output_truncated=overflow.is_set(), retained_output_bytes=capture['bytes'],
                max_transport_chunk_bytes=capture['max_frame'],
                output_complete=capture['complete'] and not raw['timed_out'])
            trace.call('inspect.after_output', container.reload)
            resources = workspace.resource_evidence(record)
            pid_events = resources['pid_limit_events']
            raw.update(oom_killed=container.attrs.get('State', {}).get('OOMKilled') is True,
                       **resources)
            if type(pid_events) is not int or type(resources['memory_limit_events']) is not int:
                raw['output_complete'] = False
            if raw['oom_killed'] or (type(resources['memory_limit_events']) is int and resources['memory_limit_events'] > 0):
                raw['resource_failure'] = 'memory'
            elif type(pid_events) is int and pid_events > 0:
                raw['resource_failure'] = 'pids'
            elif resources['workspace_free_bytes'] == 0:
                raw['resource_failure'] = 'workspace'
            elif raw['exit_code'] == 153:
                raw['resource_failure'] = 'file'
        except WorkspaceCapacityError:
            raw.update(resource_failure='admission', output_complete=False)
            allocation_started = False  # reserve refused before creating a record
        except Exception as error:
            raw.update(output_complete=False, sandbox_error='SANDBOX_EXECUTION_FAILED',
                       failure_phase=trace.last_failure or phase, failure_type=trace.category(error))
            logger.error('Sandbox failed; private diagnostics withheld')
        finally:
            if record is not None:
                try:
                    trace.call('workspace.cleanup', lambda: workspace.cleanup(record), deadline_ms=None)
                    raw['cleanup_success'] = True
                except Exception:
                    raw.update(cleanup_error=True, output_complete=False)
                    logger.error('Sandbox cleanup pending for job %s', record['job'])
            else:
                raw['cleanup_success'] = not allocation_started
                if allocation_started:
                    raw['cleanup_error'] = True
            if stream is not None:
                try:
                    stream.close()
                except Exception:
                    raw['output_complete'] = False
            if collector is not None:
                collector.join(timeout=2)
                if collector.is_alive():
                    raw.update(output_complete=False, capture_error=True)
            if trace.last_failure and 'failure_phase' not in raw:
                raw['failure_phase'] = trace.last_failure
            raw.update(rpc_events=list(trace.events), diagnostics_truncated=trace.truncated)
        return raw

    def _execute_fallback(self, student_code, testbench):
        return dict(exit_code=-1, stdout='', stderr='Isolated Docker execution unavailable',
                    timed_out=False, output_complete=False, output_truncated=False)
