/* ==========================================================================
   VeriQuest View — Quests & Progression Paths
   With loading, empty, and error boundaries
   ========================================================================== */

import React, { useState, useEffect } from 'react';
import { useApp } from '../context/AppContext';
import { questApi } from '../api/questApi';
import { Quest } from '../types/quest';
import { Route, CheckCircle2, Lock, Loader2, AlertTriangle } from 'lucide-react';
import { XPBadge } from '../components/common/XPBadge';

export const QuestsView: React.FC = () => {
  const { openChallenge } = useApp();
  const [quests, setQuests] = useState<Quest[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const fetchQuests = () => {
    setIsLoading(true);
    setErrorMessage(null);

    questApi
      .getQuests()
      .then((data) => {
        setQuests(data || []);
        setIsLoading(false);
      })
      .catch(() => {
        setErrorMessage('Unable to load quest tracks. Please try again.');
        setIsLoading(false);
      });
  };

  useEffect(() => {
    fetchQuests();
  }, []);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Header */}
      <div className="neu-card" style={{ padding: '24px 28px' }}>
        <div
          style={{
            fontSize: '11px',
            fontFamily: 'var(--font-mono)',
            color: 'var(--accent)',
            fontWeight: 600,
            textTransform: 'uppercase',
            marginBottom: '4px',
          }}
        >
          STRUCTURED MASTERY TRACKS
        </div>
        <h1 style={{ fontSize: '22px', margin: 0 }}>Active Quests</h1>
        <p style={{ margin: '4px 0 0 0', fontSize: '13px', color: 'var(--text-muted)' }}>
          Follow guided milestone tracks to systematically master each domain of digital logic design.
        </p>
      </div>

      {/* Quests Content */}
      {isLoading ? (
        <div
          className="neu-card"
          style={{
            padding: '60px 20px',
            textAlign: 'center',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '12px',
            color: 'var(--text-muted)',
          }}
        >
          <Loader2 size={28} style={{ animation: 'spin 1.2s linear infinite', color: 'var(--accent)' }} />
          <span style={{ fontSize: '13px' }}>Loading active quests and tracks...</span>
        </div>
      ) : errorMessage ? (
        <div
          className="neu-card"
          style={{
            padding: '40px 20px',
            textAlign: 'center',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '12px',
          }}
        >
          <AlertTriangle size={24} style={{ color: 'var(--accent)' }} />
          <span style={{ fontSize: '13px', color: 'var(--text-main)' }}>{errorMessage}</span>
          <button
            onClick={fetchQuests}
            className="neu-btn neu-btn-primary"
            style={{ padding: '6px 14px', fontSize: '12px' }}
          >
            Retry
          </button>
        </div>
      ) : quests.length === 0 ? (
        <div
          className="neu-card"
          style={{
            padding: '60px 20px',
            textAlign: 'center',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '10px',
            color: 'var(--text-muted)',
          }}
        >
          <Route size={28} style={{ color: 'var(--accent)', opacity: 0.6 }} />
          <span style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-main)' }}>
            No quests published yet
          </span>
          <p style={{ margin: 0, fontSize: '12px', maxWidth: '320px', lineHeight: 1.5 }}>
            Course instructors will publish progression quest tracks as curriculum modules are rolled out.
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {quests.map((q) => {
            const isLocked = q.status === 'LOCKED';
            const isDone = q.status === 'COMPLETED';

            return (
              <div
                key={q.id}
                className="neu-card"
                style={{
                  padding: '22px 26px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '16px',
                  opacity: isLocked ? 0.7 : 1,
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    flexWrap: 'wrap',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: '12px',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                    <div
                      className="neu-inset"
                      style={{
                        width: '42px',
                        height: '42px',
                        borderRadius: 'var(--radius-sm)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: isDone
                          ? 'var(--status-success)'
                          : isLocked
                          ? 'var(--text-dim)'
                          : 'var(--accent)',
                      }}
                    >
                      {isDone ? <CheckCircle2 size={20} /> : isLocked ? <Lock size={18} /> : <Route size={20} />}
                    </div>

                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '2px' }}>
                        <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                          {q.category}
                        </span>
                        <XPBadge xp={q.xpReward} />
                      </div>
                      <h3 style={{ fontSize: '16px', margin: 0, color: 'var(--text-main)' }}>
                        {q.title}
                      </h3>
                    </div>
                  </div>

                  <div style={{ minWidth: '180px' }}>
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        fontSize: '11px',
                        fontFamily: 'var(--font-mono)',
                        marginBottom: '4px',
                      }}
                    >
                      <span style={{ color: 'var(--text-muted)' }}>PROGRESS</span>
                      <span
                        style={{
                          fontWeight: 600,
                          color: isDone ? 'var(--status-success)' : 'var(--accent)',
                        }}
                      >
                        {q.progressPercent}% ({q.completedChallenges}/{q.totalChallenges})
                      </span>
                    </div>
                    <div className="neu-progress-track">
                      <div
                        className={`neu-progress-fill ${isDone ? 'neu-progress-fill-success' : ''}`}
                        style={{ width: `${q.progressPercent}%` }}
                      />
                    </div>
                  </div>
                </div>

                <p style={{ margin: 0, fontSize: '13px', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                  {q.description}
                </p>

                {q.challenges && q.challenges.length > 0 && (
                  <div
                    style={{
                      display: 'flex',
                      flexWrap: 'wrap',
                      alignItems: 'center',
                      gap: '8px',
                      paddingTop: '10px',
                      borderTop: '1px solid var(--border-subtle)',
                    }}
                  >
                    <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                      MODULES:
                    </span>
                    {q.challenges.map((ch, idx) => (
                      <button
                        key={idx}
                        onClick={() => openChallenge(ch.id || 'and-gate-demo')}
                        className={`neu-btn ${ch.completed ? 'neu-btn-primary' : 'neu-btn-ghost'}`}
                        style={{ padding: '3px 8px', fontSize: '11px', gap: '4px' }}
                      >
                        {ch.completed && <CheckCircle2 size={11} />}
                        <span>{ch.title}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
