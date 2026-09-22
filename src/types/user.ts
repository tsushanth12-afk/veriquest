/* ==========================================================================
   VeriQuest Types — User Profile & Telemetry
   ========================================================================== */

export interface TopicMastery {
  topic: string;
  percentage: number;
  completed: number;
  total: number;
}

export interface UserStats {
  level: number;
  levelTitle: string;
  currentXP: number;
  nextLevelXP: number;
  totalSolved: number;
  easySolved: number;
  mediumSolved: number;
  hardSolved: number;
  totalAttempts: number;
  acceptanceRate: number; // e.g. 72%
  currentStreak: number;
  longestStreak: number;
  globalRank: number;
  weeklyRank: number;
  percentile: number; // e.g. 91%
}

export interface UserProfile {
  id: string;
  username: string;
  fullName: string;
  bio: string;
  avatarUrl?: string;
  joinedDate: string;
  stats: UserStats;
  topicMasteries: TopicMastery[];
}
