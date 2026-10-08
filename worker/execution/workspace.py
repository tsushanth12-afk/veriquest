"""Exact-job named-volume subpaths. Worker daemon access is privileged authority."""
import json
import os
from pathlib import Path
import re
import shutil
import stat
import uuid
import contextlib
import time
from .diagnostics import RpcTrace

ROOT = Path('/var/lib/veriquest/workspaces')
JOB = re.compile(r'[a-f0-9]{32}')
LABEL = 'veriquest.sandbox.job'
WORKSPACE_BYTES = 128 * 1024 * 1024
MAX_JOBS = 4
VOLUME_OPTIONS = {'type': 'tmpfs', 'device': 'tmpfs', 'o': 'size=134217728,mode=0700'}


class WorkspaceCapacityError(ValueError):
    pass


class Workspace:
    def __init__(self, client, trace=None):
        self.client = client
        self.trace = trace or RpcTrace()
        self.volume = os.environ.get('VQ_WORKSPACE_VOLUME', '')
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', self.volume):
            raise ValueError('Missing or unsafe workspace volume configuration')
        volume = self.trace.call('volume.inspect', lambda: client.volumes.get(self.volume)).attrs
        if volume.get('Driver') != 'local' or volume.get('Options') != VOLUME_OPTIONS:
            raise ValueError('Workspace requires the exact bounded local tmpfs volume')
        worker = self.trace.call('worker.inspect', lambda: client.containers.get(os.environ.get('HOSTNAME', '')))
        self.trace.call('worker.reload', worker.reload)
        mounts = [m for m in worker.attrs.get('Mounts', []) if m.get('Destination') == str(ROOT)]
        if any(m.get('Destination', '').startswith(str(ROOT) + '/') for m in worker.attrs.get('Mounts', [])):
            raise ValueError('Nested mounts may not shadow workspace storage')
        if len(mounts) != 1 or not all((mounts[0].get('Type') == 'volume',
                mounts[0].get('Name') == self.volume, mounts[0].get('RW') is True)):
            raise ValueError('Worker mount does not match configured named volume')
        self.owner = worker.id
        info = ROOT.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or os.geteuid() != 0:
            raise ValueError('Workspace root must be a real root-owned directory')
        os.chmod(ROOT, 0o700)
        capacity = os.statvfs(ROOT)
        if capacity.f_blocks * capacity.f_frsize != WORKSPACE_BYTES:
            raise ValueError('Actual workspace capacity differs from configured bound')

    @contextlib.contextmanager
    def admission(self):
        import fcntl  # Linux worker only; host parser tests do not allocate workspaces.
        fd = os.open(ROOT / '.admission.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        deadline = time.monotonic() + 0.5
        try:
            while True:
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        raise WorkspaceCapacityError('Workspace admission busy') from None
                    time.sleep(0.005)
            yield
        finally:
            os.close(fd)

    def create(self, source, bench):
        record = self.reserve()
        try:
            self.populate(record, source, bench)
        except BaseException:
            self.cleanup(record)
            raise
        return record

    def reserve(self):
        with self.admission():
            if len(list(ROOT.glob('*.json'))) >= MAX_JOBS:
                raise WorkspaceCapacityError('Workspace job capacity reached')
            free = os.statvfs(ROOT)
            if free.f_bavail * free.f_frsize < 512 * 1024:
                raise WorkspaceCapacityError('Workspace storage capacity reached')
            return self._reserve()

    def _reserve(self):
        job = uuid.uuid4().hex
        record = dict(version=1, job=job, volume=self.volume, owner=self.owner,
                      container='vq-exec-' + job)
        with (ROOT / (job + '.json')).open('x', encoding='ascii') as handle:
            os.chmod(handle.name, 0o600)
            json.dump(record, handle)
            handle.flush()
            os.fsync(handle.fileno())
        fd = os.open(ROOT, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
        return record

    def populate(self, record, source, bench):
        self.validate(record)
        path = ROOT / record['job']
        path.mkdir(mode=0o700)
        (path / 'input').mkdir(mode=0o750)
        os.chown(path / 'input', 0, 1000)
        for name, contents in [('submission.v', source), ('testbench.v', bench)]:
            target = path / 'input' / name
            with target.open('x', encoding='utf-8') as handle:
                handle.write(contents)
            os.chown(target, 0, 1000)
            os.chmod(target, 0o440)
        (path / 'output').mkdir(mode=0o700)
        os.chown(path / 'output', 1000, 1000)

    def validate(self, record):
        if (not isinstance(record, dict) or type(record.get('version')) is not int or record.get('version') != 1
                or not isinstance(record.get('job'), str) or not JOB.fullmatch(record['job'])
                or record.get('volume') != self.volume
                or record.get('container') != 'vq-exec-' + record['job']
                or not isinstance(record.get('owner'), str)
                or not re.fullmatch(r'[a-f0-9]{64}', record['owner'])):
            raise ValueError('Unsafe workspace record')

    def mounts(self, record):
        self.validate(record)
        for suffix, uid, gid, mode in [('', 0, 0, 0o700), ('input', 0, 1000, 0o750), ('output', 1000, 1000, 0o700)]:
            info = (ROOT / record['job'] / suffix).lstat()
            if (not stat.S_ISDIR(info.st_mode) or info.st_uid != uid
                    or info.st_gid != gid or stat.S_IMODE(info.st_mode) != mode):
                raise ValueError('Unsafe workspace directory or ownership')
        from docker.types import Mount
        return [Mount('/workspace/input', self.volume, read_only=True,
                      subpath=record['job'] + '/input', no_copy=True),
                Mount('/workspace/output', self.volume, read_only=False,
                      subpath=record['job'] + '/output', no_copy=True)]

    def stage_exit(self, record, name):
        self.validate(record)
        if name not in ('compile.exit', 'simulation.exit', 'pids.events', 'memory.events'):
            raise ValueError('Unknown stage')
        try:
            fd = os.open(ROOT / record['job'] / 'output' / name, os.O_RDONLY | os.O_NOFOLLOW)
            try:
                info = os.fstat(fd)
                limit = 12 if name in ('pids.events', 'memory.events') else 3
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > limit:
                    return None
                value = os.read(fd, limit+1).decode('ascii')
                return int(value) if re.fullmatch(r'[0-9]{1,' + str(limit) + r'}', value) else None
            finally:
                os.close(fd)
        except (OSError, UnicodeError):
            return None

    def resource_evidence(self, record):
        free = os.statvfs(ROOT)
        return dict(pid_limit_events=self.stage_exit(record, 'pids.events'),
                    memory_limit_events=self.stage_exit(record, 'memory.events'),
                    workspace_free_bytes=free.f_bavail * free.f_frsize)

    def verify_executor(self, container, record):
        """Refuse a daemon/SDK that drops volume-subpath or isolation options."""
        self.validate(record)
        self.trace.call('inspect.before_start', container.reload)
        host = container.attrs.get('HostConfig', {})
        config = container.attrs.get('Config', {})
        if (host.get('Binds') or host.get('Privileged') or not host.get('ReadonlyRootfs')
                or host.get('NetworkMode') != 'none' or config.get('User') != '1000:1000'
                or host.get('CapDrop') != ['ALL'] or host.get('CapAdd')
                or 'no-new-privileges:true' not in host.get('SecurityOpt', [])
                or host.get('LogConfig', {}).get('Type') != 'none' or host.get('PortBindings')):
            raise ValueError('Executor isolation configuration mismatch')
        mounts = host.get('Mounts', [])
        if len(mounts) != 2:
            raise ValueError('Unexpected executor mounts')
        for suffix, read_only in [('input', True), ('output', False)]:
            matches = [m for m in mounts if m.get('Target') == '/workspace/' + suffix]
            if len(matches) != 1:
                raise ValueError('Missing executor mount')
            mount = matches[0]
            if (mount.get('Type') != 'volume' or mount.get('Source') != self.volume
                    or mount.get('VolumeOptions', {}).get('Subpath') != record['job'] + '/' + suffix
                    or mount.get('ReadOnly', False) is not read_only):
                raise ValueError('Daemon did not retain exact volume-subpath isolation')

    def cleanup(self, record):
        """Idempotent recovery of exact records, never a container prefix sweep."""
        self.validate(record)
        import docker
        try:
            container = self.trace.call('inspect.cleanup', lambda: self.client.containers.get(record['container']), allow_not_found=True)
        except docker.errors.NotFound:
            container = None
        if container is not None:
            self.trace.call('inspect.cleanup_labels', container.reload)
            labels = container.attrs.get('Config', {}).get('Labels', {})
            if (labels.get(LABEL) != record['job'] or labels.get('veriquest.sandbox.volume') != self.volume
                    or labels.get('veriquest.sandbox.owner') != record['owner']):
                raise ValueError('Executor identity mismatch; cleanup refused')
            self.trace.call('remove', lambda: container.remove(force=True))
            try:
                self.trace.call('inspect.removal', lambda: self.client.containers.get(record['container']), allow_not_found=True)
            except docker.errors.NotFound:
                pass
            else:
                raise RuntimeError('Executor removal not confirmed')
        path = ROOT / record['job']
        if path.is_symlink():
            raise ValueError('Workspace symlink; cleanup refused')
        if path.exists():
            if not shutil.rmtree.avoids_symlink_attacks:
                raise RuntimeError('Symlink-safe deletion unavailable')
            shutil.rmtree(path)
        with self.admission():
            (ROOT / (record['job'] + '.json')).unlink(missing_ok=True)

    def recover(self, job):
        if not isinstance(job, str) or not JOB.fullmatch(job):
            raise ValueError('Invalid recovery job ID')
        fd = os.open(ROOT / (job + '.json'), os.O_RDONLY | os.O_NOFOLLOW)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_size > 1024 or info.st_uid != 0 or info.st_mode & 0o077:
                raise ValueError('Unsafe recovery record')
            record = json.loads(os.read(fd, 1025))
        finally:
            os.close(fd)
        if not isinstance(record, dict) or record.get('job') != job:
            raise ValueError('Recovery identity mismatch')
        self.cleanup(record)
