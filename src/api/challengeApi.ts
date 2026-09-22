/* ==========================================================================
   VeriQuest API — Challenge Services (Connected to API Client with Fallback)
   ========================================================================== */

import { PublicChallenge, Difficulty, ChallengeCategory } from '../types/challenge';
import { api } from './client';
import { MOCK_CHALLENGES } from './mockData';

export interface ChallengeFilters {
  search?: string;
  difficulty?: Difficulty | 'All';
  category?: ChallengeCategory | 'All';
  status?: 'All' | 'Solved' | 'Unsolved';
}

export function normalizeChallenge(raw: any): PublicChallenge {
  return {
    id: raw.id,
    slug: raw.slug,
    title: raw.title,
    description: raw.description || '',
    category: raw.category || 'Fundamentals',
    difficulty: raw.difficulty || 'Easy',
    level: raw.level ?? raw.level_number ?? 1,
    xp: raw.xp ?? raw.xp_reward ?? 50,
    estimatedMinutes: raw.estimatedMinutes ?? raw.estimated_minutes ?? 15,
    starterCode: raw.starterCode ?? raw.starter_code ?? '',
    learningObjective: raw.learningObjective ?? raw.learning_objective ?? '',
    constraints: Array.isArray(raw.constraints) ? raw.constraints : [],
    ioPins: (raw.ioPins || raw.io_pins || []).map((pin: any) => ({
      name: pin.name,
      direction: pin.direction,
      width: pin.width,
      description: pin.description,
    })),
    examples: (raw.examples || raw.public_examples || []).map((ex: any) => ({
      input: ex.input,
      expectedOutput: ex.expectedOutput || ex.output || ex.expected_output || '',
      explanation: ex.explanation,
    })),
    hints: Array.isArray(raw.hints) ? raw.hints : [],
    solved: Boolean(raw.solved),
    attemptsCount: raw.attemptsCount ?? raw.attempts_count ?? 0,
    acceptanceRate: raw.acceptanceRate ?? raw.acceptance_rate ?? 0,
  };
}

export const challengeApi = {
  async getChallenges(filters?: ChallengeFilters): Promise<PublicChallenge[]> {
    try {
      const { data, error } = await api.challenges.getChallenges({
        search: filters?.search,
        difficulty: filters?.difficulty !== 'All' ? filters?.difficulty : undefined,
        category: filters?.category !== 'All' ? filters?.category : undefined,
        status: filters?.status !== 'All' ? filters?.status : undefined,
      });

      if (data && !error && data.challenges && data.challenges.length > 0) {
        return data.challenges.map(normalizeChallenge);
      }
    } catch {
      // Backend offline or error — proceed to local fallback
    }

    // Local fallback for offline/development mode
    let results = MOCK_CHALLENGES.map(normalizeChallenge);

    if (filters?.search) {
      const q = filters.search.toLowerCase();
      results = results.filter(
        (c) =>
          c.title.toLowerCase().includes(q) ||
          c.description.toLowerCase().includes(q) ||
          c.category.toLowerCase().includes(q)
      );
    }

    if (filters?.difficulty && filters.difficulty !== 'All') {
      results = results.filter((c) => c.difficulty === filters.difficulty);
    }

    if (filters?.category && filters.category !== 'All') {
      results = results.filter((c) => c.category === filters.category);
    }

    if (filters?.status && filters.status !== 'All') {
      if (filters.status === 'Solved') {
        results = results.filter((c) => c.solved);
      } else if (filters.status === 'Unsolved') {
        results = results.filter((c) => !c.solved);
      }
    }

    return results;
  },

  async getChallengeById(id: string): Promise<PublicChallenge | null> {
    try {
      const { data, error } = await api.challenges.getChallengeBySlug(id);
      if (data && !error) {
        return normalizeChallenge(data);
      }
    } catch {
      // Backend offline or error — proceed to local fallback
    }

    const found = MOCK_CHALLENGES.find(
      (c) => c.id === id || c.slug === id || (id === 'and-gate-demo' && c.slug === 'and-gate-demo')
    );
    return found ? normalizeChallenge(found) : null;
  },
};
