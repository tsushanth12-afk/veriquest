"""Safe production timing vocabulary; controlled exceptions, no Docker required."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from worker.execution.diagnostics import RpcTrace


class TraceTests(unittest.TestCase):
    def test_success_does_not_capture_response(self):
        trace = RpcTrace()
        secret = 'private-source-token'
        self.assertEqual(trace.call('create', lambda: secret), secret)
        self.assertNotIn(secret, repr(trace.events))
        self.assertEqual(trace.events[0]['deadline_ms'], 10000)

    def test_exception_does_not_capture_message(self):
        trace = RpcTrace()
        class ReadTimeout(Exception):
            pass
        def failed():
            raise ReadTimeout('private token/source in unsafe exception')
        with self.assertRaises(ReadTimeout):
            trace.call('wait', failed, deadline_ms=3000)
        self.assertEqual(trace.last_failure, 'wait')
        self.assertEqual(trace.events[0]['category'], 'timeout')
        self.assertNotIn('private', repr(trace.events))

    def test_bounded_and_fixed_vocabulary(self):
        trace = RpcTrace()
        for i in range(120):
            trace.call('create', lambda: None)
        self.assertEqual(len(trace.events), 96)
        self.assertTrue(trace.truncated)
        with self.assertRaises(ValueError):
            trace.call('student-private-token', lambda: None)


if __name__ == '__main__':
    unittest.main(verbosity=2)
