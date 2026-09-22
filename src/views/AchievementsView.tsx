/* ==========================================================================
   VeriQuest View — Achievements & Silicon Badges
   With loading, empty, and error boundaries
   ========================================================================== */

import React, { useState, useEffect } from 'react';
import { badgeApi } from '../api/questApi';
import { Badge } from '../types/quest';
import { Cpu, Clock, ShieldAlert, Workflow, Zap, Award, Terminal, Loader2, AlertTriangle } from 'lucide-react';

export const AchievementsView: React.FC = () => {
  const [badges, setBadges] = useState<Badge[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const fetchBadges = () => {
    setIsLoading(true);
    setErrorMessage(null);

    badgeApi
      .getBadges()
      .then((data) => {
        setBadges(data || []);
        setIsLoading(false);
      })
      .catch(() => {
        setErrorMessage('Unable to load badges. Please try again.');
        setIsLoading(false);
      });
  };

  useEffect(() => {
    fetchBadges();
  }, []);

  const getIcon = (iconName: string) => {
    switch (iconName) {
      case 'Terminal':
        return Terminal;
      case 'Cpu':
        return Cpu;
      case 'Clock':
        return Clock;
      case 'ShieldAlert':
        return ShieldAlert;
      case 'Workflow':
        return Workflow;
      case 'Zap':
        return Zap;
      case 'Award':
      default:
        return Award;
    }
  };

  const unlockedCount = badges.filter((b) => b.unlocked).length;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Header */}
      <div
        className="neu-card"
        style={{
          padding: '24px 28px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '16px',
        }}
      >
        <div>
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
            ENGINEERING MILESTONES
          </div>
          <h1 style={{ fontSize: '22px', margin: 0 }}>Hardware Verification Badges</h1>
          <p style={{ margin: '4px 0 0 0', fontSize: '13px', color: 'var(--text-muted)' }}>
            Recognizing architectural discipline, clean synthesis, timing accuracy, and HDL mastery.
          </p>
        </div>

        <div className="neu-card-sm" style={{ padding: '10px 18px', textAlign: 'center' }}>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
            UNLOCKED
          </div>
          <div
            style={{
              fontSize: '20px',
              fontFamily: 'var(--font-mono)',
              fontWeight: 700,
              color: 'var(--accent)',
            }}
          >
            {unlockedCount} / {badges.length}
          </div>
        </div>
      </div>

      {/* Badges Area */}
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
          <span style={{ fontSize: '13px' }}>Loading achievements and badges...</span>
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
            onClick={fetchBadges}
            className="neu-btn neu-btn-primary"
            style={{ padding: '6px 14px', fontSize: '12px' }}
          >
            Retry
          </button>
        </div>
      ) : badges.length === 0 ? (
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
          <Award size={28} style={{ color: 'var(--accent)', opacity: 0.6 }} />
          <span style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-main)' }}>
            No badges configured yet
          </span>
          <p style={{ margin: 0, fontSize: '12px', maxWidth: '320px', lineHeight: 1.5 }}>
            Engineering milestones will appear here as you verify solutions and close timing.
          </p>
        </div>
      ) : (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
            gap: '18px',
          }}
        >
          {badges.map((badge) => {
            const Icon = getIcon(badge.icon);

            return (
              <div
                key={badge.id}
                className="neu-card"
                style={{
                  padding: '20px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '12px',
                  opacity: badge.unlocked ? 1 : 0.65,
                  border: badge.unlocked
                    ? '1px solid var(--accent-subtle)'
                    : '1px solid var(--border-subtle)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div
                    className="neu-inset"
                    style={{
                      width: '42px',
                      height: '42px',
                      borderRadius: 'var(--radius-sm)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: badge.unlocked ? 'var(--accent)' : 'var(--text-dim)',
                    }}
                  >
                    <Icon size={20} />
                  </div>

                  <span
                    className="neu-badge"
                    style={{
                      color: badge.unlocked ? 'var(--status-success)' : 'var(--text-dim)',
                      backgroundColor: badge.unlocked ? 'var(--status-success-bg)' : 'var(--surface-hover)',
                    }}
                  >
                    {badge.unlocked ? 'UNLOCKED' : 'LOCKED'}
                  </span>
                </div>

                <div>
                  <h3 style={{ fontSize: '15px', margin: 0, color: 'var(--text-main)' }}>
                    {badge.name}
                  </h3>
                  <p
                    style={{
                      margin: '4px 0 0 0',
                      fontSize: '12px',
                      color: 'var(--text-muted)',
                      lineHeight: 1.4,
                    }}
                  >
                    {badge.description}
                  </p>
                </div>

                <div
                  style={{
                    marginTop: 'auto',
                    paddingTop: '10px',
                    borderTop: '1px solid var(--border-subtle)',
                    fontSize: '11px',
                    color: 'var(--text-muted)',
                  }}
                >
                  {badge.unlocked ? (
                    <span style={{ color: 'var(--status-success)' }}>
                      Unlocked on {badge.unlockedAt || 'recently'}
                    </span>
                  ) : (
                    <span>
                      Requirement: <strong>{badge.requirement}</strong>
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
