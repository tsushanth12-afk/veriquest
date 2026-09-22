/* ==========================================================================
   VeriQuest Workspace — Test Results & Execution Telemetry Panel (LeetCode Style)
   ========================================================================== */

import React, { useState } from 'react';
import { SubmissionStatus, SubmissionResult } from '../../types/submission';
import {
  CheckCircle2,
  XCircle,
  Terminal,
  ArrowRight,
  Loader2,
  Play,
  FileCheck,
  AlertTriangle,
  Clock,
} from 'lucide-react';

interface SubmissionPanelProps {
  status: SubmissionStatus;
  result: SubmissionResult | null;
  onNextChallenge?: () => void;
  examples?: Array<{ input: string; expectedOutput: string; explanation?: string }>;
}

export const SubmissionPanel: React.FC<SubmissionPanelProps> = ({
  status,
  result,
  onNextChallenge,
  examples = [],
}) => {
  const [activeTab, setActiveTab] = useState<'testcase' | 'result'>('result');
  const [selectedCase, setSelectedCase] = useState<number>(0);

  const displayCases =
    examples.length > 0
      ? examples.map((ex, i) => ({
          label: `Case ${i + 1}`,
          input: ex.input,
          expected: ex.expectedOutput,
          note: ex.explanation || 'Public assertion vector',
        }))
      : [
          {
            label: 'Case 1',
            input: 'a = 0, b = 0',
            expected: 'y = 0',
            note: '0 & 0 = 0',
          },
          {
            label: 'Case 2',
            input: 'a = 0, b = 1',
            expected: 'y = 0',
            note: '0 & 1 = 0',
          },
          {
            label: 'Case 3',
            input: 'a = 1, b = 1',
            expected: 'y = 1',
            note: '1 & 1 = 1',
          },
        ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* Tab bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '4px',
          padding: '6px 12px',
          borderBottom: '1px solid var(--border-subtle)',
          backgroundColor: 'var(--surface)',
          flexShrink: 0,
        }}
      >
        <button
          onClick={() => setActiveTab('testcase')}
          className={`neu-btn ${activeTab === 'testcase' ? 'neu-btn-primary' : 'neu-btn-ghost'}`}
          style={{ padding: '4px 10px', fontSize: '11px', gap: '5px' }}
        >
          <FileCheck size={13} />
          <span>Testcase</span>
        </button>

        <button
          onClick={() => setActiveTab('result')}
          className={`neu-btn ${activeTab === 'result' ? 'neu-btn-primary' : 'neu-btn-ghost'}`}
          style={{ padding: '4px 10px', fontSize: '11px', gap: '5px' }}
        >
          <Terminal size={13} />
          <span>Test Result</span>
          {result?.status === 'ACCEPTED' && (
            <span
              style={{
                width: '6px',
                height: '6px',
                borderRadius: '50%',
                backgroundColor: 'var(--status-success)',
              }}
            />
          )}
        </button>
      </div>

      {/* Tab Body */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '16px' }}>
        {activeTab === 'testcase' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            {/* Case selector pills */}
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              {displayCases.map((c, i) => (
                <button
                  key={i}
                  onClick={() => setSelectedCase(i)}
                  className={`neu-btn ${selectedCase === i ? 'neu-btn-primary' : 'neu-btn-ghost'}`}
                  style={{ padding: '4px 10px', fontSize: '11px' }}
                >
                  {c.label}
                </button>
              ))}
            </div>

            {/* Selected case details */}
            {displayCases[selectedCase] && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <div>
                  <div
                    style={{
                      fontSize: '11px',
                      color: 'var(--text-muted)',
                      fontFamily: 'var(--font-mono)',
                      marginBottom: '4px',
                    }}
                  >
                    INPUT VECTOR
                  </div>
                  <div
                    className="neu-inset"
                    style={{
                      padding: '8px 12px',
                      fontFamily: 'var(--font-mono)',
                      fontSize: '12px',
                      color: 'var(--text-main)',
                    }}
                  >
                    {displayCases[selectedCase].input}
                  </div>
                </div>

                <div>
                  <div
                    style={{
                      fontSize: '11px',
                      color: 'var(--text-muted)',
                      fontFamily: 'var(--font-mono)',
                      marginBottom: '4px',
                    }}
                  >
                    EXPECTED OUTPUT
                  </div>
                  <div
                    className="neu-inset"
                    style={{
                      padding: '8px 12px',
                      fontFamily: 'var(--font-mono)',
                      fontSize: '12px',
                      color: 'var(--status-success)',
                    }}
                  >
                    {displayCases[selectedCase].expected}
                  </div>
                </div>

                <div style={{ fontSize: '11px', color: 'var(--text-dim)', fontStyle: 'italic' }}>
                  Note: {displayCases[selectedCase].note}
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'result' && (
          <>
            {/* Idle State */}
            {status === 'IDLE' && !result && (
              <div
                style={{
                  height: '100%',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  textAlign: 'center',
                  color: 'var(--text-muted)',
                  gap: '10px',
                  padding: '20px',
                }}
              >
                <div
                  className="neu-inset"
                  style={{
                    width: '40px',
                    height: '40px',
                    borderRadius: '50%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'var(--accent)',
                  }}
                >
                  <Play size={18} />
                </div>
                <div style={{ fontWeight: 600, color: 'var(--text-main)', fontSize: '13px' }}>
                  Ready for Verification
                </div>
                <p style={{ fontSize: '12px', maxWidth: '280px', margin: 0, lineHeight: 1.5 }}>
                  Click <strong style={{ color: 'var(--text-main)' }}>Run</strong> to verify against public examples, or <strong style={{ color: 'var(--accent)' }}>Submit</strong> for full verification on the remote worker cluster.
                </p>
              </div>
            )}

            {/* In-Flight Simulation Transition */}
            {(status === 'QUEUED' || status === 'COMPILING' || status === 'RUNNING_TESTS') && (
              <div
                style={{
                  height: '100%',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  textAlign: 'center',
                  gap: '12px',
                  padding: '20px',
                }}
              >
                <Loader2
                  size={26}
                  style={{ animation: 'spin 1.2s linear infinite', color: 'var(--accent)' }}
                />
                <div>
                  <div
                    style={{
                      fontFamily: 'var(--font-mono)',
                      fontSize: '13px',
                      fontWeight: 600,
                      color: 'var(--accent)',
                    }}
                  >
                    {status === 'QUEUED' && 'Queued in Execution Queue...'}
                    {status === 'COMPILING' && 'Icarus Verilog Compiling...'}
                    {status === 'RUNNING_TESTS' && 'Simulating Testbench Assertions...'}
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
                    Sandboxed execution in isolated container
                  </div>
                </div>
              </div>
            )}

            {/* Accepted State */}
            {result && result.status === 'ACCEPTED' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                <div
                  className="neu-card"
                  style={{
                    padding: '14px',
                    backgroundColor: 'var(--status-success-bg)',
                    borderColor: 'rgba(94, 138, 94, 0.3)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <CheckCircle2
                      size={22}
                      style={{ color: 'var(--status-success)', flexShrink: 0 }}
                    />
                    <div>
                      <div
                        style={{
                          fontFamily: 'var(--font-mono)',
                          fontSize: '14px',
                          fontWeight: 700,
                          color: 'var(--status-success)',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px',
                        }}
                      >
                        <span>✓ ACCEPTED</span>
                        {result.xpEarned && result.xpEarned > 0 ? (
                          <span
                            style={{
                              fontSize: '11px',
                              padding: '1px 6px',
                              borderRadius: '4px',
                              backgroundColor: 'rgba(201, 111, 74, 0.15)',
                              color: 'var(--accent)',
                            }}
                          >
                            +{result.xpEarned} XP
                          </span>
                        ) : null}
                      </div>
                      <div style={{ fontSize: '11px', color: 'var(--text-main)', marginTop: '2px' }}>
                        {result.testsPassed} / {result.totalTests} tests passed
                        {result.xpEarned && result.xpEarned > 0
                          ? ' • Timing closure met & XP recorded'
                          : ' • All sample vectors verified'}
                      </div>
                    </div>
                  </div>

                  {onNextChallenge && (
                    <button
                      onClick={onNextChallenge}
                      className="neu-btn neu-btn-primary"
                      style={{ padding: '6px 12px', fontSize: '11px', flexShrink: 0 }}
                    >
                      <span>Next</span>
                      <ArrowRight size={13} />
                    </button>
                  )}
                </div>

                {/* Telemetry row */}
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(3, 1fr)',
                    gap: '8px',
                    fontSize: '11px',
                    fontFamily: 'var(--font-mono)',
                  }}
                >
                  <div className="neu-card-sm" style={{ padding: '8px' }}>
                    <div style={{ color: 'var(--text-muted)', fontSize: '10px' }}>RUNTIME</div>
                    <div style={{ color: 'var(--text-main)', fontWeight: 700 }}>
                      {result.executionTimeMs} ms
                    </div>
                  </div>
                  <div className="neu-card-sm" style={{ padding: '8px' }}>
                    <div style={{ color: 'var(--text-muted)', fontSize: '10px' }}>SIM TIME</div>
                    <div style={{ color: 'var(--text-main)', fontWeight: 700 }}>
                      {result.simulationNanoseconds} ns
                    </div>
                  </div>
                  <div className="neu-card-sm" style={{ padding: '8px' }}>
                    <div style={{ color: 'var(--text-muted)', fontSize: '10px' }}>PASS RATE</div>
                    <div style={{ color: 'var(--status-success)', fontWeight: 700 }}>100%</div>
                  </div>
                </div>

                {/* Synthesis Output */}
                {result.compilerOutput && (
                  <div>
                    <div
                      style={{
                        fontSize: '10px',
                        color: 'var(--text-muted)',
                        fontFamily: 'var(--font-mono)',
                        marginBottom: '4px',
                      }}
                    >
                      SYNTHESIS & SIMULATION LOGS
                    </div>
                    <pre
                      className="neu-inset"
                      style={{
                        padding: '10px',
                        fontSize: '11px',
                        fontFamily: 'var(--font-mono)',
                        color: 'var(--text-muted)',
                        lineHeight: 1.4,
                        margin: 0,
                        whiteSpace: 'pre-wrap',
                      }}
                    >
                      {result.compilerOutput}
                    </pre>
                  </div>
                )}
              </div>
            )}

            {/* Failed State / Wrong Answer */}
            {result && result.status === 'FAILED' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                <div
                  className="neu-card"
                  style={{
                    padding: '14px',
                    backgroundColor: 'var(--status-error-bg)',
                    borderColor: 'rgba(184, 74, 57, 0.3)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                  }}
                >
                  <XCircle size={22} style={{ color: 'var(--status-error)', flexShrink: 0 }} />
                  <div>
                    <div
                      style={{
                        fontFamily: 'var(--font-mono)',
                        fontSize: '14px',
                        fontWeight: 700,
                        color: 'var(--status-error)',
                      }}
                    >
                      ✕ WRONG ANSWER
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--text-main)', marginTop: '2px' }}>
                      {result.testsPassed} / {result.totalTests} tests passed
                    </div>
                  </div>
                </div>

                {/* Comparison Boxes */}
                {result.failedVector && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    <div
                      style={{
                        fontSize: '10px',
                        color: 'var(--text-muted)',
                        fontFamily: 'var(--font-mono)',
                      }}
                    >
                      FAILED TESTCASE #{result.failedVector.vectorIndex}
                    </div>
                    <div
                      className="neu-inset"
                      style={{ padding: '8px 10px', fontFamily: 'var(--font-mono)', fontSize: '11px' }}
                    >
                      <span style={{ color: 'var(--text-muted)' }}>Input:    </span>
                      <span style={{ color: 'var(--text-main)' }}>{result.failedVector.input}</span>
                    </div>
                    <div
                      className="neu-inset"
                      style={{ padding: '8px 10px', fontFamily: 'var(--font-mono)', fontSize: '11px' }}
                    >
                      <span style={{ color: 'var(--text-muted)' }}>Output:   </span>
                      <span style={{ color: 'var(--status-error)' }}>{result.failedVector.actual}</span>
                    </div>
                    <div
                      className="neu-inset"
                      style={{ padding: '8px 10px', fontFamily: 'var(--font-mono)', fontSize: '11px' }}
                    >
                      <span style={{ color: 'var(--text-muted)' }}>Expected: </span>
                      <span style={{ color: 'var(--status-success)' }}>{result.failedVector.expected}</span>
                    </div>
                  </div>
                )}

                {result.compilerOutput && (
                  <div>
                    <div
                      style={{
                        fontSize: '10px',
                        color: 'var(--text-muted)',
                        fontFamily: 'var(--font-mono)',
                        marginBottom: '4px',
                      }}
                    >
                      DIAGNOSTICS
                    </div>
                    <pre
                      className="neu-inset"
                      style={{
                        padding: '10px',
                        fontSize: '11px',
                        fontFamily: 'var(--font-mono)',
                        color: 'var(--status-error)',
                        lineHeight: 1.4,
                        margin: 0,
                        whiteSpace: 'pre-wrap',
                      }}
                    >
                      {result.compilerOutput}
                    </pre>
                  </div>
                )}
              </div>
            )}

            {/* Compilation Error */}
            {result && result.status === 'COMPILATION_ERROR' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                <div
                  className="neu-card"
                  style={{
                    padding: '14px',
                    backgroundColor: 'var(--status-error-bg)',
                    borderColor: 'rgba(184, 74, 57, 0.3)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                  }}
                >
                  <XCircle size={22} style={{ color: 'var(--status-error)', flexShrink: 0 }} />
                  <div>
                    <div
                      style={{
                        fontFamily: 'var(--font-mono)',
                        fontSize: '14px',
                        fontWeight: 700,
                        color: 'var(--status-error)',
                      }}
                    >
                      ✕ COMPILATION ERROR
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--text-main)', marginTop: '2px' }}>
                      Icarus Verilog could not synthesize or compile your module.
                    </div>
                  </div>
                </div>

                {result.compilerOutput && (
                  <div>
                    <div
                      style={{
                        fontSize: '10px',
                        color: 'var(--text-muted)',
                        fontFamily: 'var(--font-mono)',
                        marginBottom: '4px',
                      }}
                    >
                      COMPILER DIAGNOSTICS
                    </div>
                    <pre
                      className="neu-inset"
                      style={{
                        padding: '10px',
                        fontSize: '11px',
                        fontFamily: 'var(--font-mono)',
                        color: 'var(--status-error)',
                        lineHeight: 1.4,
                        margin: 0,
                        whiteSpace: 'pre-wrap',
                      }}
                    >
                      {result.compilerOutput}
                    </pre>
                  </div>
                )}
              </div>
            )}

            {/* Timeout Error */}
            {result && result.status === 'TIMEOUT' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                <div
                  className="neu-card"
                  style={{
                    padding: '14px',
                    backgroundColor: 'var(--status-warning-bg)',
                    borderColor: 'rgba(217, 119, 6, 0.3)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                  }}
                >
                  <Clock size={22} style={{ color: 'var(--accent)', flexShrink: 0 }} />
                  <div>
                    <div
                      style={{
                        fontFamily: 'var(--font-mono)',
                        fontSize: '14px',
                        fontWeight: 700,
                        color: 'var(--accent)',
                      }}
                    >
                      ⏱ EXECUTION TIMEOUT
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--text-main)', marginTop: '2px' }}>
                      Execution exceeded the 5-second hard time limit. Check for zero-delay loops or infinite latch loops.
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* System / Resource Limit Error */}
            {result && (result.status === 'SYSTEM_ERROR' || result.status === 'RESOURCE_LIMIT') && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                <div
                  className="neu-card"
                  style={{
                    padding: '14px',
                    backgroundColor: 'var(--surface)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                  }}
                >
                  <AlertTriangle size={22} style={{ color: 'var(--accent)', flexShrink: 0 }} />
                  <div>
                    <div
                      style={{
                        fontFamily: 'var(--font-mono)',
                        fontSize: '14px',
                        fontWeight: 700,
                        color: 'var(--accent)',
                      }}
                    >
                      ⚠ {result.status === 'RESOURCE_LIMIT' ? 'RESOURCE LIMIT EXCEEDED' : 'SYSTEM ERROR'}
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
                      The verification worker encountered an environmental boundary. No attempt penalty assessed.
                    </div>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};
