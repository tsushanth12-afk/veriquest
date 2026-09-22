/* ==========================================================================
   VeriQuest — Centralized Typed Frontend API Client
   
   All frontend→backend communication goes through this module.
   Organized into domain namespaces:
   - authApi
   - userApi
   - challengeApi
   - submissionApi
   - progressApi
   - questApi
   - badgeApi
   - leaderboardApi
   - adminApi

   Strictly handles 401, 403, 422, 429, and 500 error boundaries.
   Submission polling strictly caps duration at 60s per Section 6.
   ========================================================================== */

import { supabase } from '../lib/supabase';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export interface ApiError {
  code:
    | 'UNAUTHORIZED'
    | 'FORBIDDEN'
    | 'NOT_FOUND'
    | 'VALIDATION_ERROR'
    | 'RATE_LIMITED'
    | 'SYSTEM_ERROR'
    | 'NETWORK_ERROR'
    | string;
  message: string;
}

export interface ApiResponse<T> {
  data: T | null;
  error: ApiError | null;
}

/**
 * Get current Supabase session token for Bearer authentication.
 */
async function getAccessToken(): Promise<string | null> {
  try {
    const { data } = await supabase.auth.getSession();
    return data.session?.access_token || null;
  } catch {
    return null;
  }
}

/**
 * Core fetch wrapper with JWT injection, token refresh, and structured error mapping.
 */
async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  const token = await getAccessToken();

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((options.headers as Record<string, string>) || {}),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      // 401: Attempt one session refresh and retry
      if (response.status === 401) {
        try {
          const { data: refreshData } = await supabase.auth.refreshSession();
          if (refreshData.session) {
            headers['Authorization'] = `Bearer ${refreshData.session.access_token}`;
            const retryResp = await fetch(`${API_BASE}${endpoint}`, {
              ...options,
              headers,
            });
            if (retryResp.ok) {
              const data = await retryResp.json();
              return { data, error: null };
            }
          }
        } catch {
          // Refresh failed
        }
        return {
          data: null,
          error: {
            code: 'UNAUTHORIZED',
            message: 'Session expired or authentication required. Please sign in.',
          },
        };
      }

      // 429: Rate limited
      if (response.status === 429) {
        try {
          const errJson = await response.json();
          return {
            data: null,
            error: errJson.error || {
              code: 'RATE_LIMITED',
              message: 'Rate limit exceeded. Please wait a moment before trying again.',
            },
          };
        } catch {
          return {
            data: null,
            error: {
              code: 'RATE_LIMITED',
              message: 'Too many requests. Please wait a moment before trying again.',
            },
          };
        }
      }

      // Parse structured JSON error
      try {
        const errorBody = await response.json();
        return {
          data: null,
          error: errorBody.error || {
            code: `HTTP_${response.status}`,
            message: response.statusText,
          },
        };
      } catch {
        return {
          data: null,
          error: {
            code: `HTTP_${response.status}`,
            message: `Request failed with status ${response.status}`,
          },
        };
      }
    }

    const data = await response.json();
    return { data, error: null };
  } catch (err: unknown) {
    return {
      data: null,
      error: {
        code: 'NETWORK_ERROR',
        message: 'Unable to connect to the VeriQuest backend API server.',
      },
    };
  }
}

/* ==========================================================================
   Domain API 1: Auth
   ========================================================================== */
export const authApi = {
  async getSession() {
    return supabase.auth.getSession();
  },
  async signIn(email: string, password: string) {
    return supabase.auth.signInWithPassword({ email, password });
  },
  async signUp(email: string, password: string, username: string) {
    return supabase.auth.signUp({
      email,
      password,
      options: {
        data: {
          username,
          display_name: username,
        },
      },
    });
  },
  async signOut() {
    return supabase.auth.signOut();
  },
  async resetPassword(email: string) {
    return supabase.auth.resetPasswordForEmail(email);
  },
  async refreshSession() {
    return supabase.auth.refreshSession();
  },
};

