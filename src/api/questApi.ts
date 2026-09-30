/* ==========================================================================
   VeriQuest API — Quests, Badges & Leaderboard Services
   Connected to API client with graceful fallback
   ========================================================================== */

import { Quest, Badge, LeaderboardEntry } from '../types/quest';
import { sessionSnapshot, isCurrentSession } from './sessionBoundary';
import { api } from './client';
import { MOCK_QUESTS, MOCK_LEADERBOARD } from './mockData';

export const questApi = {
  async getQuests(): Promise<Quest[]> {
    const snapshot = sessionSnapshot();
    try {
      const { data, error } = await api.quests.getQuests();
      if (!isCurrentSession(snapshot)) return [];
      if (data && !error && data.quests) {
        return data.quests.map((q: any) => ({
          id: q.id,
          title: q.title,
          description: q.description,
          category: q.category,
          status: q.status || 'UNLOCKED',
          progressPercent: q.progress_percent || q.progressPercent || 0,
          completedChallenges: q.completed_challenges || q.completedChallenges || 0,
          totalChallenges: q.total_challenges || q.totalChallenges || 1,
          xpReward: q.xp_reward || q.xpReward || 50,
          challenges: q.challenges || [],
        }));
      }
    } catch {
      // Backend offline — proceed to fallback
    }

    return [];
  },

  async getCurrentQuest(): Promise<Quest> {
    const quests = await this.getQuests();
    return quests[0] || { ...MOCK_QUESTS[0], status: 'LOCKED', progressPercent: 0, completedChallenges: 0, title: 'No server quest available' };
  },
};

export const badgeApi = {
  async getBadges(): Promise<Badge[]> {
    const snapshot = sessionSnapshot();
    try {
      const { data, error } = await api.badges.getBadges();
      if (!isCurrentSession(snapshot)) return [];
      if (data && !error && data.badges) {
        return data.badges.map((b: any) => ({
          id: b.id,
          name: b.name,
          description: b.description,
          category: b.category,
          icon: b.icon,
          unlocked: Boolean(b.unlocked),
          unlockedAt: b.unlocked_at || b.unlockedAt,
          requirement: b.requirement,
        }));
      }
    } catch {
      // Backend offline — proceed to fallback
    }

    return [];
  },
};

export const leaderboardApi = {
  async getLeaderboard(tab: 'global' | 'weekly' | 'monthly' = 'global'): Promise<LeaderboardEntry[]> {
    const snapshot = sessionSnapshot();
    try {
      const { data, error } = await api.leaderboard.getLeaderboard(tab);
      if (!isCurrentSession(snapshot)) return [];
      if (data && !error && data.entries) {
        return data.entries.map((e: any) => ({
          rank: Number(e.rank),
          userId: e.user_id || e.userId,
          username: e.username,
          level: Number(e.level ?? 1),
          xp: Number(e.xp ?? 0),
          solvedCount: Number(e.solved_count ?? e.solvedCount ?? 0),
          isCurrentUser: Boolean(e.is_current_user ?? e.isCurrentUser),
        }));
      }
    } catch {
      // Backend offline — proceed to fallback
    }

    if (!isCurrentSession(snapshot) || snapshot.identity) return [];
    if (tab === 'weekly') {
      return MOCK_LEADERBOARD.map((entry, i) => ({
        ...entry,
        rank: i + 1,
        xp: Math.round(entry.xp * 0.35),
        solvedCount: Math.round(entry.solvedCount * 0.25),
      }));
    }
    return MOCK_LEADERBOARD;
  },
};
