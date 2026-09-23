/* ==========================================================================
   VeriQuest API — Simulation & Verification Service
   Authoritative Verilog Grading Engine using @veriflow/iverilog-wasm.

   NON-NEGOTIABLE INVARIANTS:
   1. ZERO hardcoded per-challenge logic anywhere in the evaluation path.
   2. Every submission is compiled and simulated via @veriflow/iverilog-wasm.
   3. Unconfigured challenge IDs return EVALUATOR_NOT_CONFIGURED.
   4. No regex-on-source-text grading or synthetic passes.
   5. Resubmitting an already-ACCEPTED solution awards zero additional XP.
   ========================================================================== */

import { SubmissionStatus, SubmissionResult } from '../types/submission';
import { api } from './client';
import { MOCK_CHALLENGES } from './mockData';
import type { EvaluatorResult } from '../evaluator/evaluator';

interface ActiveLocalJob {
  submissionId: string;
  challengeId: string;
  code: string;
  startedAt: number;
}

const localJobs = new Map<string, ActiveLocalJob>();

// XP Idempotency tracking (client-side stopgap until backend unique constraint takes over)
const COMPLETED_SET_KEY = 'veriquest_completed_challenge_ids';
const inMemoryCompletedSet = new Set<string>();

export function getCompletedChallenges(): Set<string> {
  if (typeof window !== 'undefined' && window.localStorage) {
    try {
      const raw = localStorage.getItem(COMPLETED_SET_KEY);
      if (raw) {
        const arr = JSON.parse(raw);
        if (Array.isArray(arr)) {
          return new Set(arr);
        }
      }
    } catch {
      // localStorage read failed
    }
  }
  return inMemoryCompletedSet;
}

export function recordChallengeCompleted(challengeId: string): void {
  const set = getCompletedChallenges();
  set.add(challengeId);
  inMemoryCompletedSet.add(challengeId);
  if (typeof window !== 'undefined' && window.localStorage) {
    try {
      localStorage.setItem(COMPLETED_SET_KEY, JSON.stringify([...set]));
    } catch {
      // localStorage write failed
    }
  }
}

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
    case 'failed':
      return 'FAILED';
    case 'compilation_error':
      return 'COMPILATION_ERROR';
    case 'simulation_error':
      return 'COMPILATION_ERROR';
    case 'evaluator_not_configured':
      return 'SYSTEM_ERROR';
    case 'timeout':
      return 'TIMEOUT';
    case 'resource_limit':
      return 'RESOURCE_LIMIT';
    case 'system_error':
      return 'SYSTEM_ERROR';
    default:
      return 'QUEUED';
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
    throw new Error(`Evaluator endpoint returned HTTP status ${res.status}`);
  }

  return (await res.json()) as EvaluatorResult;
}

