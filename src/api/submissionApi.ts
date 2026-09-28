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

import { SubmissionStatus, SubmissionResult } from '../types/submission.ts';
import { api } from './client.ts';
import { MOCK_CHALLENGES } from './mockData.ts';
import type { EvaluatorResult } from '../evaluator/evaluator.ts';

interface ActiveLocalJob {
  submissionId: string;
  challengeId: string;
  code: string;
  startedAt: number;
}

const localJobs = new Map<string, ActiveLocalJob>();

/* ==========================================================================
   TEMPORARY CLIENT-SIDE TAMPER RESISTANCE STOPGAP (F-04)
   
   IMPORTANT NOTICE:
   This is explicitly a temporary client-side mitigation designed to deter
   casual manipulation (e.g. single-click localStorage clearing or manual JSON edits).
   It is NOT server-authoritative and CANNOT make client state secure against
   a determined user with browser DevTools.
   
   Permanent resolution requires the real backend's database-transaction-based
   XP idempotency and authenticated user records (backend/app/gamification/xp.py).
   ========================================================================== */

const COMPLETED_SET_KEY = 'veriquest_completed_challenge_ids';
const INTEGRITY_LEDGER_KEY = 'veriquest_ledger_integrity';
const SESSION_LEDGER_KEY = 'veriquest_session_ledger';

function computeLedgerChecksum(ids: string[]): string {
  const str = `v1:${[...ids].sort().join(',')}:veriquest_stopgap_salt`;
  let hash = 0x811c9dc5;
  for (let i = 0; i < str.length; i++) {
    hash ^= str.charCodeAt(i);
    hash = Math.imul(hash, 0x01000193);
  }
  return (hash >>> 0).toString(16);
}

const inMemoryCompletedSet = new Set<string>();

export function getCompletedChallenges(): Set<string> {
  const knownCompleted = new Set<string>(inMemoryCompletedSet);

  if (typeof window === 'undefined') {
    return knownCompleted;
  }

  let localIds: string[] | null = null;
  let localChecksumValid = false;
  let sessionIds: string[] | null = null;

  // 1. Read redundant session tier (isolated from localStorage clear)
  try {
    const rawSession = window.sessionStorage?.getItem(SESSION_LEDGER_KEY);
    if (rawSession) {
      const parsed = JSON.parse(rawSession);
      if (Array.isArray(parsed)) {
        sessionIds = parsed;
        sessionIds.forEach((id) => knownCompleted.add(id));
      }
    }
  } catch {
    // sessionStorage read failed
  }

  // 2. Read primary localStorage tier + verify integrity checksum
  try {
    const rawLocal = window.localStorage?.getItem(COMPLETED_SET_KEY);
    const rawChecksum = window.localStorage?.getItem(INTEGRITY_LEDGER_KEY);

    if (rawLocal) {
      const parsed = JSON.parse(rawLocal);
      if (Array.isArray(parsed)) {
        localIds = parsed;
        const expectedChecksum = computeLedgerChecksum(parsed);
        localChecksumValid = (rawChecksum === expectedChecksum);

        if (localChecksumValid) {
          parsed.forEach((id) => knownCompleted.add(id));
        } else {
          // MODIFICATION TAMPERING: Payload modified without valid checksum!
          console.warn('[F-04 Stopgap] Modification tampering detected in localStorage! Restoring from secure session tier.');
        }
      }
    }
  } catch {
    // localStorage read failed
  }

  // 3. Detect Deletion Tampering: localStorage was cleared, but sessionStorage / heap has records
  const wasLocalStorageCleared = localIds === null && (sessionIds !== null && sessionIds.length > 0);
  const wasTampered = !localChecksumValid && localIds !== null;

  if (wasLocalStorageCleared || wasTampered) {
    // Re-sync and restore integrity back to localStorage from validated session/memory
    try {
      const restoredList = [...knownCompleted];
      const newChecksum = computeLedgerChecksum(restoredList);
      window.localStorage?.setItem(COMPLETED_SET_KEY, JSON.stringify(restoredList));
      window.localStorage?.setItem(INTEGRITY_LEDGER_KEY, newChecksum);
      window.sessionStorage?.setItem(SESSION_LEDGER_KEY, JSON.stringify(restoredList));
    } catch {
      // Restore write failed
    }
  }

  return knownCompleted;
}

export function recordChallengeCompleted(challengeId: string): void {
  const set = getCompletedChallenges();
  set.add(challengeId);
  inMemoryCompletedSet.add(challengeId);

  if (typeof window !== 'undefined') {
    const list = [...set];
    const checksum = computeLedgerChecksum(list);

    try {
      window.localStorage?.setItem(COMPLETED_SET_KEY, JSON.stringify(list));
      window.localStorage?.setItem(INTEGRITY_LEDGER_KEY, checksum);
    } catch {
      // localStorage write failed
    }

    try {
      window.sessionStorage?.setItem(SESSION_LEDGER_KEY, JSON.stringify(list));
    } catch {
      // sessionStorage write failed
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
      let finalStatus: SubmissionStatus = 'WRONG_ANSWER';

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
      } else if (evalResult.status === 'SIMULATION_ERROR') {
        finalStatus = 'SIMULATION_ERROR';
      } else if (evalResult.status === 'EVALUATOR_NOT_CONFIGURED') {
        finalStatus = 'EVALUATOR_NOT_CONFIGURED';
        xpEarned = 0;
      } else if (evalResult.status === 'WRONG_ANSWER') {
        finalStatus = 'WRONG_ANSWER';
      } else {
        finalStatus = 'SYSTEM_ERROR';
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
    const challenge = MOCK_CHALLENGES.find(
      (c) => c.id === challengeSlug || c.slug === challengeSlug
    );

    let xpEarned = 0;
    const normStatus = normalizeBackendStatus(data.status);
    if (normStatus === 'ACCEPTED') {
      const alreadyCompleted = getCompletedChallenges().has(challengeSlug);
      if (alreadyCompleted || testId === 'I') {
        xpEarned = 0;
      } else {
        xpEarned = challenge?.xp || 40;
        recordChallengeCompleted(challengeSlug);
      }
    }

    return {
      submissionId: `matrix_${testId}_${Date.now()}`,
      challengeId: challengeSlug,
      status: normStatus,
      testsPassed: data.testsPassed ?? 0,
      totalTests: data.totalTests ?? 0,
      executionTimeMs: data.executionTimeMs ?? 0,
      simulationNanoseconds: data.simulationNanoseconds ?? 0,
      xpEarned,
      compilerOutput: data.compilerOutput || '',
      failedVector: data.failedVector,
      submittedAt: new Date().toISOString(),
    };
  },
};

