/* ==========================================================================
   VeriQuest View — Profile Page
   Dynamic presentation of user progress, verification stats & milestones
   ========================================================================== */

import React, { useState, useEffect } from 'react';
import { useApp } from '../context/AppContext';
import { Calendar, Award, CheckCircle2, Terminal, Route, Flame } from 'lucide-react';
import { challengeApi } from '../api/challengeApi';
import { questApi, badgeApi } from '../api/questApi';
import { PublicChallenge } from '../types/challenge';
import { Quest, Badge } from '../types/quest';

export const ProfileView: React.FC = () => {
  const { user, openChallenge } = useApp();
  const [activeTab, setActiveTab] = useState<'Challenges' | 'Quests' | 'Achievements' | 'Activity'>('Challenges');
  const [challenges, setChallenges] = useState<PublicChallenge[]>([]);
  const [quests, setQuests] = useState<Quest[]>([]);
  const [badges, setBadges] = useState<Badge[]>([]);

  useEffect(() => {
    challengeApi.getChallenges().then(setChallenges);
    questApi.getQuests().then(setQuests);
    badgeApi.getBadges().then(setBadges);
  }, [user.stats.totalSolved]);

  const skills = [
    'Verilog HDL (IEEE 1364-2005)',
    'Combinational Synthesis',
    'Sequential Timing Closure',
    'Mealy / Moore FSMs',
    'RTL Bus Architectures',
    'Automated Testbenches',
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Top Profile Summary Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
          gap: '24px',
        }}
      >
        {/* Left Card: Identity & Bio */}
        <div className="neu-card" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <div
              className="neu-inset"
              style={{
                width: '64px',
                height: '64px',
                borderRadius: 'var(--radius-md)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '24px',
                fontWeight: 700,
                color: 'var(--accent)',
              }}
            >
              {user.username ? user.username.substring(0, 2).toUpperCase() : 'EE'}
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h1 style={{ fontSize: '20px', margin: 0 }}>{user.fullName || user.username}</h1>
                <span className="neu-badge" style={{ color: 'var(--accent)' }}>
                  Level {user.stats.level}
                </span>
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
                @{user.username.toLowerCase()} • {user.stats.levelTitle}
              </div>
            </div>
          </div>

          <p style={{ margin: 0, fontSize: '13px', color: 'var(--text-main)', lineHeight: 1.5 }}>
            {user.bio || 'Verilog digital logic design student at VeriQuest.'}
          </p>

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: 'var(--text-muted)' }}>
            <Calendar size={14} />
            <span>Member since {user.joinedDate}</span>
          </div>

          {/* Skill Chips */}
          <div style={{ marginTop: 'auto', paddingTop: '10px', borderTop: '1px solid var(--border-subtle)' }}>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginBottom: '8px' }}>
              RTL CAPABILITIES
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
              {skills.map((skill, i) => (
                <span
                  key={i}
                  className="neu-card-sm"
                  style={{
                    padding: '3px 8px',
                    fontSize: '11px',
                    fontFamily: 'var(--font-mono)',
                    color: 'var(--text-main)',
                  }}
                >
                  {skill}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* Right Card: Telemetry Summary */}
        <div className="neu-card" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <h2 style={{ fontSize: '15px', margin: 0 }}>Hardware Verification Stats</h2>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div className="neu-inset" style={{ padding: '12px', borderRadius: 'var(--radius-sm)' }}>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>TOTAL XP</div>
              <div style={{ fontSize: '20px', fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--accent)' }}>
                {user.stats.currentXP.toLocaleString()}
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-dim)' }}>Next Level at {user.stats.nextLevelXP}</div>
            </div>

            <div className="neu-inset" style={{ padding: '12px', borderRadius: 'var(--radius-sm)' }}>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>SOLVED MODULES</div>
              <div style={{ fontSize: '20px', fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--status-success)' }}>
                {user.stats.totalSolved}
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-dim)' }}>{user.stats.acceptanceRate}% Acceptance rate</div>
            </div>

            <div className="neu-inset" style={{ padding: '12px', borderRadius: 'var(--radius-sm)' }}>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>CURRENT STREAK</div>
              <div style={{ fontSize: '20px', fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--status-warning)' }}>
                {user.stats.currentStreak} Days
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-dim)' }}>Best: {user.stats.longestStreak} Days</div>
            </div>

            <div className="neu-inset" style={{ padding: '12px', borderRadius: 'var(--radius-sm)' }}>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>GLOBAL RANK</div>
              <div style={{ fontSize: '20px', fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--text-main)' }}>
                #{user.stats.globalRank || 1}
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-dim)' }}>Weekly Rank: #{user.stats.weeklyRank || 1}</div>
            </div>
          </div>

          <div style={{ marginTop: 'auto', display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: 'var(--text-muted)', borderTop: '1px solid var(--border-subtle)', paddingTop: '10px' }}>
            <span>Easy: <strong style={{ color: 'var(--status-sage)' }}>{user.stats.easySolved}</strong></span>
            <span>Medium: <strong style={{ color: 'var(--status-warning)' }}>{user.stats.mediumSolved}</strong></span>
            <span>Hard: <strong style={{ color: 'var(--status-error)' }}>{user.stats.hardSolved}</strong></span>
          </div>
        </div>
      </div>

      {/* Tabs Section */}
      <div className="neu-card" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', gap: '8px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '12px', marginBottom: '16px' }}>
          {(['Challenges', 'Quests', 'Achievements', 'Activity'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`neu-btn ${activeTab === tab ? 'neu-btn-primary' : 'neu-btn-ghost'}`}
              style={{ padding: '6px 14px', fontSize: '12px' }}
            >
              {tab}
            </button>
          ))}
        </div>

        {activeTab === 'Challenges' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {challenges.map((c: PublicChallenge) => {
              const isDemo = c.slug === 'and-gate-demo' || c.category === 'Development Demo';

              return (
                <div
                  key={c.id}
                  className="neu-card-sm neu-card-interactive"
                  onClick={() => openChallenge(c.slug || c.id)}
                  style={{
                    padding: '12px 16px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    {c.solved ? (
                      <CheckCircle2 size={16} style={{ color: 'var(--status-success)' }} />
                    ) : (
                      <Terminal size={16} style={{ color: 'var(--text-dim)' }} />
                    )}
                    <div>
                      <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-main)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span>{c.title}</span>
                        {isDemo && (
                          <span style={{ fontSize: '9px', padding: '1px 5px', borderRadius: '3px', backgroundColor: 'rgba(201, 111, 74, 0.15)', color: 'var(--accent)' }}>
                            DEMO
                          </span>
                        )}
                      </div>
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                        {c.category} • {c.difficulty}
                      </div>
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <span style={{ fontSize: '12px', fontFamily: 'var(--font-mono)', color: 'var(--accent)', fontWeight: 600 }}>
                      +{c.xp} XP
                    </span>
                    <span style={{ fontSize: '11px', color: c.solved ? 'var(--status-success)' : 'var(--text-dim)', fontWeight: 500 }}>
                      {c.solved ? 'Verified' : 'Unattempted'}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {activeTab === 'Quests' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {quests.map((q) => (
              <div
                key={q.id}
                className="neu-card-sm"
                style={{
                  padding: '12px 16px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <Route size={16} style={{ color: 'var(--accent)' }} />
                  <div>
                    <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-main)' }}>{q.title}</div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{q.category}</div>
                  </div>
                </div>
                <div style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                  {q.progressPercent}% Complete
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'Achievements' && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: '12px' }}>
            {badges.map((b) => (
              <div
                key={b.id}
                className="neu-card-sm"
                style={{
                  padding: '12px 14px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  opacity: b.unlocked ? 1 : 0.6,
                }}
              >
                <Award size={18} style={{ color: b.unlocked ? 'var(--accent)' : 'var(--text-dim)' }} />
                <div>
                  <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-main)' }}>{b.name}</div>
                  <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>{b.requirement}</div>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'Activity' && (
          <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
            <Flame size={24} style={{ color: 'var(--accent)', margin: '0 auto 8px auto', display: 'block' }} />
            <span>Active Streak: {user.stats.currentStreak} consecutive days.</span>
          </div>
        )}
      </div>
    </div>
  );
};
