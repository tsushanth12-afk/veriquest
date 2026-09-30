"""Production worker verdict boundary. Never infer process success from stdout."""
from .verdict_protocol import parse_trusted_verdict


def parse_evaluation_result(execution_result: dict) -> dict:
    if not isinstance(execution_result, dict):
        execution_result = {}
    stdout = execution_result.get('stdout', '')
    stderr = execution_result.get('stderr', '')
    capture_valid = ('stdout' in execution_result and 'stderr' in execution_result
                     and isinstance(stdout, str) and isinstance(stderr, str))
    if not isinstance(stdout, str):
        stdout = ''
    if not isinstance(stderr, str):
        stderr = ''
    nonce = execution_result.get('verdict_nonce', '')
    output = stdout + '\n' + stderr
    if isinstance(nonce, str) and nonce:
        output = output.replace(nonce, '[grader-token]')
    result = dict(status='system_error', tests_total=0, tests_passed=0, tests_failed=0,
                  runtime_ms=0, simulation_ns=0, error_code='INVALID_TRUSTED_RESULT',
                  public_message='Missing, ambiguous, or inconsistent trusted grader result.',
                  compiler_output=_sanitize_output(output), counts_as_attempt=False)
    # These fields are supplied by the execution adapter, not parsed from HDL output.
    if execution_result.get('configuration_error'):
        return {**result, 'status': 'evaluator_not_configured', 'error_code': 'EVALUATOR_NOT_CONFIGURED'}
    if execution_result.get('source_error'):
        return {**result, 'status': 'compilation_error', 'error_code': 'COMPILATION_ERROR',
                'public_message': 'Unsupported HDL capability or invalid source.', 'counts_as_attempt': True}
    if execution_result.get('timed_out') is True:
        return {**result, 'status': 'timeout', 'error_code': 'TIMEOUT',
                'public_message': 'Execution timed out.', 'counts_as_attempt': True}
    compile_exit = execution_result.get('compile_exit_code')
    if type(compile_exit) is int and compile_exit != 0:
        return {**result, 'status': 'compilation_error', 'error_code': 'COMPILATION_ERROR',
                'public_message': 'Verilog compilation failed. See compiler diagnostics.', 'counts_as_attempt': True}
    if (not capture_valid or execution_result.get('timed_out') is not False
            or execution_result.get('output_complete') is not True
            or execution_result.get('output_truncated') is not False
            or type(compile_exit) is not int or compile_exit != 0
            or type(execution_result.get('simulation_exit_code')) is not int
            or execution_result['simulation_exit_code'] != 0
            or type(execution_result.get('exit_code')) is not int
            or execution_result['exit_code'] != 0):
        return result
    # Inspect both streams: conflicting authenticated records anywhere fail closed.
    verdict = parse_trusted_verdict(stdout + '\n' + stderr, nonce, execution_result.get('expected_total'))
    if not verdict:
        return result
    accepted = verdict['status'] == 'ACCEPTED'
    return {**result, 'status': 'accepted' if accepted else 'wrong_answer',
            'tests_total': verdict['total'], 'tests_passed': verdict['passed'],
            'tests_failed': verdict['failed'], 'counts_as_attempt': True,
            'error_code': None if accepted else 'WRONG_ANSWER',
            'public_message': f"{verdict['passed']}/{verdict['total']} tests passed."}


def _sanitize_output(text: str, max_len: int = 4000) -> str:
    return '\n'.join(line for line in text.split('\n')
                     if not any(secret in line for secret in
                                ('/workspace/testbench.v', '/workspace/run.sh', 'private.', 'challenge_secrets')))[:max_len]
