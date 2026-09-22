/* ==========================================================================
   VeriQuest API — User Profile & Telemetry Services
   ========================================================================== */

import { UserProfile } from '../types/user';
import { MOCK_USER, MOCK_SUBMISSIONS } from './mockData';
import { RecentSubmissionSummary } from '../types/submission';

export const userApi = {
  async getProfile(): Promise<UserProfile> {
    await new Promise((res) => setTimeout(res, 50));
    return MOCK_USER;
  },

  async getRecentSubmissions(): Promise<RecentSubmissionSummary[]> {
    await new Promise((res) => setTimeout(res, 50));
    return MOCK_SUBMISSIONS;
  },
};
