/* ==========================================================================
   VeriQuest — Generic HDL Simulation & Verification Evaluator
   Grades student Verilog by compiling and simulating against real testbenches
   using @veriflow/iverilog-wasm.

   NON-NEGOTIABLE INVARIANTS:
   1. ZERO hardcoded per-challenge logic anywhere in the evaluation path.
   2. Every submission is graded by actually compiling and simulating via iverilog-wasm.
   3. Unconfigured challenge IDs return EVALUATOR_NOT_CONFIGURED.
   4. No silent passes: ACCEPTED requires a verified simulation pass from the runtime.
   ========================================================================== */

import { simulate } from '@veriflow/iverilog-wasm';
import { getTestbenchConfig } from './testbenchCatalog.ts';

export type EvaluatorStatus =
  | 'ACCEPTED'
  | 'FAILED'
  | 'COMPILATION_ERROR'
  | 'EVALUATOR_NOT_CONFIGURED'
  | 'SYSTEM_ERROR';

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

/**
 * Generic evaluation engine.
 * Looks up testbench config solely by challengeId/slug, stages student code,
 * executes iverilog compilation and VVP simulation, and parses assertion vectors.
 */
export async function evaluate(
  challengeId: string,
  studentCode: string
): Promise<EvaluatorResult> {
  const startTime = Date.now();

  // 1. Resolve configuration from catalog
  const config = getTestbenchConfig(challengeId);
  if (!config) {
    return {
      status: 'EVALUATOR_NOT_CONFIGURED',
      success: false,
      testsPassed: 0,
      totalTests: 0,
      compilerOutput: `[Evaluator Error] EVALUATOR_NOT_CONFIGURED: No verified testbench catalog entry found for challenge identifier "${challengeId}".\nAutomatic pass-by-default is strictly prohibited.`,
      executionTimeMs: 0,
      simulationNanoseconds: 0,
    };
  }

  // 1b. Source-provenance guard: Check that student code is non-empty
  if (!studentCode || typeof studentCode !== 'string' || studentCode.trim().length === 0) {
    return {
      status: 'COMPILATION_ERROR',
      success: false,
      testsPassed: 0,
      totalTests: config.totalVectors,
      compilerOutput: `[Evaluator Error] SOURCE_EMPTY: No student source code provided for compilation.\nProvenance check failed: cannot submit empty payload to compiler.`,
      executionTimeMs: 0,
      simulationNanoseconds: 0,
    };
  }

  // 2. Execute compilation & simulation via real Icarus Verilog WebAssembly
  try {
    const simResult = await simulate({
      files: [
        { path: 'solution.v', data: studentCode },
        { path: 'testbench.v', data: config.testbenchCode },
      ],
      sources: ['testbench.v', 'solution.v'],
      generation: '2012',
      timeoutMs: 5000,
    });

    const elapsedMs = Math.max(Date.now() - startTime, 15);

    // 3. Handle compilation failures (syntax errors, missing ports, unknown modules)
    if (!simResult.success && simResult.stage === 'compile') {
      const errOutput = simResult.combinedOutput || simResult.stderr || 'Compilation error.';
      return {
        status: 'COMPILATION_ERROR',
        success: false,
        testsPassed: 0,
        totalTests: config.totalVectors,
        compilerOutput: `[Icarus Verilog 12.0] Compilation failed:\n${errOutput}`,
        executionTimeMs: elapsedMs,
        simulationNanoseconds: 0,
      };
    }

    const output = simResult.combinedOutput || simResult.stdout || '';

    // 4. Parse simulation output and testbench assertion messages
    const lines = output.split('\n');
    let passedCount = 0;
    let failedCount = 0;
    let firstFailVector: EvaluatorVectorFail | undefined;

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();

      if (line.startsWith('TEST CASE PASS:')) {
        passedCount++;
      } else if (line.startsWith('TEST CASE FAIL:')) {
        failedCount++;
        if (!firstFailVector) {
          // Parse format: "TEST CASE FAIL: <inputs> -> <actual> (expected <expected>)"
          const details = line.replace('TEST CASE FAIL:', '').trim();
          const arrowSplit = details.split('->');
          const inputPart = arrowSplit[0]?.trim() || `Test vector #${failedCount}`;
          const rightPart = arrowSplit[1]?.trim() || '';

          let expected = 'expected output';
          let actual = rightPart;
          const expMatch = rightPart.match(/\(expected\s+([^)]+)\)/);
          if (expMatch) {
            expected = expMatch[1].trim();
            actual = rightPart.replace(expMatch[0], '').trim();
          }

          firstFailVector = {
            vectorIndex: failedCount + passedCount,
            input: inputPart,
            expected,
            actual: actual || 'mismatch',
            passed: false,
          };
        }
      }
    }

    // Parse summary block if emitted by testbench
    const summaryTotalMatch = output.match(/TOTAL:\s*(\d+)/);
    const summaryPassedMatch = output.match(/PASSED:\s*(\d+)/);
    const summaryFailedMatch = output.match(/FAILED:\s*(\d+)/);

    const totalTests = summaryTotalMatch ? parseInt(summaryTotalMatch[1], 10) : config.totalVectors;
    const finalPassed = summaryPassedMatch ? parseInt(summaryPassedMatch[1], 10) : passedCount;
    const finalFailed = summaryFailedMatch ? parseInt(summaryFailedMatch[1], 10) : failedCount;

    // 5. Authoritative Acceptance Verification
    const isAccepted =
      output.includes('VERIQUEST_STATUS: ACCEPTED') &&
      finalFailed === 0 &&
      finalPassed === totalTests &&
      totalTests > 0;

    if (isAccepted) {
      return {
        status: 'ACCEPTED',
        success: true,
        testsPassed: totalTests,
        totalTests,
        compilerOutput: `[Icarus Verilog 12.0] Compilation successful.\n[Testbench Simulation]\n${output}`,
        executionTimeMs: elapsedMs,
        simulationNanoseconds: totalTests * 10,
      };
    }

    // 6. Failed Verification / Wrong Answer
    const fallbackFail: EvaluatorVectorFail = {
      vectorIndex: 1,
      input: 'Initial stimulus vector',
      expected: 'Matching signal value',
      actual: 'Signal mismatch or assertion failure',
      passed: false,
    };

    return {
      status: 'FAILED',
      success: false,
      testsPassed: finalPassed,
      totalTests,
      compilerOutput: `[Simulation Diagnostics]\n${output}`,
      failedVector: firstFailVector || fallbackFail,
      executionTimeMs: elapsedMs,
      simulationNanoseconds: totalTests * 10,
    };
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : String(err);
    return {
      status: 'SYSTEM_ERROR',
      success: false,
      testsPassed: 0,
      totalTests: config.totalVectors,
      compilerOutput: `[System Error] Evaluator execution failed unexpectedly:\n${errorMsg}`,
      executionTimeMs: Date.now() - startTime,
      simulationNanoseconds: 0,
    };
  }
}
