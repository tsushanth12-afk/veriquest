import type { User } from '@supabase/supabase-js';
import type { UserProfile } from '../types/user';
import { MOCK_USER } from '../api/mockData';

export function emptyProfile(auth?: User | null): UserProfile {
  const base = structuredClone(MOCK_USER);
  base.id = auth?.id ?? 'practice';
  base.username = auth?.email?.split('@')[0] ?? 'Practice';
  base.fullName = base.username;
  base.bio = '';
  base.topicMasteries = [];
  base.stats = Object.fromEntries(Object.keys(base.stats).map(key =>
    [key, key === 'levelTitle' ? 'Progress unavailable' : 0])) as unknown as UserProfile['stats'];
  return base;
}
