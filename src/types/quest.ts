/* ==========================================================================
   VeriQuest Types — Quests & Badges
   ========================================================================== */

export interface QuestChallengeRef {
  id: string;
  title: string;
  completed: boolean;
}

export interface Quest {
  id: string;
  title: string;
  category: string;
  description: string;
  progressPercent: number;
  completedChallenges: number;
  totalChallenges: number;
  xpReward: number;
  currentChallengeId?: string;
  currentChallengeTitle?: string;
  status: 'IN_PROGRESS' | 'COMPLETED' | 'LOCKED' | 'UNLOCKED';
  challenges?: QuestChallengeRef[];
}

export interface Badge {
  id: string;
  name: string;
  description: string;
  category: 'Logic' | 'Timing' | 'Consistency' | 'Synthesis' | string;
  icon: string; // Lucide icon name
  unlocked: boolean;
  unlockedAt?: string;
  requirement: string;
}

export interface LeaderboardEntry {
  rank: number;
  userId?: string;
  username: string;
  avatarText?: string;
  level: number;
  levelTitle?: string;
  xp: number;
  solvedCount: number;
  isCurrentUser?: boolean;
}

