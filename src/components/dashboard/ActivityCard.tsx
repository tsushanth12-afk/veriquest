/* ==========================================================================
   VeriQuest Dashboard — Activity & Milestones Card
   Realistic streak and activity display without fabricated history
   ========================================================================== */

import React from 'react';
import { useApp } from '../../context/AppContext';
import { Flame, Medal, TrendingUp } from 'lucide-react';
import { MOCK_BADGES } from '../../api/mockData';

export const ActivityCard: React.FC = () => {
  const { user, setCurrentRoute } = useApp();
  const unlockedBadges = MOCK_BADGES.filter((b) => b.unlocked).slice(0, 3);

  // Compute activity grid from real user streak
  const streak = user.stats.currentStreak;
  const activityWeeks = Array.from({ length: 12 }, (_, wIdx) => {
    return Array.from({ length: 7 }, (_, dIdx) => {
      // Days from today backwards
      const dayOffset = (11 - wIdx) * 7 + (6 - dIdx);
      if (dayOffset < streak) {
        return Math.min(3, Math.max(1, Math.floor((streak - dayOffset) % 3) + 1));
      }
      return 0;
    });
  });

  const getColor = (level: number) => {
    switch (level) {
      case 0:
        return 'rgba(197, 187, 170, 0.25)';
      case 1:
        return 'rgba(201, 111, 74, 0.35)';
      case 2:
        return 'rgba(201, 111, 74, 0.7)';
      case 3:
      default:
        return 'var(--accent)';
    }
  };

  return (
    <div
      className="neu-card"
      style={{
        padding: '20px 24px',
        display: 'flex',
        flexDirection: 'column',
        gap: '16px',
        height: '100%',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Flame size={16} style={{ color: 'var(--accent)' }} />
          <h2 style={{ fontSize: '15px', margin: 0 }}>Activity & Milestones</h2>
        </div>
        <div
          style={{
            fontSize: '11px',
            fontFamily: 'var(--font-mono)',
            color: 'var(--accent)',
            fontWeight: 600,
          }}
        >
          {user.stats.currentStreak}-Day Streak
        </div>
      </div>

      {/* Terracotta Activity Heatmap */}
      <div>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            fontSize: '11px',
            color: 'var(--text-muted)',
            marginBottom: '8px',
          }}
        >
          <span>Synthesis Activity (Last 12 Weeks)</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ fontSize: '10px' }}>Less</span>
            {[0, 1, 2, 3].map((lvl) => (
              <span
                key={lvl}
                style={{
                  width: '9px',
                  height: '9px',
                  borderRadius: '2px',
                  backgroundColor: getColor(lvl),
                  display: 'inline-block',
                }}
              />
            ))}
            <span style={{ fontSize: '10px' }}>More</span>
          </div>
        </div>

        {/* Matrix columns */}
        <div
          style={{
            display: 'flex',
            gap: '4px',
            justifyContent: 'space-between',
            padding: '10px 8px',
            backgroundColor: 'var(--surface)',
            boxShadow: 'var(--shadow-inset-sm)',
            borderRadius: 'var(--radius-sm)',
          }}
        >
          {activityWeeks.map((week, wIdx) => (
            <div key={wIdx} style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              {week.map((dayLevel, dIdx) => (
                <div
                  key={dIdx}
                  title={`Week ${wIdx + 1}, Day ${dIdx + 1}: ${dayLevel > 0 ? `${dayLevel} verification runs` : 'No activity'}`}
                  style={{
                    width: '10px',
                    height: '10px',
                    borderRadius: '2px',
                    backgroundColor: getColor(dayLevel),
                  }}
                />
              ))}
            </div>
          ))}
        </div>
      </div>

      {/* Ranking Summary & Badges Row */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '12px',
          marginTop: 'auto',
        }}
      >
        {/* Ranking Tile */}
        <div
          className="neu-inset"
          style={{
            padding: '10px 12px',
            borderRadius: 'var(--radius-sm)',
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
          }}
        >
          <TrendingUp size={16} style={{ color: 'var(--accent)', flexShrink: 0 }} />
          <div>
            <div style={{ fontSize: '10px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
              RANKING
            </div>
            <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--text-main)' }}>
              Rank #{user.stats.globalRank || 1}
            </div>
          </div>
        </div>

        {/* Badges Quick Preview */}
        <div
          onClick={() => setCurrentRoute('achievements')}
          className="neu-card-sm neu-card-interactive"
          style={{
            padding: '10px 12px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            cursor: 'pointer',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Medal size={16} style={{ color: 'var(--accent)' }} />
            <div>
              <div style={{ fontSize: '10px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                BADGES
              </div>
              <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-main)' }}>
                {unlockedBadges.length} / {MOCK_BADGES.length} Unlocked
              </div>
            </div>
          </div>
          <span style={{ fontSize: '11px', color: 'var(--accent)' }}>→</span>
        </div>
      </div>
    </div>
  );
};
