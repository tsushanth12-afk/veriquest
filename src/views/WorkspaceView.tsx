/* ==========================================================================
   VeriQuest View — Challenge Workspace (3-Pane Professional IDE)
   Wired to real submission/polling flow with 60s cap & warm neumorphic design
   ========================================================================== */

import React, { useState, useEffect, useRef } from 'react';
import { useApp } from '../context/AppContext';
import { challengeApi } from '../api/challengeApi';
import { submissionApi } from '../api/submissionApi';
import { PublicChallenge } from '../types/challenge';
import { SubmissionStatus, SubmissionResult } from '../types/submission';
import { ProblemPanel } from '../components/workspace/ProblemPanel';
import { CodeEditor } from '../components/workspace/CodeEditor';
import { SubmissionPanel } from '../components/workspace/SubmissionPanel';
import { ArrowLeft, Loader2, Sparkles } from 'lucide-react';

export const WorkspaceView: React.FC = () => {
  const { activeChallengeId, setCurrentRoute, addToast, refreshProfile } = useApp();
  const [challenge, setChallenge] = useState<PublicChallenge | null>(null);
  const [isLoadingChallenge, setIsLoadingChallenge] = useState(true);
  const [code, setCode] = useState<string>('');
  const [submissionStatus, setSubmissionStatus] = useState<SubmissionStatus>('IDLE');
  const [submissionResult, setSubmissionResult] = useState<SubmissionResult | null>(null);
  const [isExecuting, setIsExecuting] = useState(false);
  const pollTimerRef = useRef<any>(null);

  useEffect(() => {
    let mounted = true;
    setIsLoadingChallenge(true);

    challengeApi
      .getChallengeById(activeChallengeId)
      .then((c: PublicChallenge | null) => {
        if (!mounted) return;
        if (c) {
          setChallenge(c);
          setCode(c.starterCode);
          setSubmissionStatus('IDLE');
          setSubmissionResult(null);
        }
        setIsLoadingChallenge(false);
      })
      .catch(() => {
        if (mounted) setIsLoadingChallenge(false);
      });

    return () => {
      mounted = false;
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
      }
    };
  }, [activeChallengeId]);

  if (isLoadingChallenge) {
    return (
      <div
        className="neu-card"
        style={{
          padding: '60px 40px',
          textAlign: 'center',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '12px',
          color: 'var(--text-muted)',
        }}
      >
        <Loader2 size={28} style={{ animation: 'spin 1.2s linear infinite', color: 'var(--accent)' }} />
        <span style={{ fontSize: '13px' }}>Loading challenge workspace environment...</span>
      </div>
    );
  }

  if (!challenge) {
    return (
      <div
        className="neu-card"
        style={{
          padding: '60px 40px',
          textAlign: 'center',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '14px',
        }}
      >
        <h3 style={{ margin: 0, fontSize: '18px' }}>Challenge Not Found</h3>
        <p style={{ margin: 0, fontSize: '13px', color: 'var(--text-muted)' }}>
          The requested challenge identifier could not be loaded.
        </p>
        <button
          onClick={() => setCurrentRoute('challenges')}
          className="neu-btn neu-btn-primary"
          style={{ padding: '8px 16px', fontSize: '12px' }}
        >
          Return to Challenge Library
        </button>
      </div>
    );
  }

  // Handle non-scoring local test vector execution ("Run")
  const handleRun = async () => {
    setIsExecuting(true);
    setSubmissionStatus('RUNNING_TESTS');
    addToast({
      type: 'info',
      title: 'Testing Sample Vectors',
      description: 'Running local verification on visible test cases (non-scoring)...',
    });

    try {
      const result = await submissionApi.runPublicVectors(
        challenge.id,
        code,
        challenge.examples || []
      );
      setSubmissionStatus(result.status);
      setSubmissionResult(result);

      if (result.status === 'ACCEPTED') {
        addToast({
          type: 'success',
          title: 'Sample Vectors Passed!',
          description: `${result.testsPassed}/${result.totalTests} sample test cases verified clean.`,
        });
      } else if (result.status === 'COMPILATION_ERROR') {
        addToast({
          type: 'error',
          title: 'Syntax Error',
          description: 'Module compilation failed. Check your Verilog syntax.',
        });
      } else {
        addToast({
          type: 'warning',
          title: 'Vector Mismatch',
          description: 'Output differed on sample vectors. Review logic assignments.',
        });
      }
    } catch {
      setSubmissionStatus('SYSTEM_ERROR');
    } finally {
      setIsExecuting(false);
    }
  };

  // Handle authoritative remote verification ("Submit")
  const handleSubmit = async () => {
    setIsExecuting(true);
    setSubmissionStatus('QUEUED');
    addToast({
      type: 'info',
      title: 'Dispatching to Verification Cluster',
      description: 'Sending RTL module to backend sandbox for automated grading...',
    });

    try {
      const { submissionId, isRemote } = await submissionApi.submitSolution(challenge.id, code);

      const startTime = Date.now();
      const maxWaitMs = 60000; // Strictly cap at 60s per Section 6

      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
      }

      pollTimerRef.current = setInterval(async () => {
        // Enforce 60s hard polling cap
        if (Date.now() - startTime >= maxWaitMs) {
          clearInterval(pollTimerRef.current);
          setIsExecuting(false);
          setSubmissionStatus('TIMEOUT');
          addToast({
            type: 'warning',
            title: 'Polling Timeout Cap Reached',
            description: 'Simulation took longer than 60s. Check Submissions history later.',
          });
          return;
        }

        const res = await submissionApi.pollSubmissionStatus(submissionId, isRemote);
        setSubmissionStatus(res.status);

        const terminalStatuses: SubmissionStatus[] = [
          'ACCEPTED',
          'FAILED',
          'COMPILATION_ERROR',
          'TIMEOUT',
          'RESOURCE_LIMIT',
          'SYSTEM_ERROR',
        ];

        if (terminalStatuses.includes(res.status)) {
          clearInterval(pollTimerRef.current);
          setIsExecuting(false);
          setSubmissionResult(res);

          if (res.status === 'ACCEPTED') {
            const xp = res.xpEarned || challenge.xp || 40;
            addToast({
              type: 'success',
              title: `Challenge Verified! +${xp} XP`,
              description: 'Timing closure met. Server progress updated.',
            });
            refreshProfile();
          } else if (res.status === 'COMPILATION_ERROR') {
            addToast({
              type: 'error',
              title: 'Compilation Error',
              description: 'Icarus Verilog syntax or synthesis diagnostics reported.',
            });
          } else {
            addToast({
              type: 'warning',
              title: 'Simulation Mismatch Detected',
              description: 'Assertion check failed against hidden testbench vectors.',
            });
          }
        }
      }, 500);
    } catch {
      setIsExecuting(false);
      setSubmissionStatus('SYSTEM_ERROR');
      addToast({
        type: 'error',
        title: 'Submission Failed',
        description: 'Unable to communicate with the verification runner.',
      });
    }
  };

  const handleReset = () => {
    setCode(challenge.starterCode);
    setSubmissionStatus('IDLE');
    setSubmissionResult(null);
    addToast({ type: 'info', title: 'Reverted to starter code' });
  };

  const isDemoChallenge =
    challenge.slug === 'and-gate-demo' || challenge.category === 'Development Demo';

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: 'calc(100vh - 84px)',
        gap: '12px',
      }}
    >
      {/* Workspace Subheader Navigation */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 4px',
          flexShrink: 0,
        }}
      >
        <button
          onClick={() => setCurrentRoute('challenges')}
          className="neu-btn-ghost"
          style={{ fontSize: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}
        >
          <ArrowLeft size={14} />
          <span>Back to Challenges</span>
        </button>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {isDemoChallenge && (
            <span
              style={{
                fontSize: '11px',
                fontFamily: 'var(--font-mono)',
                fontWeight: 700,
                padding: '2px 8px',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: 'rgba(201, 111, 74, 0.15)',
                color: 'var(--accent)',
                border: '1px solid rgba(201, 111, 74, 0.3)',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
              }}
            >
              <Sparkles size={11} />
              <span>DEVELOPMENT DEMO</span>
            </span>
          )}

          <span
            style={{
              fontSize: '12px',
              color: 'var(--text-muted)',
              fontFamily: 'var(--font-mono)',
            }}
          >
            CHALLENGE: <strong style={{ color: 'var(--text-main)' }}>{challenge.slug}</strong>
          </span>
        </div>
      </div>

      {/* 3-Pane Desktop Layout / Vertically Stacked on Mobile (Master Prompt Item 15) */}
      <div className="workspace-grid">
        {/* Left Pane: Problem Specification */}
        <div
          className="neu-card"
          style={{
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          <ProblemPanel challenge={challenge} />
        </div>

        {/* Center Pane: Monaco Editor (Warm Theme) */}
        <div
          className="neu-card"
          style={{
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          <CodeEditor
            code={code}
            onChange={setCode}
            onRun={handleRun}
            onSubmit={handleSubmit}
            onReset={handleReset}
            isExecuting={isExecuting}
            filename={`${challenge.slug}.v`}
          />
        </div>

        {/* Right Pane: Execution Telemetry & Verification Console */}
        <div
          className="neu-card"
          style={{
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          <div
            style={{
              padding: '10px 16px',
              borderBottom: '1px solid var(--border-subtle)',
              fontSize: '11px',
              fontWeight: 600,
              color: 'var(--text-muted)',
              fontFamily: 'var(--font-mono)',
              textTransform: 'uppercase',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              backgroundColor: 'var(--surface)',
            }}
          >
            <span>Verification Terminal</span>
            <span
              style={{
                fontSize: '10px',
                fontWeight: 700,
                color:
                  submissionStatus === 'ACCEPTED'
                    ? 'var(--status-success)'
                    : submissionStatus === 'FAILED' || submissionStatus === 'COMPILATION_ERROR'
                    ? 'var(--status-error)'
                    : 'var(--accent)',
              }}
            >
              {submissionStatus}
            </span>
          </div>
          <div style={{ flex: 1, overflowY: 'auto' }}>
            <SubmissionPanel
              status={submissionStatus}
              result={submissionResult}
              examples={challenge.examples}
            />
          </div>
        </div>
      </div>

      <style>{`
        @media (max-width: 1024px) {
          .workspace-grid {
            grid-template-columns: 1fr !important;
            height: auto !important;
            display: flex !important;
            flex-direction: column !important;
          }
        }
      `}</style>
    </div>
  );
};
