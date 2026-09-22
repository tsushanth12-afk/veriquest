/* ==========================================================================
   VeriQuest Dashboard — Key Telemetry Stat Strip
   ========================================================================== */

import React from 'react';
import { useApp } from '../../context/AppContext';
import { Layers, Zap, CheckCircle2, Flame } from 'lucide-react';

export const StatStrip: React.FC = () => {
  const { user } = useApp();
  const { stats } = user;

  const statItems = [
    {
      label: 'LEVEL',
      value: `0${stats.level}`,
      subtext: stats.levelTitle,
      icon: Layers,
    },
    {
      label: 'TOTAL XP',
      value: stats.currentXP.toLocaleString(),
      subtext: `Rank #${stats.globalRank}`,
      icon: Zap,
    },
    {
      label: 'SOLVED',
      value: stats.totalSolved.toString(),
      subtext: `${stats.acceptanceRate}% Acceptance`,
      icon: CheckCircle2,
    },
    {
      label: 'STREAK',
      value: `${stats.currentStreak} DAYS`,
      subtext: `Best: ${stats.longestStreak} Days`,
      icon: Flame,
    },
  ];

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: '16px',
      }}
    >
      {statItems.map((item, idx) => {
        const Icon = item.icon;
        return (
          <div
            key={idx}
            className="neu-card"
            style={{
              padding: '16px 20px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <div>
              <div
                style={{
                  fontSize: '11px',
                  fontFamily: 'var(--font-mono)',
                  fontWeight: 600,
                  color: 'var(--text-muted)',
                  letterSpacing: '0.06em',
                }}
              >
                {item.label}
              </div>
              <div
                style={{
                  fontSize: '22px',
                  fontFamily: 'var(--font-mono)',
                  fontWeight: 700,
                  color: 'var(--text-main)',
                  marginTop: '2px',
                  lineHeight: 1.1,
                }}
              >
                {item.value}
              </div>
              <div
                style={{
                  fontSize: '11px',
                  color: 'var(--text-muted)',
                  marginTop: '4px',
                }}
              >
                {item.subtext}
              </div>
            </div>

            <div
              className="neu-inset"
              style={{
                width: '38px',
                height: '38px',
                borderRadius: 'var(--radius-sm)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--accent)',
              }}
            >
              <Icon size={18} strokeWidth={2} />
            </div>
          </div>
        );
      })}
    </div>
  );
};
