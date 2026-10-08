"""Production workspace/profile unit tests; mocked daemon, real isolated Linux files."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, '/app')
import docker
from worker.execution.workspace import Workspace, VOLUME_OPTIONS, WORKSPACE_BYTES
from worker.execution.profile import parse_execution_profile
from worker.execution.sandbox import DockerSandbox


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.patcher = patch('worker.execution.workspace.ROOT', self.root)
        self.patcher.start()
        self.client = Mock()
        self.client.volumes.get.return_value.attrs = dict(Driver='local', Options=VOLUME_OPTIONS.copy())
        self.quota = patch('worker.execution.workspace.os.statvfs', return_value=Mock(
            f_blocks=WORKSPACE_BYTES//4096, f_frsize=4096, f_bavail=WORKSPACE_BYTES//4096))
        self.quota.start()
        worker = self.client.containers.get.return_value
        worker.id = 'a' * 64
        worker.attrs = dict(Mounts=[dict(Destination=str(self.root), Type='volume', Name='unit-volume', RW=True)])
        self.env = patch.dict(os.environ, {'VQ_WORKSPACE_VOLUME': 'unit-volume'})
        self.env.start()
        self.workspace = Workspace(self.client)

    def tearDown(self):
        self.env.stop()
        self.patcher.stop()
        self.quota.stop()
        self.directory.cleanup()

    def missing_container(self):
        self.client.containers.get.side_effect = docker.errors.NotFound('task executor absent')

    def test_configuration_fail_closed(self):
        for value in ('', '../escape', '/host/path', 'name with spaces'):
            with patch.dict(os.environ, {'VQ_WORKSPACE_VOLUME': value}), self.assertRaises(ValueError):
                Workspace(self.client)
        self.client.volumes.get.return_value.attrs['Options'] = {'device': '/host'}
        with self.assertRaises(ValueError):
            Workspace(self.client)
        self.client.volumes.get.return_value.attrs['Options'] = VOLUME_OPTIONS.copy()
        self.client.containers.get.return_value.attrs['Mounts'][0]['RW'] = False
        with self.assertRaises(ValueError):
            Workspace(self.client)
        self.client.containers.get.return_value.attrs['Mounts'][0]['RW'] = True
        self.client.containers.get.return_value.attrs['Mounts'].append(dict(Destination=str(self.root / 'shadow')))
        with self.assertRaises(ValueError):
            Workspace(self.client)

    def test_record_types_and_traversal(self):
        record = self.workspace.reserve()
        for key, bad in [('version', True), ('job', '../escape'), ('owner', None), ('volume', 'other'), ('container', 'other')]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.workspace.validate({**record, key: bad})
        with self.assertRaises(ValueError):
            self.workspace.recover('../escape')

    def test_permissions_and_safe_intent(self):
        record = self.workspace.create('unit-private-source', 'unit-private-token')
        text = (self.root / (record['job'] + '.json')).read_text()
        self.assertNotIn('unit-private', text)
        self.assertLess(len(text), 1024)
        self.assertEqual((self.root / (record['job'] + '.json')).stat().st_mode & 0o777, 0o600)
        self.assertEqual((self.root / record['job'] / 'input/submission.v').stat().st_mode & 0o777, 0o440)
        self.assertEqual((self.root / record['job'] / 'output').stat().st_uid, 1000)
        mounts = self.workspace.mounts(record)
        self.assertEqual(mounts[0]['VolumeOptions']['Subpath'], record['job'] + '/input')
        self.assertTrue(mounts[0]['ReadOnly'])
        target = self.root / record['job'] / 'input'
        target.rename(target.with_name('retained-input'))
        target.symlink_to(target.with_name('retained-input'))
        with self.assertRaises(ValueError):
            self.workspace.mounts(record)

    def test_stage_artifact_integrity(self):
        record = self.workspace.create('source', 'bench')
        target = self.root / record['job'] / 'output/compile.exit'
        for value, expected in [('0', 0), ('2', 2), ('', None), ('0000', None), ('true', None), ('1\n', None)]:
            target.write_text(value)
            self.assertEqual(self.workspace.stage_exit(record, 'compile.exit'), expected)
        target.unlink()
        target.symlink_to(self.root / (record['job'] + '.json'))
        self.assertIsNone(self.workspace.stage_exit(record, 'compile.exit'))

    def test_exact_cleanup_is_idempotent_and_does_not_follow_symlinks(self):
        record = self.workspace.create('source', 'bench')
        outside = self.root / 'unrelated'
        outside.mkdir()
        (outside / 'sentinel').write_text('preserve')
        (self.root / record['job'] / 'output/linked').symlink_to(outside)
        self.missing_container()
        self.workspace.cleanup(record)
        self.workspace.cleanup(record)
        self.assertEqual((outside / 'sentinel').read_text(), 'preserve')

    def test_mismatched_container_and_daemon_errors_preserve_intent(self):
        record = self.workspace.create('source', 'bench')
        self.client.containers.get.return_value.attrs = dict(Config=dict(Labels={}))
        with self.assertRaises(ValueError):
            self.workspace.cleanup(record)
        self.client.containers.get.return_value.remove.assert_not_called()
        self.client.containers.get.side_effect = docker.errors.APIError('daemon unavailable')
        with self.assertRaises(docker.errors.APIError):
            self.workspace.cleanup(record)
        self.assertTrue((self.root / (record['job'] + '.json')).exists())

    def test_recovery_record_permissions_and_malformed_payload(self):
        record = self.workspace.reserve()
        target = self.root / (record['job'] + '.json')
        os.chmod(target, 0o644)
        with self.assertRaises(ValueError):
            self.workspace.recover(record['job'])
        os.chmod(target, 0o600)
        target.write_text(json.dumps([]))
        with self.assertRaises(ValueError):
            self.workspace.recover(record['job'])

    def test_profile_ceilings(self):
        self.assertEqual(parse_execution_profile(None)['timeout_ms'], 5000)
        for bad in [dict(memory_mb=257), dict(timeout_ms=5001), dict(cpu_limit='NaN'),
                    dict(pids_limit=True), dict(max_output_bytes=0), {'unknown': 1},
                    '{"timeout_ms":1,"timeout_ms":2}']:
            with self.subTest(profile=bad), self.assertRaises(ValueError):
                parse_execution_profile(bad)
        for value in ('0', '65537', 'invalid', '-1', '0128'):
            with patch.dict(os.environ, {'MAX_OUTPUT_BYTES': value}), self.assertRaises(ValueError):
                DockerSandbox()
        with patch.dict(os.environ, {'MAX_OUTPUT_BYTES': '128'}), patch('docker.from_env'):
            self.assertEqual(DockerSandbox(max_output_bytes=1024).max_output_bytes, 128)

    def test_admission_four_records_and_exact_release(self):
        records = [self.workspace.reserve() for _ in range(4)]
        with self.assertRaises(ValueError):
            self.workspace.reserve()
        self.missing_container()
        self.workspace.cleanup(records[0])
        self.assertIsNotNone(self.workspace.reserve())

    def test_remove_fault_is_precise_and_preserves_record(self):
        from worker.execution.workspace import LABEL
        record=self.workspace.create('source','bench')
        container=self.client.containers.get.return_value
        container.attrs=dict(Config=dict(Labels={LABEL:record['job'],
            'veriquest.sandbox.volume':self.workspace.volume,'veriquest.sandbox.owner':record['owner']}))
        class ReadTimeout(Exception):
            pass
        container.remove.side_effect=ReadTimeout('unsafe secret exception detail')
        with self.assertRaises(ReadTimeout):
            self.workspace.cleanup(record)
        self.assertEqual(self.workspace.trace.last_failure,'remove')
        self.assertTrue((self.root/(record['job']+'.json')).exists())
        self.assertNotIn('unsafe secret',repr(self.workspace.trace.events))


if __name__ == '__main__':
    unittest.main(verbosity=2)
