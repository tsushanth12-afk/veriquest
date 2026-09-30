import { runBoundedWasm } from './boundedWasm.ts';
import { getTestbenchConfig } from './testbenchCatalog.ts';
import { prepareTestbench, validateStudentSource, parseTrustedVerdict, redactVerdict } from './verdictProtocol.ts';

export type EvaluatorStatus = 'ACCEPTED' | 'WRONG_ANSWER' | 'COMPILATION_ERROR' |
  'SIMULATION_ERROR' | 'EVALUATOR_NOT_CONFIGURED' | 'SYSTEM_ERROR';

export interface EvaluatorVectorFail {
  vectorIndex: number;
  input: string;
  expected: string;
  actual: string;
  passed: boolean;
}

export interface EvaluatorResult {
  status: EvaluatorStatus;
  success: boolean;
  testsPassed: number;
  totalTests: number;
  compilerOutput: string;
  failedVector?: EvaluatorVectorFail;
  executionTimeMs: number;
  simulationNanoseconds: number;
}

/** Production result boundary, exported so regressions exercise the real parser.
 * Exit codes originate from the runtime, never from student stdout.
 */
export function parseEvaluationResult(execution: {
  compileExitCode?: number | null; simulationExitCode?: number | null; output: string;
  outputComplete?: boolean; outputTruncated?: boolean;
}, nonce: string, total: number): EvaluatorResult {
  const captureValid = typeof execution?.output === 'string';
  const output = captureValid ? execution.output : '';
  const base = {
    success: false, testsPassed: 0, totalTests: total,
    compilerOutput: `[Untrusted simulator diagnostics]\n${redactVerdict(output, nonce)}`,
    executionTimeMs: 0, simulationNanoseconds: 0,
  };
  if (Number.isInteger(execution.compileExitCode) && execution.compileExitCode !== 0) {
    return { ...base, status: 'COMPILATION_ERROR' };
  }
  if (!captureValid || execution.outputComplete !== true || execution.outputTruncated !== false)
    return { ...base, status: 'SYSTEM_ERROR' };
  if (execution.compileExitCode !== 0) return { ...base, status: 'SYSTEM_ERROR' };
  if (execution.simulationExitCode !== 0) return { ...base, status: 'SIMULATION_ERROR' };
  const verdict = parseTrustedVerdict(output, nonce, total);
  if (!verdict) return { ...base, status: 'SYSTEM_ERROR',
    compilerOutput: `Missing, ambiguous, or inconsistent trusted grader result.\n${base.compilerOutput}` };
  return { ...base, status: verdict.status, success: verdict.status === 'ACCEPTED',
    testsPassed: verdict.passed, totalTests: verdict.total };
}

export async function evaluate(challengeId: string, studentCode: string): Promise<EvaluatorResult> {
  const start = Date.now();
  const config = getTestbenchConfig(challengeId);
  const failure = (status: EvaluatorStatus, message: string): EvaluatorResult => ({
    status, success: false, testsPassed: 0, totalTests: config?.totalVectors ?? 0,
    compilerOutput: message, executionTimeMs: Date.now() - start, simulationNanoseconds: 0,
  });
  if (!config) return failure('EVALUATOR_NOT_CONFIGURED', 'No verified testbench configured.');
  if (typeof studentCode !== 'string' || !studentCode.trim()) return failure('COMPILATION_ERROR', 'SOURCE_EMPTY');
  let nonce = '';
  try {
    const trusted = prepareTestbench(config.testbenchCode, config.totalVectors);
    nonce = trusted.nonce;
    try { validateStudentSource(studentCode, trusted.reserved); }
    catch (error) { return failure('COMPILATION_ERROR', String(error)); }

    // Separate stages: stdout cannot assert compilation succeeded. The run receives
    // only the compiled program, not source files. Capability checks remain mandatory
    // because an unrestricted VVP program can still inspect its own bytecode.
    const simulated = await runBoundedWasm(studentCode, trusted.code);
    const result = parseEvaluationResult({
      compileExitCode: simulated.compileExitCode,
      simulationExitCode: simulated.stage === 'run' ? simulated.simulationExitCode : null,
      output: simulated.output,
      outputComplete: simulated.outputComplete,
      outputTruncated: simulated.outputTruncated,
    }, nonce, trusted.total);
    return { ...result, executionTimeMs: Date.now() - start };
  } catch (error) {
    return failure('SYSTEM_ERROR', nonce ? redactVerdict(String(error), nonce) : String(error));
  }
}
