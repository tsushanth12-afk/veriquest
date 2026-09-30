"""Stdlib production-parser/adapter tests. No service, install, or DB required.

python -B tests/test_verdict_integrity.py
--bridge is used by the Node real-WASM cross-language regression, not production.
"""
import json
from pathlib import Path
import re
import sys
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from worker.execution.evaluator import parse_evaluation_result
from worker.execution.verdict_protocol import prepare_testbench, validate_student_source
from worker.execution.sandbox import DockerSandbox

CASES = json.loads((ROOT / 'tests/verdict_integrity_cases.json').read_text())
NONCE = 'a' * 64
CATALOG = (ROOT / 'src/evaluator/testbenchCatalog.ts').read_text()
BENCH = re.search(r'const AND_GATE_TESTBENCH = `([\s\S]*?)`;', CATALOG)[1].replace('\\`', '`')
CORRECT = 'module and_gate(input a,input b,output y); assign y=a&b; endmodule'


def execution(output='', **overrides):
    return dict(stdout=output, stderr='', verdict_nonce=NONCE, expected_total=4,
                compile_exit_code=0, simulation_exit_code=0, exit_code=0,
                timed_out=False, output_complete=True, output_truncated=False, **overrides)


class VerdictIntegrityTests(unittest.TestCase):
    def test_shared_parser_cases(self):
        for case in CASES['parser']:
            with self.subTest(case=case['name']):
                run = execution(case['output'].replace('{nonce}', NONCE))
                for key, value in case['execution'].items():
                    run[{'compileExitCode': 'compile_exit_code', 'simulationExitCode': 'simulation_exit_code'}[key]] = value
                expected = case['status'].lower()
                # Worker contract has no simulation_error; infrastructure failure is neutral.
                if expected == 'simulation_error':
                    expected = 'system_error'
                result = parse_evaluation_result(run)
                self.assertEqual(result['status'], expected)
                self.assertNotIn(NONCE, result['compiler_output'])
                if expected == 'system_error':
                    self.assertFalse(result['counts_as_attempt'])

    def test_worker_process_evidence(self):
        good = execution(f'VQ_TRUSTED:{NONCE}:ACCEPTED:4:4:0')
        for key, value in [('exit_code', 1), ('exit_code', None), ('exit_code', False),
                           ('compile_exit_code', False), ('simulation_exit_code', False),
                           ('output_truncated', True), ('output_truncated', None),
                           ('output_truncated', 'false'), ('output_complete', False),
                           ('output_complete', None), ('output_complete', 'true'),
                           ('timed_out', None), ('timed_out', 'false'),
                           ('verdict_nonce', ''), ('expected_total', None)]:
            with self.subTest(key=key, value=value):
                self.assertEqual(parse_evaluation_result({**good, key: value})['status'], 'system_error')
        self.assertEqual(parse_evaluation_result({**good, 'timed_out': True})['status'], 'timeout')
        self.assertEqual(parse_evaluation_result({**good, 'stderr': good['stdout']})['status'], 'system_error')
        for missing in ('output_complete', 'output_truncated', 'timed_out'):
            with self.subTest(missing=missing):
                self.assertEqual(parse_evaluation_result({k: v for k, v in good.items() if k != missing})['status'], 'system_error')
        self.assertEqual(parse_evaluation_result({**good, 'stdout': None})['status'], 'system_error')

    def test_capability_attacks(self):
        trusted = prepare_testbench(BENCH)
        validate_student_source(CORRECT, trusted['reserved'])
        for attack in CASES['capabilityAttacks']:
            with self.subTest(attack=attack['name']):
                with self.assertRaises(ValueError):
                    validate_student_source(f'module and_gate(input a,input b,output y); {attack["body"]} endmodule', trusted['reserved'])

    def test_fresh_token_and_template_fail_closed(self):
        first = prepare_testbench(BENCH)
        self.assertNotEqual(first['nonce'], prepare_testbench(BENCH)['nonce'])
        self.assertEqual(first['total'], 4)
        for bench in ['', ' ', BENCH.replace('TOTAL: 4', 'TOTAL: 0'),
                      BENCH.replace('VERIQUEST_STATUS: ACCEPTED', 'NO_VERDICT'),
                      BENCH + '$display("VERIQUEST_STATUS: ACCEPTED");']:
            with self.subTest(bench=bench[:20]), self.assertRaises(ValueError):
                prepare_testbench(bench)

    def test_seeded_testbench_profile(self):
        sql = (ROOT / 'supabase/migrations/002_seed_demo_challenge.sql').read_text()
        literal = re.search(r"E'(`timescale[^\r\n]*)',", sql)[1]
        seeded = literal.replace('\\n', '\n').replace("''", "'")
        prepared = prepare_testbench(seeded)
        self.assertEqual(prepared['total'], 4)
        self.assertIn('__vq_grader_passed', prepared['code'])

    def test_lexical_template_and_beginner_profile(self):
        for name, source in [
            ('line', '// module and_gate\n' + BENCH),
            ('block', '/* integer and_gate; */\n' + BENCH),
            ('string', BENCH.replace('module tb_and_gate;', 'module tb_and_gate; initial $display("module and_gate");')),
            ('similar', '// module and_gate_extra\n' + BENCH),
            ('parameterized', BENCH.replace('and_gate uut (', 'and_gate #(.P(1)) uut (').replace(
                '    task check_case;', '    wire y2; and_gate #(.P(1)) uut2 (.a(a), .b(b), .y(y2));\n    task check_case;')),
            ('formatted', ('// $display("VERIQUEST_STATUS: ACCEPTED");\n' + BENCH)
             .replace('$display("TOTAL: 4");', '$display ( "TOTAL: 4" ) ;')
             .replace('$display("VERIQUEST_STATUS: ACCEPTED");\n', '$display ( "VERIQUEST_STATUS: ACCEPTED" ) ;\n')),
        ]:
            with self.subTest(name=name):
                prepared = prepare_testbench(source)
                self.assertIn('and_gate', prepared['code'])
                self.assertNotIn('__vq_grader_and_gate', prepared['code'])
        safe = [
            '`timescale 1ns/1ps\n' + CORRECT,
            CORRECT.replace('assign y=', 'localparam real SCALE=1.0; assign y='),
            'module sub(input a,input b,output y); assign y=a&b; endmodule module and_gate(input a,input b,output y); sub u(.a,.b,.y); endmodule',
            CORRECT.replace('assign y=', 'initial $display("%d",$isunknown(a)); assign y='),
        ]
        reserved = prepare_testbench(BENCH)['reserved']
        for source in safe:
            with self.subTest(source=source[:40]):
                validate_student_source(source, reserved)
        for source in ['`include "private.v"\n' + CORRECT,
                       CORRECT.replace('assign y=', 'initial $fopen("/workspace/testbench.v"); assign y='),
                       CORRECT.replace('assign y=', 'assign y=tb_and_gate.__vq_grader_failed; assign unused=')]:
            with self.subTest(attack=source[:40]), self.assertRaises(ValueError):
                validate_student_source(source, reserved)

    def test_preflight_before_docker_and_fallback(self):
        sandbox = DockerSandbox.__new__(DockerSandbox)
        sandbox.client = Mock()
        for bench in ['', ' ', 'module empty; endmodule']:
            result = parse_evaluation_result(sandbox.execute(CORRECT, bench))
            self.assertEqual(result['status'], 'evaluator_not_configured')
        result = parse_evaluation_result(sandbox.execute('module and_gate; initial $dumpvars; endmodule', BENCH))
        self.assertEqual(result['status'], 'compilation_error')
        sandbox.client.containers.run.assert_not_called()
        sandbox.client = None
        self.assertEqual(parse_evaluation_result(sandbox.execute(CORRECT, BENCH))['status'], 'system_error')

    def test_adapter_with_mocked_docker_transport(self):
        # Executes the production adapter/parser, but NOT Docker or the shell script.
        # Real simulator/parser integration lives in verdict_integrity.test.mjs.
        for mode, expected in [('valid', 'accepted'), ('compile_failure', 'compilation_error'),
                               ('run_failure', 'system_error'), ('missing_stage', 'system_error'),
                               ('partial_logs', 'system_error'), ('truncated', 'system_error'),
                               ('duplicate', 'system_error'), ('wait_exception', 'system_error')]:
            with self.subTest(mode=mode):
                sandbox = DockerSandbox.__new__(DockerSandbox)
                sandbox.image = 'unused-mock-image'
                sandbox.timeout_s, sandbox.memory_mb, sandbox.cpu_limit, sandbox.pids_limit = 5, 256, 1, 64
                sandbox.client = Mock()
                container = Mock()
                container.wait.return_value = {'StatusCode': 0}
                if mode == 'wait_exception':
                    container.wait.side_effect = OSError('transport lost')

                def launched(**kwargs):
                    workspace = Path(next(iter(kwargs['volumes'])))
                    source = (workspace / 'testbench.v').read_text()
                    token = re.search(r'VQ_TRUSTED:([a-f0-9]{64}):', source)[1]
                    if mode != 'missing_stage':
                        (workspace / 'compile.exit').write_text('1' if mode == 'compile_failure' else '0')
                        (workspace / 'simulation.exit').write_text('1' if mode == 'run_failure' else '0')
                    record = f'VQ_TRUSTED:{token}:ACCEPTED:4:4:0\n'.encode()
                    if mode == 'duplicate':
                        record *= 2
                    if mode == 'truncated':
                        record += b'x' * 65536
                    def frames():
                        if mode == 'partial_logs':
                            raise OSError('lost logs')
                        yield (record, None)
                        if mode == 'truncated':
                            yield (b'x' * 65536, None)
                            raise AssertionError('Adapter read beyond budget')
                    container.attach.side_effect = lambda **_: frames()
                    return container

                sandbox.client.containers.run.side_effect = launched
                with patch.dict('os.environ', {'MAX_OUTPUT_BYTES': '65536'}):
                    result = parse_evaluation_result(sandbox.execute(CORRECT, BENCH))
                self.assertEqual(result['status'], expected)
                container.remove.assert_called_once_with(force=True)
                container.logs.assert_not_called()
                if mode == 'truncated':
                    container.kill.assert_called()

    def test_stream_budget_stops_before_unbounded_generator(self):
        sandbox = DockerSandbox.__new__(DockerSandbox)
        sandbox.image = 'unused-mock-image'
        sandbox.timeout_s, sandbox.memory_mb, sandbox.cpu_limit, sandbox.pids_limit = 5, 256, 1, 64
        sandbox.client = Mock()
        container = Mock()
        container.wait.return_value = {'StatusCode': 0}
        def launch(**kwargs):
            workspace = Path(next(iter(kwargs['volumes'])))
            token = re.search(r'VQ_TRUSTED:([a-f0-9]{64}):', (workspace / 'testbench.v').read_text())[1]
            (workspace / 'compile.exit').write_text('0')
            (workspace / 'simulation.exit').write_text('0')
            def frames():
                yield (f'VQ_TRUSTED:{token}:ACCEPTED:4:4:0\n'.encode(), None)
                yield (b'z' * 1000000, None)
                raise AssertionError('Full stream was consumed after overflow')
            container.attach.side_effect = lambda **_: frames()
            return container
        sandbox.client.containers.run.side_effect = launch
        with patch.dict('os.environ', {'MAX_OUTPUT_BYTES': '256'}):
            raw = sandbox.execute(CORRECT, BENCH)
        self.assertFalse(raw['output_complete'])
        self.assertTrue(raw['output_truncated'])
        self.assertLessEqual(len(raw['stdout'].encode()), 256)
        self.assertEqual(parse_evaluation_result(raw)['status'], 'system_error')
        container.kill.assert_called()
        container.logs.assert_not_called()


def bridge(request):
    if request['action'] == 'prepare':
        trusted = prepare_testbench(request['testbench'])
        validate_student_source(request['source'], trusted['reserved'])
        return {key: value for key, value in trusted.items() if key != 'reserved'}
    if request['action'] == 'parse':
        return parse_evaluation_result(request['execution'])
    if request['action'] == 'docker':
        sandbox = DockerSandbox()
        if not sandbox.client:
            raise RuntimeError('BLOCKED: Docker SDK/daemon unavailable; no container validation performed')
        sandbox.client.images.get(sandbox.image)  # Require prebuilt image; do not auto-pull.
        return parse_evaluation_result(sandbox.execute(request['source'], request['testbench']))
    raise ValueError('Unknown test bridge action')


if __name__ == '__main__':
    if '--bridge' in sys.argv:
        print(json.dumps(bridge(json.load(sys.stdin))))
    else:
        unittest.main(verbosity=2)
