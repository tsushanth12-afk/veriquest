/* ==========================================================================
   VeriQuest API — Simulation & Verification Service
   Backend-only scored submissions; unscored local WASM practice.

   NON-NEGOTIABLE INVARIANTS:
   1. ZERO hardcoded per-challenge logic anywhere in the evaluation path.
   2. Scored submissions never fall back to local jobs or client awards.
   3. Unconfigured challenge IDs return EVALUATOR_NOT_CONFIGURED.
   4. No regex-on-source-text grading or synthetic passes.
   5. Run and reference fixtures always award zero XP and no completion.
   ========================================================================== */

import { SubmissionStatus, SubmissionResult } from '../types/submission.ts';
import { api } from './client.ts';
import { sessionSnapshot, requireCurrentSession } from './sessionBoundary';
import { requireApiData } from './requireApiData';
import type { EvaluatorResult } from '../evaluator/evaluator.ts';

export function normalizeBackendStatus(status: string): SubmissionStatus {
  const s = (status || '').toLowerCase();
  switch (s) {
    case 'queued':
      return 'QUEUED';
    case 'compiling':
      return 'COMPILING';
    case 'running':
    case 'running_tests':
      return 'RUNNING_TESTS';
    case 'accepted':
      return 'ACCEPTED';
    case 'wrong_answer':
      return 'WRONG_ANSWER';
    case 'compilation_error':
      return 'COMPILATION_ERROR';
    case 'simulation_error':
      return 'SIMULATION_ERROR';
    case 'evaluator_not_configured':
      return 'EVALUATOR_NOT_CONFIGURED';
    case 'timeout':
      return 'TIMEOUT';
    case 'resource_limit':
      return 'RESOURCE_LIMIT';
    case 'system_error':
      return 'SYSTEM_ERROR';
    case 'cancelled':
      return 'CANCELLED';
    default:
      console.warn(`[submissionApi] Unknown submission status received: "${status}". Resolving to SYSTEM_ERROR per fail-closed contract.`);
      return 'SYSTEM_ERROR';
  }
}

/**
 * Executes Verilog compilation and simulation via the real Icarus Verilog WebAssembly engine.
 * Dispatches to /api/internal/evaluate in browser, or invokes local evaluate() directly in Node.
 */
export async function runEvaluator(challengeId: string, code: string): Promise<EvaluatorResult> {
  const res = await fetch('/api/internal/evaluate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ challengeId, code }),
  });

  if (!res.ok) {
    if (res.status === 413) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(`SUBMISSION_TOO_LARGE: ${errData.message || 'Submission exceeds the 64 KB limit.'}`);
    }
    throw new Error(`Evaluator endpoint returned HTTP status ${res.status}`);
  }

  return (await res.json()) as EvaluatorResult;
}