/* ==========================================================================
   Domain API 2: User Profile
   ========================================================================== */
export const userApi = {
  async getProfile() {
    return apiFetch<Record<string, unknown>>('/api/v1/profile');
  },
  async updateProfile(updates: { display_name?: string; bio?: string; avatar_url?: string }) {
    return apiFetch<{ message: string; updated_fields: string[] }>('/api/v1/profile', {
      method: 'PATCH',
      body: JSON.stringify(updates),
    });
  },
};

/* ==========================================================================
   Domain API 3: Challenges (Public by Construction)
   ========================================================================== */
export interface ChallengeQueryFilters {
  search?: string;
  difficulty?: string;
  category?: string;
  level?: number;
  status?: string;
  page?: number;
  page_size?: number;
}

export const challengeApi = {
  async getChallenges(params?: ChallengeQueryFilters) {
    const searchParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== 'All') {
          searchParams.set(key, String(value));
        }
      });
    }
    const query = searchParams.toString();
    return apiFetch<{
      challenges: Record<string, unknown>[];
      total: number;
      page: number;
      page_size: number;
    }>(`/api/v1/challenges${query ? `?${query}` : ''}`);
  },

  async getChallengeBySlug(slug: string) {
    return apiFetch<Record<string, unknown>>(`/api/v1/challenges/${slug}`);
  },
};

/* ==========================================================================
   Domain API 4: Submissions & Execution Polling
   ========================================================================== */
export const submissionApi = {
  async submitSolution(challengeId: string, submittedCode: string, idempotencyKey?: string) {
    return apiFetch<{ submission_id: string; status: string }>('/api/v1/submissions', {
      method: 'POST',
      body: JSON.stringify({
        challenge_id: challengeId,
        submitted_code: submittedCode,
        idempotency_key: idempotencyKey,
      }),
    });
  },

  async getSubmission(submissionId: string) {
    return apiFetch<Record<string, unknown>>(`/api/v1/submissions/${submissionId}`);
  },

  /**
   * Poll submission status until terminal state.
   * Strictly caps total polling duration (default 60s per Master Prompt Section 6)
   * so frontend cannot poll indefinitely.
   */
  async pollSubmission(
    submissionId: string,
    intervalMs: number = 1500,
    maxWaitMs: number = 60000
  ): Promise<ApiResponse<Record<string, unknown>>> {
    const startTime = Date.now();
    const terminalStatuses = new Set([
      'accepted',
      'wrong_answer',
      'compilation_error',
      'simulation_error',
      'timeout',
      'resource_limit',
      'system_error',
      'cancelled',
    ]);

    while (Date.now() - startTime < maxWaitMs) {
      const response = await this.getSubmission(submissionId);
      if (response.error) {
        return response;
      }

      const status = (response.data?.status as string) || '';
      if (terminalStatuses.has(status)) {
        return response;
      }

      await new Promise((resolve) => setTimeout(resolve, intervalMs));
    }

    // Polling timeout cap reached (60s) — surface "still processing"
    return {
      data: {
        submission_id: submissionId,
        status: 'processing',
        message:
          'Your HDL simulation is taking longer than expected to finish. You can safely navigate away and check results in your Submissions history.',
      },
      error: null,
    };
  },

  async getSubmissionHistory(page: number = 1, pageSize: number = 20) {
    return apiFetch<{ submissions: Record<string, unknown>[]; total: number }>(
      `/api/v1/submissions?page=${page}&page_size=${pageSize}`
    );
  },
};

/* ==========================================================================
   Domain API 5: Progress & Telemetry
   ========================================================================== */
export const progressApi = {
  async getUserProgress() {
    return apiFetch<Record<string, unknown>>('/api/v1/profile');
  },
};

/* ==========================================================================
   Domain API 6: Quests
   ========================================================================== */
export const questApi = {
  async getQuests() {
    return apiFetch<{ quests: Record<string, unknown>[] }>('/api/v1/quests');
  },
};

