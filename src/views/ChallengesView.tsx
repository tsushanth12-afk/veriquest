/* ==========================================================================
   VeriQuest View — Challenge Library (Catalog with Loading/Empty/Error States)
   ========================================================================== */

import React, { useState, useEffect, useCallback } from 'react';
import { useApp } from '../context/AppContext';
import { challengeApi } from '../api/challengeApi';
import { PublicChallenge, Difficulty, ChallengeCategory } from '../types/challenge';
import { DifficultyBadge } from '../components/common/DifficultyBadge';
import { XPBadge } from '../components/common/XPBadge';
import { Search, CheckCircle2, ArrowRight, Clock, Loader2, AlertTriangle, Sparkles } from 'lucide-react';

export const ChallengesView: React.FC = () => {
  const { openChallenge, searchQuery, setSearchQuery } = useApp();
  const [challenges, setChallenges] = useState<PublicChallenge[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [selectedDifficulty, setSelectedDifficulty] = useState<Difficulty | 'All'>('All');
  const [selectedCategory, setSelectedCategory] = useState<ChallengeCategory | 'All'>('All');
  const [selectedStatus, setSelectedStatus] = useState<'All' | 'Solved' | 'Unsolved'>('All');

  const fetchChallenges = useCallback(() => {
    setIsLoading(true);
    setErrorMessage(null);

    challengeApi
      .getChallenges({
        search: searchQuery,
        difficulty: selectedDifficulty,
        category: selectedCategory,
        status: selectedStatus,
      })
      .then((data) => {
        setChallenges(data);
        setIsLoading(false);
      })
      .catch(() => {
        setErrorMessage('Unable to load challenge catalog. Please try again.');
        setIsLoading(false);
      });
  }, [searchQuery, selectedDifficulty, selectedCategory, selectedStatus]);

  useEffect(() => {
    fetchChallenges();
  }, [fetchChallenges]);

  const categories: (ChallengeCategory | 'All')[] = [
    'All',
    'Fundamentals',
    'Combinational Logic',
    'Sequential Logic',
    'Finite State Machines',
    'Advanced HDL',
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Header & Filter Bar */}
      <div className="neu-card" style={{ padding: '24px 28px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <div>
          <h1 style={{ fontSize: '22px', margin: 0 }}>Verilog Challenge Library</h1>
          <p style={{ margin: '4px 0 0 0', fontSize: '13px', color: 'var(--text-muted)' }}>
            Practice real digital logic design, write synthesizable RTL, and verify with automated testbenches.
          </p>
        </div>

        {/* Filter Controls Row */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', alignItems: 'center', justifyContent: 'space-between' }}>
          {/* Search */}
          <div className="neu-inset" style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 12px', width: '280px' }}>
            <Search size={15} style={{ color: 'var(--text-muted)' }} />
            <input
              type="text"
              placeholder="Search challenges..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{ background: 'none', border: 'none', outline: 'none', fontSize: '13px', width: '100%', color: 'var(--text-main)' }}
            />
          </div>

          {/* Difficulty Filters */}
          <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>DIFF:</span>
            {(['All', 'Easy', 'Medium', 'Hard'] as (Difficulty | 'All')[]).map((d) => (
              <button
                key={d}
                onClick={() => setSelectedDifficulty(d)}
                className={`neu-btn ${selectedDifficulty === d ? 'neu-btn-primary' : ''}`}
                style={{ padding: '4px 10px', fontSize: '11px' }}
              >
                {d}
              </button>
            ))}
          </div>

          {/* Status Filters */}
          <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>STATUS:</span>
            {(['All', 'Solved', 'Unsolved'] as const).map((s) => (
              <button
                key={s}
                onClick={() => setSelectedStatus(s)}
                className={`neu-btn ${selectedStatus === s ? 'neu-btn-primary' : ''}`}
                style={{ padding: '4px 10px', fontSize: '11px' }}
              >
                {s}
              </button>
            ))}
          </div>
        </div>

        {/* Category Pills */}
        <div style={{ display: 'flex', gap: '8px', overflowX: 'auto', paddingBottom: '4px' }}>
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`neu-badge ${selectedCategory === cat ? 'neu-btn-primary' : 'neu-btn-ghost'}`}
              style={{ padding: '4px 10px', cursor: 'pointer', border: '1px solid var(--border-subtle)' }}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* Content Area: Loading, Error, Empty, or Cards Grid */}
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
          <span style={{ fontSize: '13px' }}>Loading Verilog challenges...</span>
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
            onClick={fetchChallenges}
            className="neu-btn neu-btn-primary"
            style={{ padding: '6px 14px', fontSize: '12px' }}
          >
            Retry
          </button>
        </div>
      ) : challenges.length === 0 ? (
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
          <span style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-main)' }}>
            No challenges found
          </span>
          <p style={{ margin: 0, fontSize: '12px', maxWidth: '320px', lineHeight: 1.5 }}>
            No challenges match your current search criteria or category filter. Try clearing filters.
          </p>
          <button
            onClick={() => {
              setSearchQuery('');
              setSelectedDifficulty('All');
              setSelectedCategory('All');
              setSelectedStatus('All');
            }}
            className="neu-btn"
            style={{ padding: '6px 14px', fontSize: '12px', marginTop: '6px' }}
          >
            Clear Filters
          </button>
        </div>
      ) : (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
            gap: '18px',
          }}
        >
          {challenges.map((c) => {
            const isDemo = c.slug === 'and-gate-demo' || c.category === 'Development Demo';

            return (
              <div
                key={c.id}
                className="neu-card neu-card-interactive"
                onClick={() => openChallenge(c.slug || c.id)}
                style={{
                  padding: '20px',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  gap: '14px',
                  position: 'relative',
                }}
              >
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                    <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                      <DifficultyBadge difficulty={c.difficulty} />
                      <XPBadge xp={c.xp} />
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      {isDemo && (
                        <span
                          style={{
                            fontSize: '10px',
                            fontFamily: 'var(--font-mono)',
                            fontWeight: 700,
                            padding: '1px 6px',
                            borderRadius: 'var(--radius-sm)',
                            backgroundColor: 'rgba(201, 111, 74, 0.15)',
                            color: 'var(--accent)',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '3px',
                          }}
                        >
                          <Sparkles size={10} />
                          <span>DEMO</span>
                        </span>
                      )}

                      {c.solved && (
                        <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--status-success)', fontSize: '11px', fontWeight: 600 }}>
                          <CheckCircle2 size={13} />
                          <span>Solved</span>
                        </span>
                      )}
                    </div>
                  </div>

                  <h3 style={{ fontSize: '16px', margin: 0, color: 'var(--text-main)' }}>
                    {c.title}
                  </h3>
                  <div style={{ fontSize: '11px', color: 'var(--accent)', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
                    {c.category}
                  </div>

                  <p style={{ margin: '8px 0 0 0', fontSize: '12px', color: 'var(--text-muted)', lineHeight: 1.5, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                    {c.description}
                  </p>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: '10px', borderTop: '1px solid var(--border-subtle)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '11px', color: 'var(--text-muted)' }}>
                    <Clock size={12} />
                    <span>{c.estimatedMinutes} mins</span>
                  </div>

                  <button
                    className="neu-btn"
                    style={{ padding: '5px 10px', fontSize: '11px', gap: '4px' }}
                  >
                    <span>{c.solved ? 'Review' : 'Start'}</span>
                    <ArrowRight size={12} />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