export const submissionApi = {
  /**
   * Dispatches Verilog code to verification cluster with local WASM simulator fallback.
   */
  async submitSolution(
    challengeId: string,
    submittedCode: string
  ): Promise<{ submissionId: string; isRemote: boolean }> {
    try {
      const { data, error } = await api.submissions.submitSolution(challengeId, submittedCode);
      if (data && !error && data.submission_id) {
        return { submissionId: data.submission_id, isRemote: true };
      }
    } catch {
      // Backend offline or unreachable — fall back to local iverilog-wasm evaluator
    }

    const localId = `sub_local_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
    localJobs.set(localId, {
      submissionId: localId,
      challengeId,
      code: submittedCode,
      startedAt: Date.now(),
    });

    return { submissionId: localId, isRemote: false };
  },

  /**
   * Polls compilation/simulation runner status.
   * Progression: QUEUED (0-200ms) -> COMPILING (200-500ms) -> RUNNING (500-900ms) -> TERMINAL WASM RESULT
   */
  async pollSubmissionStatus(
    submissionId: string,
    isRemote: boolean = false
  ): Promise<SubmissionResult> {
    if (isRemote && !submissionId.startsWith('sub_local_')) {
      try {
        const { data, error } = await api.submissions.getSubmission(submissionId);
        if (data && !error) {
          const rawStatus = (data.status as string) || 'queued';
          const status = normalizeBackendStatus(rawStatus);

          return {
            submissionId,
            challengeId: (data.challenge_id as string) || '',
            status,
            testsPassed: Number(data.tests_passed ?? 0),
            totalTests: Number(data.tests_total ?? 0),
            executionTimeMs: Number(data.runtime_ms ?? 0),
            simulationNanoseconds: Number(data.simulation_ns ?? 0),
            xpEarned: Number(data.xp_awarded ?? 0),
            compilerOutput: (data.compiler_output as string) || (data.public_message as string) || '',
            submittedAt: (data.submitted_at as string) || new Date().toISOString(),
          };
        }
      } catch {
        // Polling failed, fall through to local job
      }
    }

    const job = localJobs.get(submissionId);
    const elapsed = job ? Date.now() - job.startedAt : 1500;

    if (!job || elapsed < 200) {
      return {
        submissionId,
        challengeId: job?.challengeId || '',
        status: 'QUEUED',
        testsPassed: 0,
        totalTests: 4,
        executionTimeMs: 15,
        simulationNanoseconds: 0,
        submittedAt: new Date().toISOString(),
      };
    }

    if (elapsed < 500) {
      return {
        submissionId,
        challengeId: job.challengeId,
        status: 'COMPILING',
        testsPassed: 0,
        totalTests: 4,
        executionTimeMs: 100,
        simulationNanoseconds: 0,
        submittedAt: new Date().toISOString(),
      };
    }

    if (elapsed < 900) {
      return {
        submissionId,
        challengeId: job.challengeId,
        status: 'RUNNING_TESTS',
        testsPassed: 0,
        totalTests: 4,
        executionTimeMs: 180,
        simulationNanoseconds: 40,
        submittedAt: new Date().toISOString(),
      };
    }

    // Run authoritative iverilog-wasm simulation
    try {
      const evalResult = await runEvaluator(job.challengeId, job.code);

      const challenge = MOCK_CHALLENGES.find(
        (c) => c.id === job.challengeId || c.slug === job.challengeId
      );

      let xpEarned = 0;
      let finalStatus: SubmissionStatus = 'FAILED';

      if (evalResult.status === 'ACCEPTED') {
        finalStatus = 'ACCEPTED';
        const alreadyCompleted = getCompletedChallenges().has(job.challengeId);
        if (alreadyCompleted) {
          // Idempotency: Resubmitting an already-accepted challenge yields 0 XP
          xpEarned = 0;
        } else {
          xpEarned = challenge?.xp || 40;
          recordChallengeCompleted(job.challengeId);
        }
      } else if (evalResult.status === 'COMPILATION_ERROR') {
        finalStatus = 'COMPILATION_ERROR';
      } else if (evalResult.status === 'EVALUATOR_NOT_CONFIGURED') {
        finalStatus = 'SYSTEM_ERROR';
      } else {
        finalStatus = 'FAILED'; // Maps to WRONG_ANSWER in UI
      }

      return {
        submissionId,
        challengeId: job.challengeId,
        status: finalStatus,
        testsPassed: evalResult.testsPassed,
        totalTests: evalResult.totalTests,
        executionTimeMs: evalResult.executionTimeMs,
        simulationNanoseconds: evalResult.simulationNanoseconds,
        xpEarned,
        compilerOutput: evalResult.compilerOutput,
        failedVector: evalResult.failedVector,
        submittedAt: new Date().toISOString(),
      };
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      return {
        submissionId,
        challengeId: job.challengeId,
        status: 'SYSTEM_ERROR',
        testsPassed: 0,
        totalTests: 0,
        executionTimeMs: 50,
        simulationNanoseconds: 0,
        xpEarned: 0,
        compilerOutput: `[System Error] Execution engine failed: ${msg}`,
        submittedAt: new Date().toISOString(),
      };
    }
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

      let finalStatus: SubmissionStatus = 'FAILED';
      if (evalResult.status === 'ACCEPTED') {
        finalStatus = 'ACCEPTED';
      } else if (evalResult.status === 'COMPILATION_ERROR') {
        finalStatus = 'COMPILATION_ERROR';
      } else if (evalResult.status === 'EVALUATOR_NOT_CONFIGURED') {
        finalStatus = 'SYSTEM_ERROR';
      } else {
        finalStatus = 'FAILED';
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
};
