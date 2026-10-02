"""Production worker functions; controlled asyncpg rows/transport and sandbox.

No database, broker, real simulator or worker daemon. Stdlib assertions fail exit.
"""
import asyncio
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from worker.tasks import hdl_task as tasks
from worker.execution.profile import parse_execution_profile, DEFAULTS

ID = '33333333-3333-4333-8333-333333333333'


def database():
    conn = MagicMock()
    conn.fetchval = AsyncMock(side_effect=[ID, ID])
    conn.fetchrow = AsyncMock(return_value=dict(official_solution='module a; endmodule',
        hidden_testbench='bench', execution_profile=json.dumps(DEFAULTS)))
    conn.execute = AsyncMock()
    conn.transaction.return_value.__aenter__ = AsyncMock()
    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
    pool.close = AsyncMock()
    return conn, pool


class WorkerDispatchTests(unittest.TestCase):
    def test_registration(self):
        for name in ['execute_hdl_submission', 'validate_challenge_task']:
            self.assertIn(name, tasks.celery_app.tasks)
            self.assertEqual(tasks.celery_app.conf.task_routes[name], {'queue': 'hdl_execution'})

    def test_profiles_dict_json_null_and_lower_bounds(self):
        for value in [None, {}, json.dumps(DEFAULTS), DEFAULTS]:
            self.assertEqual(parse_execution_profile(value), DEFAULTS)
        lower = dict(timeout_ms=1, memory_mb=16, cpu_limit='0.1', pids_limit=1, max_output_bytes=1)
        self.assertEqual(parse_execution_profile(json.dumps(lower)), lower)

    def test_profiles_fail_closed(self):
        bad = ['', 'null', '[]', '[1]', 'true', '1', '{bad', [], False,
               '{"timeout_ms":1,"timeout_ms":5000}', {'unknown': 1}]
        for key, values in {
            'timeout_ms': [0, 5001, True, '5000', None, 2.5],
            'memory_mb': [0, 257, True, '256'],
            'cpu_limit': [0, 1.1, True, 'nan', 'Infinity', None, 'garbage'],
            'pids_limit': [0, 65, '64', False],
            'max_output_bytes': [0, 65537, '65536', False],
        }.items():
            bad += [{key: value} for value in values]
        for value in bad:
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_execution_profile(value)

    def test_validation_exception_and_malformed_profile_finalize_failure(self):
        for failure in ['sandbox', 'profile', 'parser', 'missing']:
            conn, pool = database()
            if failure == 'profile':
                conn.fetchrow.return_value['execution_profile'] = '[]'
            if failure == 'missing':
                conn.fetchrow.return_value = None
            sandbox = MagicMock()
            if failure == 'sandbox':
                sandbox.return_value.execute.side_effect = RuntimeError('secret exception detail')
            with patch.object(tasks, 'create_runtime_pool', AsyncMock(return_value=pool)), \
                 patch.object(tasks, 'DockerSandbox', sandbox), \
                 patch.object(tasks, 'parse_evaluation_result', side_effect=RuntimeError('secret parser error')):
                asyncio.run(tasks._validate_challenge(ID, ID))
            self.assertEqual(conn.fetchval.call_args.args[2], 'validation_failed')
            self.assertIn("is_published = FALSE", conn.fetchval.call_args.args[0])
            details = json.loads(conn.execute.call_args.args[-1])
            self.assertEqual(details, dict(result='execution_error', status='validation_failed'))
            self.assertNotIn('secret', json.dumps(details))
            pool.close.assert_awaited_once()
            if failure in ['profile', 'missing']:
                sandbox.assert_not_called()

    def test_validation_uses_production_parser(self):
        nonce = 'a'*64
        for status, passed, failed, final in [('ACCEPTED', 4, 0, 'validated'),
                                            ('WRONG_ANSWER', 3, 1, 'validation_failed')]:
            conn, pool = database()
            raw = dict(stdout=f'VQ_TRUSTED:{nonce}:{status}:4:{passed}:{failed}', stderr='',
                verdict_nonce=nonce, expected_total=4, compile_exit_code=0,
                simulation_exit_code=0, exit_code=0, timed_out=False,
                output_complete=True, output_truncated=False)
            sandbox = MagicMock()
            sandbox.return_value.execute.return_value = raw
            with patch.object(tasks, 'create_runtime_pool', AsyncMock(return_value=pool)), \
                 patch.object(tasks, 'DockerSandbox', sandbox):
                tasks.validate_challenge_task.run(ID, ID)
            sandbox.assert_called_once_with(**DEFAULTS)
            self.assertEqual(conn.fetchval.call_args.args[2], final)
            pool.close.assert_awaited_once()

    def test_validation_skip_changed_state_and_db_failure_visible(self):
        conn, pool = database()
        conn.fetchval.side_effect = None
        conn.fetchval.return_value = None
        with patch.object(tasks, 'create_runtime_pool', AsyncMock(return_value=pool)), \
             patch.object(tasks, 'DockerSandbox') as sandbox:
            asyncio.run(tasks._validate_challenge(ID, ID))
        sandbox.assert_not_called()
        conn.execute.assert_not_called()
        with patch.object(tasks, 'create_runtime_pool', AsyncMock(side_effect=OSError('unavailable'))):
            with self.assertRaises(OSError):
                tasks.validate_challenge_task.run(ID, ID)

    def test_submission_invalid_profile_never_constructs_sandbox(self):
        conn, pool = database()
        conn.fetchrow.side_effect = [dict(user_id=ID, challenge_id=ID, submitted_code='code'),
                                   dict(hidden_testbench='bench', execution_profile='[]')]
        with patch.object(tasks, 'create_runtime_pool', AsyncMock(return_value=pool)), \
             patch.object(tasks, 'DockerSandbox') as sandbox:
            asyncio.run(tasks._execute_hdl_submission(ID))
        sandbox.assert_not_called()
        self.assertIn('INVALID_EXECUTION_PROFILE', conn.execute.call_args.args[0])
        self.assertIn('evaluator_not_configured', conn.execute.call_args.args[0])
        pool.close.assert_awaited_once()


if __name__ == '__main__':
    unittest.main(verbosity=2)
