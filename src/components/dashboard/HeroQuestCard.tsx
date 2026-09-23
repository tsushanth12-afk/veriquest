/* ==========================================================================
   VeriQuest Dashboard — Hero & Active Challenge Card
   Displays authentic user progress and links to the Development Demo challenge
   ========================================================================== */

import React from 'react';
import { useApp } from '../../context/AppContext';
import { ArrowRight, Sparkles, CheckCircle2 } from 'lucide-react';

export const HeroQuestCard: React.FC = () => {
  const { user, openChallenge } = useApp();
  const xpPercent =
    user.stats.nextLevelXP > 0
      ? Math.min(100, Math.round((user.stats.currentXP / user.stats.nextLevelXP) * 100))
      : 0;

  const hasSolvedDemo = user.stats.totalSolved > 0;

  return (
    <div
      className="neu-card"
      style={{
        padding: '24px 28px',
        display: 'flex',
        flexDirection: 'column',
        gap: '20px',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Top Identity & Status Row */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '16px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div
            className="neu-inset"
            style={{
              width: '52px',
              height: '52px',
              borderRadius: 'var(--radius-md)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              backgroundColor: 'var(--surface)',
              color: 'var(--accent)',
              fontSize: '20px',
              fontWeight: 700,
            }}
          >
            {user.username ? user.username.substring(0, 2).toUpperCase() : 'EE'}
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h1 style={{ fontSize: '20px', margin: 0 }}>
                Welcome back, {user.username || 'Student'}
              </h1>
              <span
                className="neu-badge"
                style={{
                  color: 'var(--accent)',
                  backgroundColor: 'var(--accent-subtle)',
                  borderColor: 'rgba(201, 111, 74, 0.25)',
                }}
              >
                Level {user.stats.level} • {user.stats.levelTitle}
              </span>
            </div>
            <p style={{ margin: '4px 0 0 0', fontSize: '13px', color: 'var(--text-muted)' }}>
              Master Verilog HDL one challenge at a time.
            </p>
          </div>
        </div>

        {/* Level XP Progress Bar */}
        <div style={{ minWidth: '220px' }}>
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              fontSize: '11px',
              fontFamily: 'var(--font-mono)',
              marginBottom: '6px',
              color: 'var(--text-muted)',
            }}
          >
            <span>XP TO NEXT LEVEL</span>
            <span style={{ color: 'var(--accent)', fontWeight: 600 }}>
              {user.stats.currentXP.toLocaleString()} / {user.stats.nextLevelXP.toLocaleString()}
            </span>
          </div>
          <div className="neu-progress-track">
            <div className="neu-progress-fill" style={{ width: `${xpPercent}%` }} />
          </div>
        </div>
      </div>

      <div className="neu-divider" style={{ margin: '2px 0' }} />

      {/* Active Challenge Cluster — Real Demo Challenge */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '18px',
        }}
      >
        <div style={{ flex: '1 1 400px' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '11px',
              fontFamily: 'var(--font-mono)',
              color: 'var(--accent)',
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: '0.04em',
              marginBottom: '4px',
            }}
          >
            <Sparkles size={13} />
            <span>
              {hasSolvedDemo
                ? 'Development Demo • Verified'
                : 'Development Demo • Ready to Start'}
            </span>
          </div>
          <div style={{ fontSize: '16px', fontWeight: 600, color: 'var(--text-main)' }}>
            Two-Input AND Gate (Development Demo)
          </div>
          <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '2px' }}>
            {hasSolvedDemo
              ? 'All 4 boolean vectors passed. Review module or practice authoring in Admin panel.'
              : 'Implement continuous assignment logic: a & b (+40 XP).'}
          </div>
        </div>

        {/* Primary Call to Action */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <button
            onClick={() => openChallenge('and-gate-demo')}
            className="neu-btn neu-btn-primary"
            style={{ padding: '10px 20px', fontSize: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}
          >
            {hasSolvedDemo ? <CheckCircle2 size={16} /> : null}
            <span>{hasSolvedDemo ? 'Review Demo' : 'Start Demo'}</span>
            <ArrowRight size={16} />
          </button>
        </div>
      </div>
    </div>
  );
};
