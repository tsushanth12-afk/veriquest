/* ==========================================================================
   VeriQuest View — Dashboard (Minimalist & High-Value)
   ========================================================================== */

import React from 'react';
import { HeroQuestCard } from '../components/dashboard/HeroQuestCard';
import { StatStrip } from '../components/dashboard/StatStrip';
import { TopicMasteryCard } from '../components/dashboard/TopicMasteryCard';
import { ActivityCard } from '../components/dashboard/ActivityCard';
import { ChallengeHistoryTable } from '../components/dashboard/ChallengeHistoryTable';

export const DashboardView: React.FC = () => {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '24px',
      }}
    >
      {/* 1. Hero Quest & Next Action */}
      <HeroQuestCard />

      {/* 2. Key Telemetry Strip */}
      <StatStrip />

      {/* 3. Skill Mastery & Activity Grid (Two-Column Balanced Layout) */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))',
          gap: '24px',
        }}
      >
        <TopicMasteryCard />
        <ActivityCard />
      </div>

      {/* 4. Challenge History Table */}
      <ChallengeHistoryTable />
    </div>
  );
};
