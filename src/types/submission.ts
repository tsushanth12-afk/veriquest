/* ==========================================================================
   VeriQuest Types — Execution Lifecycle & Submission Status
   ========================================================================== */

export type SubmissionStatus = 
  | 'IDLE'
  | 'QUEUED'
  | 'COMPILING'
  | 'RUNNING'
  | 'RUNNING_TESTS'
  | 'ACCEPTED'
  | 'WRONG_ANSWER'
  | 'FAILED'
  | 'COMPILATION_ERROR'
  | 'SIMULATION_ERROR'
  | 'TIMEOUT'
  | 'RESOURCE_LIMIT'
  | 'SYSTEM_ERROR'
  | 'CANCELLED';

export interface TestVectorSummary {
  vectorIndex: number;
  input: string;
  expected: string;
  actual: string;
  passed: boolean;
}

export interface SubmissionResult {
  submissionId: string;
  challengeId: string;
  status: SubmissionStatus;
  testsPassed: number;
  totalTests: number;
  executionTimeMs: number;
  simulationNanoseconds: number;
  xpEarned?: number;
  compilerOutput?: string;
  failedVector?: TestVectorSummary;
  submittedAt: string;
}

export interface RecentSubmissionSummary {
  id: string;
  challengeId: string;
  challengeTitle: string;
  status: 'ACCEPTED' | 'WRONG_ANSWER' | 'FAILED' | 'COMPILATION_ERROR';
  testsPassed: number;
  totalTests: number;
  xp: number;
  timeAgo: string;
  timestamp: string;
}
