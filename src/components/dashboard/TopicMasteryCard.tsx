/* ==========================================================================
   VeriQuest Dashboard — Topic Skill Mastery
   ========================================================================== */

import React from 'react';
import { useApp } from '../../context/AppContext';
import { Cpu } from 'lucide-react';

export const TopicMasteryCard: React.FC = () => {
  const { user, setCurrentRoute } = useApp();

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
          <Cpu size={16} style={{ color: 'var(--accent)' }} />
          <h2 style={{ fontSize: '15px', margin: 0 }}>Skill Mastery</h2>
        </div>
        <button
          onClick={() => setCurrentRoute('learn')}
          className="neu-btn-ghost"
          style={{ fontSize: '11px', padding: '3px 8px' }}
        >
          View Roadmap →
        </button>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {user.topicMasteries.map((topic, i) => (
          <div key={i}>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                fontSize: '12px',
                marginBottom: '5px',
              }}
            >
              <span style={{ fontWeight: 500, color: 'var(--text-main)' }}>
                {topic.topic}
              </span>
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                  {topic.completed}/{topic.total}
                </span>
                <span
                  style={{
                    fontFamily: 'var(--font-mono)',
                    fontWeight: 600,
                    color: topic.percentage === 100 ? 'var(--status-success)' : 'var(--accent)',
                    width: '38px',
                    textAlign: 'right',
                  }}
                >
                  {topic.percentage}%
                </span>
              </div>
            </div>
            <div className="neu-progress-track">
              <div
                className={`neu-progress-fill ${topic.percentage === 100 ? 'neu-progress-fill-success' : ''}`}
                style={{ width: `${topic.percentage}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
