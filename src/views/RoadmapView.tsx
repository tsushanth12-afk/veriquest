/* ==========================================================================
   VeriQuest View — Learning Roadmap (Dynamic Database-Driven Skill Tree)
   Calculated from published challenges and authentic user progress
   ========================================================================== */

import React, { useState, useEffect } from 'react';
import { useApp } from '../context/AppContext';
import { challengeApi } from '../api/challengeApi';
import { PublicChallenge } from '../types/challenge';
import {
  Lock,
  ArrowRight,
  Compass,
  Cpu,
  Layers,
  Workflow,
  Sparkles,
  CheckCircle2,
  Loader2,
  Info,
} from 'lucide-react';

export const RoadmapView: React.FC = () => {
  const { openChallenge } = useApp();
  const [challenges, setChallenges] = useState<PublicChallenge[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    challengeApi
      .getChallenges()
      .then((data) => {
        setChallenges(data || []);
        setIsLoading(false);
      })
      .catch(() => {
        setIsLoading(false);
      });
  }, []);

  const stageTemplates = [
    {
      level: 1,
      title: 'Verilog Foundations (Development Demo)',
      category: 'Fundamentals',
      icon: Compass,
      description:
        'Master continuous assignments, wire declaration, boolean primitives, bitwise logic, and reduction operators.',
    },
    {
      level: 2,
      title: 'Combinational Logic',
      category: 'Combinational Logic',
      icon: Cpu,
      description:
        'Design multiplexers, priority encoders, decoders, ripple-carry adders, and ALUs without latch inferences.',
    },
    {
      level: 3,
      title: 'Sequential Logic',
      category: 'Sequential Logic',
      icon: Layers,
      description:
        'Clocked D flip-flops, synchronous resets, shift registers, Johnson counters, and timing closure fundamentals.',
    },
    {
      level: 4,
      title: 'Finite State Machines',
      category: 'Finite State Machines',
      icon: Workflow,
      description:
        'Mealy and Moore state controllers, one-hot vs binary state encoding, traffic light systems, and UART transceivers.',
    },
    {
      level: 5,
      title: 'Advanced HDL & Memory',
      category: 'Advanced HDL',
      icon: Sparkles,
      description:
        'Parameterized synchronous FIFOs, dual-port Block RAM controllers, and AXI4-Lite bus interfaces.',
    },
  ];

  // Dynamically compute progress per stage from real challenges
  const stages = stageTemplates.map((template, index) => {
    const stageChallenges = challenges.filter(
      (c) =>
        c.category === template.category ||
        (template.category === 'Fundamentals' &&
          (c.category === 'Development Demo' || c.slug === 'and-gate-demo'))
    );
    const total = stageChallenges.length;
    const completed = stageChallenges.filter((c) => c.solved).length;
    const completionPercent = total > 0 ? Math.round((completed / total) * 100) : 0;

    let status: 'COMPLETED' | 'IN_PROGRESS' | 'UNLOCKED' | 'LOCKED' = 'LOCKED';
    if (total === 0) {
      status = 'LOCKED';
    } else if (completed === total) {
      status = 'COMPLETED';
    } else if (completed > 0) {
      status = 'IN_PROGRESS';
    } else if (index === 0) {
      status = 'UNLOCKED';
    } else {
      status = 'LOCKED';
    }

    const firstChallenge = stageChallenges[0];

    return {
      ...template,
      totalChallenges: total,
      completedChallenges: completed,
      completionPercent,
      status,
      firstChallengeId: firstChallenge ? (firstChallenge.slug || firstChallenge.id) : 'and-gate-demo',
    };
  });

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
          SILICON ARCHITECT PROGRESSION PATH
        </div>
        <h1 style={{ fontSize: '22px', margin: 0 }}>HDL Learning Roadmap</h1>
        <p style={{ margin: '6px 0 0 0', fontSize: '13px', color: 'var(--text-muted)', maxWidth: '650px' }}>
          A database-driven curriculum structured into 5 foundational digital logic stages. All challenge content is administered through the VeriQuest Admin API.
        </p>

        {/* Development Demo Notice */}
        <div
          style={{
            marginTop: '14px',
            padding: '10px 14px',
            borderRadius: 'var(--radius-sm)',
            backgroundColor: 'rgba(201, 111, 74, 0.08)',
            border: '1px solid rgba(201, 111, 74, 0.2)',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            fontSize: '12px',
            color: 'var(--text-main)',
          }}
        >
          <Info size={16} style={{ color: 'var(--accent)', flexShrink: 0 }} />
          <span>
            <strong>Curriculum Note:</strong> The platform is seeded with the single proof-of-concept module (<strong>Two-Input AND Gate</strong>). Subsequent stage challenges unlock as instructors author and publish curriculum.
          </span>
        </div>
      </div>

      {/* Connected Pathway / Skill Tree */}
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
          <span style={{ fontSize: '13px' }}>Loading roadmap stages...</span>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {stages.map((stage) => {
            const Icon = stage.icon;
            const isLocked = stage.status === 'LOCKED';
            const isCompleted = stage.status === 'COMPLETED';
            const isInProgress = stage.status === 'IN_PROGRESS';

            return (
              <div
                key={stage.level}
                className="neu-card"
                style={{
                  padding: '24px 28px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '16px',
                  opacity: isLocked ? 0.65 : 1,
                  border: isCompleted
                    ? '1px solid var(--accent-subtle)'
                    : isInProgress
                    ? '1px solid var(--border-subtle)'
                    : '1px solid var(--border-subtle)',
                }}
              >
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
                        width: '48px',
                        height: '48px',
                        borderRadius: 'var(--radius-md)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: isCompleted
                          ? 'var(--status-success)'
                          : isLocked
                          ? 'var(--text-dim)'
                          : 'var(--accent)',
                      }}
                    >
                      {isCompleted ? <CheckCircle2 size={24} /> : isLocked ? <Lock size={20} /> : <Icon size={24} />}
                    </div>

                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '2px' }}>
                        <span
                          style={{
                            fontSize: '11px',
                            fontFamily: 'var(--font-mono)',
                            color: 'var(--text-muted)',
                            textTransform: 'uppercase',
                          }}
                        >
                          STAGE 0{stage.level} • {stage.category}
                        </span>
                        <span
                          className="neu-badge"
                          style={{
                            fontSize: '10px',
                            color: isCompleted
                              ? 'var(--status-success)'
                              : isInProgress
                              ? 'var(--accent)'
                              : 'var(--text-dim)',
                          }}
                        >
                          {stage.totalChallenges === 0
                            ? 'IN DEVELOPMENT'
                            : stage.status.replace('_', ' ')}
                        </span>
                      </div>

                      <h3 style={{ fontSize: '17px', margin: 0, color: 'var(--text-main)' }}>
                        {stage.title}
                      </h3>
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
                    <div style={{ minWidth: '160px' }}>
                      <div
                        style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          fontSize: '11px',
                          fontFamily: 'var(--font-mono)',
                          marginBottom: '6px',
                        }}
                      >
                        <span style={{ color: 'var(--text-muted)' }}>COMPLETION</span>
                        <span style={{ fontWeight: 600, color: isCompleted ? 'var(--status-success)' : 'var(--accent)' }}>
                          {stage.completionPercent}% ({stage.completedChallenges}/{stage.totalChallenges})
                        </span>
                      </div>
                      <div className="neu-progress-track">
                        <div
                          className={`neu-progress-fill ${isCompleted ? 'neu-progress-fill-success' : ''}`}
                          style={{ width: `${stage.completionPercent}%` }}
                        />
                      </div>
                    </div>

                    {!isLocked && stage.totalChallenges > 0 ? (
                      <button
                        onClick={() => openChallenge(stage.firstChallengeId)}
                        className={`neu-btn ${isCompleted ? 'neu-btn-ghost' : 'neu-btn-primary'}`}
                        style={{ padding: '8px 14px', fontSize: '12px' }}
                      >
                        <span>{isCompleted ? 'Review' : 'Continue'}</span>
                        <ArrowRight size={13} />
                      </button>
                    ) : (
                      <div
                        style={{
                          fontSize: '11px',
                          fontFamily: 'var(--font-mono)',
                          color: 'var(--text-dim)',
                          padding: '6px 12px',
                        }}
                      >
                        {stage.totalChallenges === 0 ? 'Pending Authorship' : 'Locked'}
                      </div>
                    )}
                  </div>
                </div>

                <p style={{ margin: 0, fontSize: '13px', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                  {stage.description}
                </p>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
