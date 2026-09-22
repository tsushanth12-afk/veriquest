/* ==========================================================================
   VeriQuest Workspace — Problem Panel (LeetCode-Style Clean Tabs)
   ========================================================================== */

import React, { useState } from 'react';
import { PublicChallenge } from '../../types/challenge';
import { DifficultyBadge } from '../common/DifficultyBadge';
import { XPBadge } from '../common/XPBadge';
import { BookOpen, History, HelpCircle, Target, CheckCircle2, ChevronRight, XCircle } from 'lucide-react';
import { MOCK_SUBMISSIONS } from '../../api/mockData';

interface ProblemPanelProps {
  challenge: PublicChallenge;
}

export const ProblemPanel: React.FC<ProblemPanelProps> = ({ challenge }) => {
  const [activeTab, setActiveTab] = useState<'description' | 'submissions' | 'hints'>('description');
  const [revealedHints, setRevealedHints] = useState<number[]>([0]);

  const toggleHint = (index: number) => {
    setRevealedHints((prev) =>
      prev.includes(index) ? prev.filter((i) => i !== index) : [...prev, index]
    );
  };

  const challengeSubmissions = MOCK_SUBMISSIONS.filter(
    (s) => s.challengeId === challenge.id || challenge.solved
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* LeetCode-style Clean Tab Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '4px',
          padding: '6px 12px',
          borderBottom: '1px solid var(--border-subtle)',
          backgroundColor: 'var(--surface)',
          flexShrink: 0,
        }}
      >
        <button
          onClick={() => setActiveTab('description')}
          className={`neu-btn ${activeTab === 'description' ? 'neu-btn-primary' : 'neu-btn-ghost'}`}
          style={{ padding: '4px 10px', fontSize: '11px', gap: '5px' }}
        >
          <BookOpen size={13} />
          <span>Description</span>
        </button>

        <button
          onClick={() => setActiveTab('submissions')}
          className={`neu-btn ${activeTab === 'submissions' ? 'neu-btn-primary' : 'neu-btn-ghost'}`}
          style={{ padding: '4px 10px', fontSize: '11px', gap: '5px' }}
        >
          <History size={13} />
          <span>Submissions</span>
        </button>

        <button
          onClick={() => setActiveTab('hints')}
          className={`neu-btn ${activeTab === 'hints' ? 'neu-btn-primary' : 'neu-btn-ghost'}`}
          style={{ padding: '4px 10px', fontSize: '11px', gap: '5px' }}
        >
          <HelpCircle size={13} />
          <span>Hints ({challenge.hints.length})</span>
        </button>
      </div>

      {/* Tab Contents */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '18px 20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {activeTab === 'description' && (
          <>
            {/* Title & Metadata */}
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                <DifficultyBadge difficulty={challenge.difficulty} />
                <XPBadge xp={challenge.xp} />
                <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                  Level {challenge.level} • {challenge.category}
                </span>
              </div>
              <h1 style={{ fontSize: '18px', margin: 0, color: 'var(--text-main)' }}>
                {challenge.title}
              </h1>
            </div>

            <div className="neu-divider" style={{ margin: '2px 0' }} />

            {/* Problem Statement */}
            <div>
              <h3 style={{ fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--text-muted)', marginBottom: '6px' }}>
                Specification
              </h3>
              <p style={{ fontSize: '13px', lineHeight: 1.6, color: 'var(--text-main)', margin: 0 }}>
                {challenge.description}
              </p>
            </div>

            {/* Learning Objective */}
            <div
              className="neu-inset"
              style={{
                padding: '10px 12px',
                borderRadius: 'var(--radius-sm)',
                display: 'flex',
                gap: '8px',
                alignItems: 'flex-start',
              }}
            >
              <Target size={15} style={{ color: 'var(--accent)', flexShrink: 0, marginTop: '2px' }} />
              <div>
                <div style={{ fontSize: '10px', fontWeight: 600, color: 'var(--accent)', textTransform: 'uppercase' }}>
                  Learning Target
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-main)', marginTop: '2px' }}>
                  {challenge.learningObjective}
                </div>
              </div>
            </div>

            {/* I/O Pin Specifications */}
            <div>
              <h3 style={{ fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--text-muted)', marginBottom: '6px' }}>
                Module Ports & Pins
              </h3>
              <div className="neu-inset" style={{ borderRadius: 'var(--radius-sm)', overflow: 'hidden' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: '10px' }}>
                      <th style={{ padding: '6px 10px', textAlign: 'left' }}>PORT</th>
                      <th style={{ padding: '6px 10px', textAlign: 'left' }}>DIR</th>
                      <th style={{ padding: '6px 10px', textAlign: 'left' }}>WIDTH</th>
                      <th style={{ padding: '6px 10px', textAlign: 'left' }}>DESCRIPTION</th>
                    </tr>
                  </thead>
                  <tbody>
                    {challenge.ioPins.map((pin, i) => (
                      <tr key={i} style={{ borderBottom: i < challenge.ioPins.length - 1 ? '1px solid var(--border-subtle)' : 'none' }}>
                        <td style={{ padding: '6px 10px', fontFamily: 'var(--font-mono)', color: 'var(--accent)', fontWeight: 600 }}>
                          {pin.name}
                        </td>
                        <td style={{ padding: '6px 10px', fontFamily: 'var(--font-mono)' }}>
                          <span style={{ color: pin.direction === 'input' ? 'var(--status-sage)' : 'var(--accent)' }}>
                            {pin.direction}
                          </span>
                        </td>
                        <td style={{ padding: '6px 10px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                          {pin.width}
                        </td>
                        <td style={{ padding: '6px 10px', color: 'var(--text-muted)', fontSize: '11px' }}>
                          {pin.description}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Test Examples */}
            <div>
              <h3 style={{ fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--text-muted)', marginBottom: '6px' }}>
                Sample Test Vectors
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {challenge.examples.map((ex, i) => (
                  <div
                    key={i}
                    className="neu-inset"
                    style={{ padding: '8px 12px', borderRadius: 'var(--radius-sm)', fontFamily: 'var(--font-mono)', fontSize: '11px' }}
                  >
                    <div><span style={{ color: 'var(--text-muted)' }}>Input:  </span><span style={{ color: 'var(--text-main)' }}>{ex.input}</span></div>
                    <div><span style={{ color: 'var(--text-muted)' }}>Output: </span><span style={{ color: 'var(--status-success)' }}>{ex.expectedOutput}</span></div>
                    {ex.explanation && (
                      <div style={{ fontSize: '10px', color: 'var(--text-dim)', marginTop: '2px', fontFamily: 'var(--font-sans)' }}>
                        Note: {ex.explanation}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Constraints */}
            <div>
              <h3 style={{ fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--text-muted)', marginBottom: '6px' }}>
                Constraints
              </h3>
              <ul style={{ paddingLeft: '18px', margin: 0, fontSize: '12px', color: 'var(--text-muted)', display: 'flex', flexDirection: 'column', gap: '3px' }}>
                {challenge.constraints.map((c, i) => (
                  <li key={i}>{c}</li>
                ))}
              </ul>
            </div>
          </>
        )}

        {activeTab === 'submissions' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              History of module synthesis and testbench execution runs for this challenge:
            </div>

            {challengeSubmissions.length > 0 ? (
              challengeSubmissions.map((sub) => (
                <div
                  key={sub.id}
                  className="neu-card-sm"
                  style={{
                    padding: '12px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    {sub.status === 'ACCEPTED' ? (
                      <CheckCircle2 size={16} style={{ color: 'var(--status-success)' }} />
                    ) : (
                      <XCircle size={16} style={{ color: 'var(--status-error)' }} />
                    )}
                    <div>
                      <div style={{ fontWeight: 600, fontSize: '12px', color: sub.status === 'ACCEPTED' ? 'var(--status-success)' : 'var(--status-error)' }}>
                        {sub.status}
                      </div>
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                        {sub.testsPassed} / {sub.totalTests} vectors passed • {sub.timeAgo}
                      </div>
                    </div>
                  </div>
                  <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--accent)' }}>
                    +{sub.xp} XP
                  </span>
                </div>
              ))
            ) : (
              <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '12px' }}>
                No prior submissions recorded for this module. Submit your code to begin.
              </div>
            )}
          </div>
        )}

        {activeTab === 'hints' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              Progressive hints to guide your RTL architecture without giving away the exact solution:
            </div>

            {challenge.hints.map((hint, i) => {
              const isRevealed = revealedHints.includes(i);
              return (
                <div key={i} className="neu-card-sm" style={{ padding: '12px' }}>
                  <div
                    onClick={() => toggleHint(i)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      cursor: 'pointer',
                      fontWeight: 600,
                      fontSize: '12px',
                      color: isRevealed ? 'var(--accent)' : 'var(--text-main)',
                    }}
                  >
                    <span>Hint {i + 1}</span>
                    <ChevronRight
                      size={14}
                      style={{
                        transform: isRevealed ? 'rotate(90deg)' : 'none',
                        transition: 'transform var(--transition-fast)',
                      }}
                    />
                  </div>
                  {isRevealed && (
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '8px', lineHeight: 1.5 }}>
                      {hint}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
