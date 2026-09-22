/* ==========================================================================
   VeriQuest Dashboard — Challenge History & Submissions Table
   With real submission history and clean empty state
   ========================================================================== */

import React, { useState, useEffect } from 'react';
import { useApp } from '../../context/AppContext';
import { CheckCircle2, XCircle, ArrowRight, History, Loader2 } from 'lucide-react';
import { api } from '../../api/client';

interface SubmissionItem {
  id: string;
  challenge_id: string;
  challenge_title?: string;
  status: string;
  tests_passed: number;
  tests_total: number;
  xp_awarded: number;
  submitted_at: string;
}

export const ChallengeHistoryTable: React.FC = () => {
  const { openChallenge, setCurrentRoute, user } = useApp();
  const [submissions, setSubmissions] = useState<SubmissionItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    let mounted = true;
    setIsLoading(true);

    api.submissions
      .getSubmissionHistory(1, 5)
      .then(({ data, error }) => {
        if (!mounted) return;
        if (data && !error && data.submissions && data.submissions.length > 0) {
          setSubmissions(data.submissions as unknown as SubmissionItem[]);
        } else {
          setSubmissions([]);
        }
        setIsLoading(false);
      })
      .catch(() => {
        if (mounted) setIsLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, [user.stats.totalSolved]);

  return (
    <div
      className="neu-card"
      style={{
        padding: '22px 24px',
        display: 'flex',
        flexDirection: 'column',
        gap: '16px',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <History size={16} style={{ color: 'var(--accent)' }} />
          <h2 style={{ fontSize: '15px', margin: 0 }}>Recent Verification History</h2>
        </div>
        <button
          onClick={() => setCurrentRoute('challenges')}
          className="neu-btn-ghost"
          style={{ fontSize: '11px', padding: '3px 8px' }}
        >
          View Challenge Library →
        </button>
      </div>

      {isLoading ? (
        <div style={{ textAlign: 'center', padding: '30px', color: 'var(--text-muted)' }}>
          <Loader2 size={20} style={{ animation: 'spin 1.2s linear infinite', color: 'var(--accent)' }} />
        </div>
      ) : submissions.length === 0 ? (
        <div
          style={{
            padding: '36px 20px',
            textAlign: 'center',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '10px',
            color: 'var(--text-muted)',
          }}
        >
          <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-main)' }}>
            No submissions recorded yet
          </span>
          <p style={{ margin: 0, fontSize: '12px', maxWidth: '340px', lineHeight: 1.5 }}>
            Launch the <strong>Two-Input AND Gate</strong> development demo challenge to test continuous assignments and generate your first simulation record.
          </p>
          <button
            onClick={() => openChallenge('and-gate-demo')}
            className="neu-btn neu-btn-primary"
            style={{ padding: '6px 14px', fontSize: '12px', marginTop: '6px', gap: '6px' }}
          >
            <span>Start Development Demo</span>
            <ArrowRight size={13} />
          </button>
        </div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
            <thead>
              <tr
                style={{
                  borderBottom: '1px solid var(--border-subtle)',
                  color: 'var(--text-muted)',
                  fontFamily: 'var(--font-mono)',
                  fontSize: '11px',
                  letterSpacing: '0.04em',
                }}
              >
                <th style={{ padding: '8px 12px', width: '40px' }}>STATUS</th>
                <th style={{ padding: '8px 12px' }}>CHALLENGE</th>
                <th style={{ padding: '8px 12px' }}>TESTS</th>
                <th style={{ padding: '8px 12px' }}>XP AWARDED</th>
                <th style={{ padding: '8px 12px' }}>TIMESTAMP</th>
                <th style={{ padding: '8px 12px', textAlign: 'right' }}>ACTION</th>
              </tr>
            </thead>
            <tbody>
              {submissions.map((sub) => {
                const isAccepted = sub.status.toLowerCase() === 'accepted';

                return (
                  <tr
                    key={sub.id}
                    style={{
                      borderBottom: '1px solid var(--border-subtle)',
                    }}
                  >
                    <td style={{ padding: '12px', verticalAlign: 'middle' }}>
                      {isAccepted ? (
                        <CheckCircle2 size={16} style={{ color: 'var(--status-success)' }} />
                      ) : (
                        <XCircle size={16} style={{ color: 'var(--status-error)' }} />
                      )}
                    </td>
                    <td style={{ padding: '12px', verticalAlign: 'middle' }}>
                      <div style={{ fontWeight: 600, color: 'var(--text-main)' }}>
                        {sub.challenge_title || sub.challenge_id}
                      </div>
                    </td>
                    <td style={{ padding: '12px', verticalAlign: 'middle', fontFamily: 'var(--font-mono)' }}>
                      {sub.tests_passed} / {sub.tests_total}
                    </td>
                    <td
                      style={{
                        padding: '12px',
                        verticalAlign: 'middle',
                        fontFamily: 'var(--font-mono)',
                        color: 'var(--accent)',
                        fontWeight: 600,
                      }}
                    >
                      {sub.xp_awarded > 0 ? `+${sub.xp_awarded} XP` : '0 XP'}
                    </td>
                    <td
                      style={{
                        padding: '12px',
                        verticalAlign: 'middle',
                        fontSize: '11px',
                        color: 'var(--text-muted)',
                        fontFamily: 'var(--font-mono)',
                      }}
                    >
                      {new Date(sub.submitted_at).toLocaleDateString()}
                    </td>
                    <td style={{ padding: '12px', verticalAlign: 'middle', textAlign: 'right' }}>
                      <button
                        onClick={() => openChallenge(sub.challenge_id)}
                        className="neu-btn"
                        style={{ padding: '4px 8px', fontSize: '11px', gap: '4px' }}
                      >
                        <span>Workspace</span>
                        <ArrowRight size={11} />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
