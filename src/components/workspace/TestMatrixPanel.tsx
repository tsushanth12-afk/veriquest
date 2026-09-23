/* ==========================================================================
   VeriQuest — Automated Test Matrix Runner UI Panel
   Runs the mandatory 9-case test matrix (A through I) against the active challenge
   via the live UI submission pipeline with real compiler diagnostics.
   ========================================================================== */

import React, { useState } from 'react';
import { Play, CheckCircle2, XCircle, AlertTriangle, ShieldCheck } from 'lucide-react';
import { submissionApi } from '../../api/submissionApi';
import { SubmissionResult } from '../../types/submission';

import { getTestbenchConfig, TestCaseDef } from '../../evaluator/testbenchCatalog';
export type { TestCaseDef };

export interface TestResultItem {
  testId: string;
  title: string;
  expectedStatus: string;
  actualStatus: string;
  passed: boolean;
  compilerOutput: string;
  testsPassed: number;
  totalTests: number;
  xpEarned?: number;
  durationMs: number;
}

interface TestMatrixPanelProps {
  challengeSlug: string;
  onLoadCode: (code: string) => void;
  onSetResult: (res: SubmissionResult) => void;
}

export const TestMatrixPanel: React.FC<TestMatrixPanelProps> = ({
  challengeSlug,
  onLoadCode,
  onSetResult,
}) => {
  const [isRunningAll, setIsRunningAll] = useState(false);
  const [currentRunningId, setCurrentRunningId] = useState<string | null>(null);
  const [results, setResults] = useState<Record<string, TestResultItem>>({});

  const config = getTestbenchConfig(challengeSlug);
  const testList = config?.testMatrix || [];

  if (testList.length === 0) {
    return (
      <div
        style={{
          padding: '30px 20px',
          textAlign: 'center',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '12px',
          color: 'var(--text-muted)',
        }}
      >
        <AlertTriangle size={28} style={{ color: 'var(--accent)' }} />
        <h4 style={{ margin: 0, fontSize: '15px', color: 'var(--text-main)' }}>
          No Verification Test Matrix Configured
        </h4>
        <p style={{ margin: 0, fontSize: '13px', maxWidth: '320px', lineHeight: 1.5 }}>
          The active challenge (<code>{challengeSlug}</code>) does not have a 9-case test matrix registered in the catalog.
        </p>
        <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono)' }}>
          Supported challenges: and-gate-demo, mux-2to1, 4-bit-counter, xor-gate
        </span>
      </div>
    );
  }

  const pollUntilTerminal = async (submissionId: string, isRemote: boolean = false): Promise<SubmissionResult> => {
    const terminal = new Set(['ACCEPTED', 'FAILED', 'COMPILATION_ERROR', 'SYSTEM_ERROR', 'TIMEOUT']);
    const start = Date.now();
    while (Date.now() - start < 10000) {
      const res = await submissionApi.pollSubmissionStatus(submissionId, isRemote);
      if (terminal.has(res.status)) {
        return res;
      }
      await new Promise((r) => setTimeout(r, 250));
    }
    return await submissionApi.pollSubmissionStatus(submissionId, isRemote);
  };

  const executeSingleTest = async (test: TestCaseDef): Promise<TestResultItem> => {
    const t0 = Date.now();

    if (test.id === 'G' && test.secondaryCode) {
      // Step G: First submit correct, then submit broken
      const sub1 = await submissionApi.submitSolution(challengeSlug, test.code);
      await pollUntilTerminal(sub1.submissionId, false);

      // Now submit broken
      const sub2 = await submissionApi.submitSolution(challengeSlug, test.secondaryCode);
      const res = await pollUntilTerminal(sub2.submissionId, false);
      onSetResult(res);

      const isPass = res.status === test.expectedStatus;
      return {
        testId: test.id,
        title: test.title,
        expectedStatus: test.expectedStatus,
        actualStatus: res.status,
        passed: isPass,
        compilerOutput: res.compilerOutput || '',
        testsPassed: res.testsPassed,
        totalTests: res.totalTests,
        xpEarned: res.xpEarned,
        durationMs: Date.now() - t0,
      };
    }

    onLoadCode(test.code);
    const { submissionId, isRemote } = await submissionApi.submitSolution(challengeSlug, test.code);
    const res = await pollUntilTerminal(submissionId, isRemote);
    onSetResult(res);

    let isPass = res.status === test.expectedStatus;
    if (test.id === 'I') {
      // For Test I, must be ACCEPTED AND xpEarned must be 0
      isPass = res.status === 'ACCEPTED' && (res.xpEarned === 0 || res.xpEarned === undefined);
    }

    return {
      testId: test.id,
      title: test.title,
      expectedStatus: test.expectedStatus,
      actualStatus: res.status,
      passed: isPass,
      compilerOutput: res.compilerOutput || '',
      testsPassed: res.testsPassed,
      totalTests: res.totalTests,
      xpEarned: res.xpEarned,
      durationMs: Date.now() - t0,
    };
  };

  const handleRunSingle = async (test: TestCaseDef) => {
    setCurrentRunningId(test.id);
    try {
      const res = await executeSingleTest(test);
      setResults((prev) => ({ ...prev, [test.id]: res }));
    } finally {
      setCurrentRunningId(null);
    }
  };

  const handleRunAll = async () => {
    setIsRunningAll(true);
    const newResults: Record<string, TestResultItem> = {};

    try {
      for (const test of testList) {
        setCurrentRunningId(test.id);
        const item = await executeSingleTest(test);
        newResults[test.id] = item;
        setResults({ ...newResults });
        // Expose to window for automated assertion inspection
        if (typeof window !== 'undefined') {
          (window as any).__testMatrixResults = {
            ...(window as any).__testMatrixResults,
            [`${challengeSlug}_${test.id}`]: item,
          };
        }
        await new Promise((r) => setTimeout(r, 400));
      }
    } finally {
      setIsRunningAll(false);
      setCurrentRunningId(null);
    }
  };

  const passedTotal = Object.values(results).filter((r) => r.passed).length;
  const isAllComplete = Object.keys(results).length === testList.length;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', padding: '16px 20px', height: '100%', overflowY: 'auto' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '10px' }}>
        <div>
          <h3 style={{ margin: 0, fontSize: '14px', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '6px' }}>
            <ShieldCheck size={16} style={{ color: 'var(--accent)' }} />
            <span>Grading Engine Test Matrix (Cases A – I)</span>
          </h3>
          <p style={{ margin: '2px 0 0', fontSize: '11px', color: 'var(--text-muted)' }}>
            Authoritative verification against @veriflow/iverilog-wasm testbench.
          </p>
        </div>

        <button
          onClick={handleRunAll}
          disabled={isRunningAll || !!currentRunningId}
          className="neu-btn neu-btn-primary"
          style={{ padding: '6px 14px', fontSize: '12px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px' }}
        >
          <Play size={12} />
          <span>{isRunningAll ? 'Running Matrix...' : 'Run All 9 Cases'}</span>
        </button>
      </div>

      {/* Progress / Status banner */}
      {isAllComplete && (
        <div
          style={{
            padding: '8px 12px',
            borderRadius: 'var(--radius-sm)',
            backgroundColor: passedTotal === testList.length ? 'rgba(52, 168, 83, 0.15)' : 'rgba(234, 67, 53, 0.15)',
            border: `1px solid ${passedTotal === testList.length ? 'rgba(52, 168, 83, 0.4)' : 'rgba(234, 67, 53, 0.4)'}`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: '12px',
            fontWeight: 600,
          }}
        >
          <span>Matrix Status: {passedTotal} / {testList.length} PASSED</span>
          <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono)' }}>
            {passedTotal === testList.length ? '✓ ALL PASS' : '⚠ FAILURES DETECTED'}
          </span>
        </div>
      )}

      {/* Test List Table */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
        {testList.map((test) => {
          const res = results[test.id];
          const isCurrent = currentRunningId === test.id;

          return (
            <div
              key={test.id}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '8px 10px',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border-subtle)',
                backgroundColor: isCurrent ? 'var(--highlight)' : 'transparent',
                fontSize: '12px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: 1, minWidth: 0 }}>
                <span
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    width: '20px',
                    height: '20px',
                    borderRadius: '50%',
                    backgroundColor: 'var(--border-subtle)',
                    fontSize: '11px',
                    fontWeight: 700,
                    fontFamily: 'var(--font-mono)',
                  }}
                >
                  {test.id}
                </span>
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <span style={{ fontWeight: 600, color: 'var(--text-main)' }}>{test.title}</span>
                  <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                    Expected: {test.expectedStatus}
                    {res && ` → Actual: ${res.actualStatus} (${res.testsPassed}/${res.totalTests}) [${res.durationMs}ms]`}
                  </span>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                {res ? (
                  res.passed ? (
                    <span style={{ color: 'var(--color-success, #2e7d32)', display: 'flex', alignItems: 'center', gap: '4px', fontSize: '11px', fontWeight: 700 }}>
                      <CheckCircle2 size={14} />
                      <span>PASS</span>
                    </span>
                  ) : (
                    <span style={{ color: 'var(--color-danger, #c62828)', display: 'flex', alignItems: 'center', gap: '4px', fontSize: '11px', fontWeight: 700 }}>
                      <XCircle size={14} />
                      <span>FAIL</span>
                    </span>
                  )
                ) : isCurrent ? (
                  <span style={{ color: 'var(--accent)', fontSize: '11px', fontWeight: 600 }}>Executing...</span>
                ) : (
                  <button
                    onClick={() => handleRunSingle(test)}
                    disabled={isRunningAll || !!currentRunningId}
                    className="neu-btn"
                    style={{ padding: '3px 8px', fontSize: '10px' }}
                  >
                    Run
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