/* ==========================================================================
   Domain API 7: Badges
   ========================================================================== */
export const badgeApi = {
  async getBadges() {
    return apiFetch<{ badges: Record<string, unknown>[] }>('/api/v1/badges');
  },
};

/* ==========================================================================
   Domain API 8: Leaderboard
   ========================================================================== */
export const leaderboardApi = {
  async getLeaderboard(
    tab: 'global' | 'weekly' | 'monthly' = 'global',
    page: number = 1,
    pageSize: number = 50
  ) {
    return apiFetch<{
      entries: Record<string, unknown>[];
      total: number;
      page: number;
      tab: string;
    }>(`/api/v1/leaderboard?tab=${tab}&page=${page}&page_size=${pageSize}`);
  },
};

/* ==========================================================================
   Domain API 9: Admin Management (CRUD + Lifecycle)
   ========================================================================== */
export const adminApi = {
  async listChallenges<T = Record<string, unknown>>() {
    return apiFetch<{ challenges: T[] }>('/api/v1/admin/challenges');
  },

  async getChallenge<T = Record<string, unknown>>(challengeId: string) {
    return apiFetch<T>(`/api/v1/admin/challenges/${challengeId}`);
  },

  async createChallenge(data: Record<string, unknown>) {
    return apiFetch<{ challenge_id: string; status: string }>('/api/v1/admin/challenges', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async updateChallenge(challengeId: string, data: Record<string, unknown>) {
    return apiFetch<{ message: string }>(`/api/v1/admin/challenges/${challengeId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  async validateChallenge(challengeId: string) {
    return apiFetch<{ message: string; challenge_id: string; status: string }>(
      `/api/v1/admin/challenges/${challengeId}/validate`,
      { method: 'POST' }
    );
  },

  async publishChallenge(challengeId: string) {
    return apiFetch<{ message: string; status: string }>(
      `/api/v1/admin/challenges/${challengeId}/publish`,
      { method: 'POST' }
    );
  },

  async unpublishChallenge(challengeId: string) {
    return apiFetch<{ message: string; status: string }>(
      `/api/v1/admin/challenges/${challengeId}/unpublish`,
      { method: 'POST' }
    );
  },

  async getAuditLog(page: number = 1, pageSize: number = 50) {
    return apiFetch<{
      audit_logs: AuditLogEntry[];
      total: number;
      page: number;
      page_size: number;
    }>(`/api/v1/admin/audit-log?page=${page}&page_size=${pageSize}`);
  },
};

export interface AuditLogEntry {
  id: string;
  admin_user_id: string;
  admin_username: string;
  action: string;
  target_type: string;
  target_id: string | null;
  details: Record<string, unknown>;
  created_at: string;
}

/* ==========================================================================
   Unified Backwards-Compatible Export
   ========================================================================== */
export const api = {
  auth: authApi,
  user: userApi,
  challenges: challengeApi,
  submissions: submissionApi,
  progress: progressApi,
  quests: questApi,
  badges: badgeApi,
  leaderboard: leaderboardApi,
  admin: adminApi,

  // Direct shortcuts for existing views
  getChallenges: challengeApi.getChallenges.bind(challengeApi),
  getChallengeBySlug: challengeApi.getChallengeBySlug.bind(challengeApi),
  submitSolution: submissionApi.submitSolution.bind(submissionApi),
  pollSubmission: submissionApi.pollSubmission.bind(submissionApi),
  getSubmissionHistory: submissionApi.getSubmissionHistory.bind(submissionApi),
  getProfile: userApi.getProfile.bind(userApi),
  updateProfile: userApi.updateProfile.bind(userApi),
  getLeaderboard: leaderboardApi.getLeaderboard.bind(leaderboardApi),
  getQuests: questApi.getQuests.bind(questApi),
  getBadges: badgeApi.getBadges.bind(badgeApi),
  getAuditLog: adminApi.getAuditLog.bind(adminApi),
};

