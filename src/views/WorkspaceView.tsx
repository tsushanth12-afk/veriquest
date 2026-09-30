/* ==========================================================================
   VeriQuest View — Challenge Workspace (3-Pane Professional IDE)
   Wired to real submission/polling flow with 60s cap & warm neumorphic design
   ========================================================================== */

import React, { useState, useEffect, useRef } from 'react';
import { useApp } from '../context/AppContext';
import { challengeApi } from '../api/challengeApi';
import { sessionSnapshot, isCurrentSession } from '../api/sessionBoundary';
import { submissionApi } from '../api/submissionApi';
import { PublicChallenge } from '../types/challenge';
import { SubmissionStatus, SubmissionResult } from '../types/submission';
import { ProblemPanel } from '../components/workspace/ProblemPanel';
import { CodeEditor } from '../components/workspace/CodeEditor';
import { SubmissionPanel } from '../components/workspace/SubmissionPanel';
import { ArrowLeft, Loader2, Sparkles } from 'lucide-react';

export const WorkspaceView: React.FC = () => {
  const { activeChallengeId, setCurrentRoute, addToast, refreshProfile, isAuthenticated, setAuthOpen } = useApp();
  const [challenge, setChallenge] = useState<PublicChallenge | null>(null);
  const [isLoadingChallenge, setIsLoadingChallenge] = useState(true);
  const [code, setCode] = useState<string>('');
  const [submissionStatus, setSubmissionStatus] = useState<SubmissionStatus>('IDLE');
  const [submissionResult, setSubmissionResult] = useState<SubmissionResult | null>(null);
  const [isExecuting, setIsExecuting] = useState(false);
  const operation = useRef(0);
  const pollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

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
      operation.current++;
      setIsExecuting(false);
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
    const run = ++operation.current;
    const snapshot = sessionSnapshot();
    setIsExecuting(true);
    setSubmissionStatus('RUNNING_TESTS');
    addToast({
      type: 'info',
      title: 'Unscored Local Practice',
      description: 'Running local WASM verification. Zero XP; no scored completion.',
    });

    try {
      const result = await submissionApi.runPublicVectors(
        challenge.id,
        code,
        challenge.examples || []
      );
      if (run !== operation.current || !isCurrentSession(snapshot)) return;
      setSubmissionStatus(result.status);
      setSubmissionResult(result);

      if (result.status === 'ACCEPTED') {
        addToast({
          type: 'success',
          title: 'Practice Tests Passed!',
          description: `${result.testsPassed}/${result.totalTests} practice test cases verified. No progress awarded.`,
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
      if (run === operation.current && isCurrentSession(snapshot)) setSubmissionStatus('SYSTEM_ERROR');
    } finally {
      if (run === operation.current && isCurrentSession(snapshot)) setIsExecuting(false);
    }
  };

  // Handle authoritative remote verification ("Submit")
  const handleSubmit = async () => {
    if (!isAuthenticated) {
      setAuthOpen(true);
      addToast({ type: 'info', title: 'Sign in for scored Submit', description: 'Run is unscored local practice: zero XP and no completion.' });
      return;
    }
    const id = ++operation.current;
    const snapshot = sessionSnapshot();
    const current = () => id === operation.current && isCurrentSession(snapshot);
    setIsExecuting(true);
    setSubmissionResult(null);
    setSubmissionStatus('QUEUED');
    const fail = (error: unknown) => {
      if (!current()) return;
      setIsExecuting(false);
      setSubmissionStatus('SYSTEM_ERROR');
      addToast({ type: 'error', title: 'Submission Failed', description: error instanceof Error ? error.message : String(error) });
    };
    try {
      const { submissionId } = await submissionApi.submitSolution(challenge.id, code);
      if (!current()) return;
      const start = Date.now();
      const poll = async () => {
        if (!current()) return;
        try {
          if (Date.now() - start >= 60000) throw new Error('Polling timeout. Check backend submission history later.');
          const result = await submissionApi.pollSubmissionStatus(submissionId, true);
          if (!current()) return;
          setSubmissionStatus(result.status);
          if (['QUEUED', 'COMPILING', 'RUNNING_TESTS'].includes(result.status)) {
            pollTimerRef.current = setTimeout(() => void poll(), 500);
            return;
          }
          setSubmissionResult(result);
          setIsExecuting(false);
          if (result.status === 'ACCEPTED') {
            addToast({ type: 'success', title: 'Backend accepted submission', description: 'Refreshing server profile; no local XP is awarded.' });
            await refreshProfile();
          } else addToast({ type: 'warning', title: result.status, description: result.compilerOutput });
        } catch (error) { fail(error); }
      };
      pollTimerRef.current = setTimeout(() => void poll(), 500);
    } catch (error) { fail(error); }
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
      <p role="note">Run: local practice only — zero XP, no scored completion. Submit: authenticated backend scoring only.</p>
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
          <ProblemPanel
            challenge={challenge}
            onLoadCode={setCode}
            onSetResult={setSubmissionResult}
          />
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
                    : submissionStatus === 'WRONG_ANSWER' || submissionStatus === 'COMPILATION_ERROR'
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
