/* ==========================================================================
   VeriQuest View — Leaderboard (Global / Weekly / Monthly)
   With loading, empty, and error boundaries
   ========================================================================== */

import React, { useState, useEffect, useCallback } from 'react';
import { leaderboardApi } from '../api/questApi';
import { LeaderboardEntry } from '../types/quest';
import { Trophy, Medal, Award, Loader2, AlertTriangle } from 'lucide-react';

export const LeaderboardView: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'global' | 'weekly' | 'monthly'>('global');
  const [entries, setEntries] = useState<LeaderboardEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const fetchLeaderboard = useCallback(() => {
    setIsLoading(true);
    setErrorMessage(null);

    leaderboardApi
      .getLeaderboard(activeTab)
      .then((data) => {
        setEntries(data || []);
        setIsLoading(false);
      })
      .catch(() => {
        setErrorMessage('Failed to load leaderboard data. Please try again.');
        setIsLoading(false);
      });
  }, [activeTab]);

  useEffect(() => {
    fetchLeaderboard();
  }, [fetchLeaderboard]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Header & Tabs */}
      <div
        className="neu-card"
        style={{
          padding: '24px 28px',
          display: 'flex',
          flexWrap: 'wrap',
          justifyContent: 'space-between',
          alignItems: 'center',
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
            VERIFICATION RANKINGS
          </div>
          <h1 style={{ fontSize: '22px', margin: 0 }}>Silicon Architecture Standings</h1>
          <p style={{ margin: '4px 0 0 0', fontSize: '13px', color: 'var(--text-muted)' }}>
            Ranked by automated testbench verification XP and challenge consistency.
          </p>
        </div>

        {/* Tabs */}
        <div
          className="neu-inset"
          style={{ display: 'flex', padding: '4px', gap: '4px', borderRadius: 'var(--radius-sm)' }}
        >
          {(['global', 'weekly', 'monthly'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`neu-btn ${activeTab === tab ? 'neu-btn-primary' : 'neu-btn-ghost'}`}
              style={{
                padding: '6px 14px',
                fontSize: '12px',
                textTransform: 'capitalize',
                border: 'none',
                boxShadow: activeTab === tab ? 'var(--shadow-raised-sm)' : 'none',
              }}
            >
              {tab}
            </button>
          ))}
        </div>
      </div>

      {/* Leaderboard Table Area */}
      <div className="neu-card" style={{ padding: '20px', overflowX: 'auto' }}>
        {isLoading ? (
          <div
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
            <span style={{ fontSize: '13px' }}>Loading verification standings...</span>
          </div>
        ) : errorMessage ? (
          <div
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
              onClick={fetchLeaderboard}
              className="neu-btn neu-btn-primary"
              style={{ padding: '6px 14px', fontSize: '12px' }}
            >
              Retry
            </button>
          </div>
        ) : entries.length === 0 ? (
          <div
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
            <Trophy size={28} style={{ color: 'var(--accent)', opacity: 0.6 }} />
            <span style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-main)' }}>
              No rankings recorded yet
            </span>
            <p style={{ margin: 0, fontSize: '12px', maxWidth: '320px', lineHeight: 1.5 }}>
              Be the first to solve a challenge and claim the top position on the VeriQuest leaderboard!
            </p>
          </div>
        ) : (
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
                <th style={{ padding: '10px 14px', width: '60px' }}>RANK</th>
                <th style={{ padding: '10px 14px' }}>ENGINEER</th>
                <th style={{ padding: '10px 14px' }}>LEVEL & TIER</th>
                <th style={{ padding: '10px 14px' }}>TOTAL XP</th>
                <th style={{ padding: '10px 14px', textAlign: 'right' }}>SOLVED</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry) => {
                const isTop3 = entry.rank <= 3;
                const isCurrent = entry.isCurrentUser;
                const avatar = entry.avatarText || (entry.username ? entry.username.slice(0, 2).toUpperCase() : 'EE');

                return (
                  <tr
                    key={entry.rank}
                    style={{
                      borderBottom: '1px solid var(--border-subtle)',
                      backgroundColor: isCurrent ? 'var(--accent-subtle)' : 'transparent',
                      fontWeight: isCurrent ? 600 : 400,
                    }}
                  >
                    <td style={{ padding: '14px', verticalAlign: 'middle', fontFamily: 'var(--font-mono)' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        {entry.rank === 1 && <Trophy size={14} style={{ color: 'var(--status-warning)' }} />}
                        {entry.rank === 2 && <Medal size={14} style={{ color: 'var(--text-muted)' }} />}
                        {entry.rank === 3 && <Award size={14} style={{ color: 'var(--accent-secondary)' }} />}
                        <span style={{ color: isTop3 ? 'var(--accent)' : 'var(--text-main)', fontWeight: isTop3 ? 700 : 500 }}>
                          #{entry.rank}
                        </span>
                      </div>
                    </td>

                    <td style={{ padding: '14px', verticalAlign: 'middle' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <div
                          className="avatar-chip"
                          style={{
                            backgroundColor: isCurrent ? 'var(--accent)' : 'var(--surface-hover)',
                            color: isCurrent ? '#FFFFFF' : 'var(--text-main)',
                            border: '1px solid var(--border-subtle)',
                          }}
                        >
                          {avatar}
                        </div>
                        <div>
                          <div style={{ color: 'var(--text-main)' }}>
                            {entry.username} {isCurrent && <span style={{ fontSize: '11px', color: 'var(--accent)' }}>(You)</span>}
                          </div>
                        </div>
                      </div>
                    </td>

                    <td style={{ padding: '14px', verticalAlign: 'middle' }}>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', color: 'var(--text-muted)' }}>
                        Lvl {entry.level} • {entry.levelTitle || 'Hardware Engineer'}
                      </span>
                    </td>

                    <td style={{ padding: '14px', verticalAlign: 'middle', fontFamily: 'var(--font-mono)', color: 'var(--accent)', fontWeight: 600 }}>
                      {entry.xp.toLocaleString()} XP
                    </td>

                    <td style={{ padding: '14px', verticalAlign: 'middle', textAlign: 'right', fontFamily: 'var(--font-mono)', color: 'var(--text-main)' }}>
                      {entry.solvedCount} modules
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};