export const submissionApi = {
  async submitSolution(challengeId: string, submittedCode: string): Promise<{ submissionId: string; isRemote: boolean }> {
    const snapshot = sessionSnapshot();
    if (!snapshot.identity) throw new Error('UNAUTHORIZED: Sign in to submit for scoring. Use Run for unscored practice.');
    const data = requireApiData(await api.submissions.submitSolution(challengeId, submittedCode));
    requireCurrentSession(snapshot);
    if (!data.submission_id) throw new Error('SYSTEM_ERROR: Missing backend submission ID.');
    return { submissionId: data.submission_id, isRemote: true };
  },
  async pollSubmissionStatus(submissionId: string, isRemote = true): Promise<SubmissionResult> {
    const snapshot = sessionSnapshot();
    if (!snapshot.identity || !isRemote) throw new Error('UNAUTHORIZED: Only backend submissions can be polled.');
    const data = requireApiData(await api.submissions.getSubmission(submissionId));
    requireCurrentSession(snapshot);
    return {
      submissionId, challengeId: String(data.challenge_id || ''),
      status: normalizeBackendStatus(String(data.status || '')),
      testsPassed: Number(data.tests_passed ?? 0), totalTests: Number(data.tests_total ?? 0),
      executionTimeMs: Number(data.runtime_ms ?? 0), simulationNanoseconds: Number(data.simulation_ns ?? 0),
      xpEarned: Number(data.xp_awarded ?? 0),
      compilerOutput: String(data.compiler_output || data.public_message || ''),
      submittedAt: String(data.submitted_at || ''),
    };
  },

  /**
   * Run test vectors for "Run" button (non-scoring).
   * Executes against real compiler/simulator with identical hardware truth.
   */
  async runPublicVectors(
    challengeId: string,
    submittedCode: string,
    _publicExamples?: Array<{ input: string; expectedOutput: string }>
  ): Promise<SubmissionResult> {
    const runId = `run_${Date.now()}`;
    try {
      const evalResult = await runEvaluator(challengeId, submittedCode);

      let finalStatus: SubmissionStatus = 'WRONG_ANSWER';
      if (evalResult.status === 'ACCEPTED') {
        finalStatus = 'ACCEPTED';
      } else if (evalResult.status === 'COMPILATION_ERROR') {
        finalStatus = 'COMPILATION_ERROR';
      } else if (evalResult.status === 'SIMULATION_ERROR') {
        finalStatus = 'SIMULATION_ERROR';
      } else if (evalResult.status === 'EVALUATOR_NOT_CONFIGURED') {
        finalStatus = 'EVALUATOR_NOT_CONFIGURED';
      } else if (evalResult.status === 'WRONG_ANSWER') {
        finalStatus = 'WRONG_ANSWER';
      } else {
        finalStatus = 'SYSTEM_ERROR';
      }

      return {
        submissionId: runId,
        challengeId,
        status: finalStatus,
        testsPassed: evalResult.testsPassed,
        totalTests: evalResult.totalTests,
        executionTimeMs: evalResult.executionTimeMs,
        simulationNanoseconds: evalResult.simulationNanoseconds,
        xpEarned: 0, // Non-scoring
        compilerOutput: evalResult.compilerOutput,
        failedVector: evalResult.failedVector,
        submittedAt: new Date().toISOString(),
      };
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      return {
        submissionId: runId,
        challengeId,
        status: 'SYSTEM_ERROR',
        testsPassed: 0,
        totalTests: 0,
        executionTimeMs: 20,
        simulationNanoseconds: 0,
        xpEarned: 0,
        compilerOutput: `[System Error] Run execution failed: ${msg}`,
        submittedAt: new Date().toISOString(),
      };
    }
  },

  /**
   * Dispatches a test matrix case to the server-side evaluator endpoint.
   * Client receives execution status/telemetry only; solution code never reaches client.
   */
  async runTestMatrixCase(
    challengeSlug: string,
    testId: string
  ): Promise<SubmissionResult> {
    const res = await fetch('/api/internal/evaluate-matrix', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ challengeId: challengeSlug, testId }),
    });

    if (!res.ok) {
      if (res.status === 413) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(`SUBMISSION_TOO_LARGE: ${errData.message || 'Submission exceeds the 64 KB limit.'}`);
      }
      throw new Error(`Matrix evaluation failed with HTTP ${res.status}`);
    }

    const data = await res.json();
    const normStatus = normalizeBackendStatus(data.status);
    return {
      submissionId: `matrix_${testId}_${Date.now()}`,
      challengeId: challengeSlug,
      status: normStatus,
      testsPassed: data.testsPassed ?? 0,
      totalTests: data.totalTests ?? 0,
      executionTimeMs: data.executionTimeMs ?? 0,
      simulationNanoseconds: data.simulationNanoseconds ?? 0,
      xpEarned: 0,
      compilerOutput: data.compilerOutput || '',
      failedVector: data.failedVector,
      submittedAt: new Date().toISOString(),
    };
  },
};

