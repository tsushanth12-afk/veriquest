/* ==========================================================================
   VeriQuest Context — Global State, Routing, Auth & Theme
   ========================================================================== */

import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { UserProfile } from '../types/user';
import { emptyProfile } from './profileState';
import { supabase } from '../lib/supabase';
import { Session, User } from '@supabase/supabase-js';
import { changeSessionIdentity, sessionSnapshot, isCurrentSession } from '../api/sessionBoundary';
import { api } from '../api/client';

export type PageRoute = 
  | 'dashboard'
  | 'learn'
  | 'challenges'
  | 'workspace'
  | 'quests'
  | 'leaderboard'
  | 'achievements'
  | 'profile'
  | 'settings'
  | 'admin';

export interface ToastMessage {
  id: string;
  type: 'success' | 'warning' | 'error' | 'info';
  title: string;
  description?: string;
}

interface AppContextType {
  currentRoute: PageRoute;
  setCurrentRoute: (route: PageRoute) => void;
  activeChallengeId: string;
  openChallenge: (challengeId: string) => void;
  theme: 'light' | 'dark';
  toggleTheme: () => void;
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  user: UserProfile;
  toasts: ToastMessage[];
  addToast: (toast: Omit<ToastMessage, 'id'>) => void;
  removeToast: (id: string) => void;
  isAuthOpen: boolean;
  setAuthOpen: (open: boolean) => void;
  // Auth state
  session: Session | null;
  authUser: User | null;
  isAuthenticated: boolean;
  isAuthLoading: boolean;
  isAdmin: boolean;
  login: (email: string, password: string) => Promise<{ success: boolean; error?: string }>;
  signup: (email: string, password: string, username: string) => Promise<{ success: boolean; error?: string }>;
  logout: () => Promise<void>;
  resetPassword: (email: string) => Promise<{ success: boolean; error?: string }>;
  refreshProfile: () => Promise<void>;
  sessionGeneration: number;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [currentRoute, setCurrentRoute] = useState<PageRoute>('dashboard');
  const [activeChallengeId, setActiveChallengeId] = useState<string>('and-gate-demo');
  const [theme, setTheme] = useState<'light' | 'dark'>('light');
  const [searchQuery, setSearchQuery] = useState('');
  const [user, setUser] = useState<UserProfile>(() => emptyProfile());
  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  const [isAuthOpen, setAuthOpen] = useState(false);

  // Supabase auth state
  const [session, setSession] = useState<Session | null>(null);
  const [authUser, setAuthUser] = useState<User | null>(null);
  const [isAuthLoading, setIsAuthLoading] = useState(true);
  const [isAdmin, setIsAdmin] = useState(false);

  const [sessionGeneration, setSessionGeneration] = useState(0);
  const identityRef = useRef<string | null>(null);
  const isAuthenticated = !!session;

  const loadProfile = useCallback(async (currentAuth?: User | null) => {
    const snapshot = sessionSnapshot();
    if (!currentAuth || snapshot.identity !== currentAuth.id) return;
    try {
      const { data, error } = await api.getProfile();
      if (isCurrentSession(snapshot) && data && !error && data.id === currentAuth.id) {
        setUser(data as unknown as UserProfile);
      }
    } catch { /* Keep this identity's empty profile, never another user's stats. */ }
  }, []);

  useEffect(() => {
    let active = true;
    let authEventSeen = false;
    const apply = (s: Session | null) => {
      if (!active) return;
      const id = s?.user.id ?? null;
      if (identityRef.current !== id || sessionSnapshot().identity !== id) {
        identityRef.current = id;
        setSessionGeneration(changeSessionIdentity(id));
        setUser(emptyProfile(s?.user));
        setIsAdmin(false);
        setToasts([]);
        setSearchQuery('');
        setActiveChallengeId('and-gate-demo');
        setAuthOpen(false);
        setCurrentRoute('dashboard');
      }
      setSession(s);
      setAuthUser(s?.user ?? null);
      setIsAuthLoading(false);
      if (s?.user) {
        void loadProfile(s.user);
        const snapshot = sessionSnapshot();
        // Backend list endpoint enforces the database role. Editable metadata is not authority.
        void api.admin.listChallenges().then(({ data, error }) => {
          if (active && isCurrentSession(snapshot)) setIsAdmin(!!data && !error);
        }).catch(() => { if (active && isCurrentSession(snapshot)) setIsAdmin(false); });
      } else setIsAdmin(false);
    };
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, s) => {
      authEventSeen = true;
      apply(s);
    });
    void supabase.auth.getSession().then(({ data }) => {
      if (!authEventSeen) apply(data.session);
    }).catch(() => { if (!authEventSeen) apply(null); });
    return () => { active = false; changeSessionIdentity(null); subscription.unsubscribe(); };
  }, [loadProfile]);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  const refreshProfile = useCallback(async () => {
    await loadProfile(authUser);
  }, [loadProfile, authUser]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'light' ? 'dark' : 'light'));
  };

  const openChallenge = (challengeId: string) => {
    setActiveChallengeId(challengeId);
    setCurrentRoute('workspace');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const addToast = useCallback((toast: Omit<ToastMessage, 'id'>) => {
    const id = `t_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`;
    setToasts((prev) => [...prev, { ...toast, id }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4500);
  }, []);

  const removeToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  // Auth methods
  const login = async (email: string, password: string) => {
    try {
      const { error } = await supabase.auth.signInWithPassword({ email, password });
      if (error) {
        return { success: false, error: error.message };
      }
      return { success: true };
    } catch (err: unknown) {
      return { success: false, error: 'Login failed' };
    }
  };

  const signup = async (email: string, password: string, username: string) => {
    try {
      const { error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: {
            username,
            display_name: username,
          },
        },
      });
      if (error) {
        return { success: false, error: error.message };
      }
      return { success: true };
    } catch (err: unknown) {
      return { success: false, error: 'Signup failed' };
    }
  };

  const logout = async () => {
    setSessionGeneration(changeSessionIdentity(null));
    identityRef.current = null;
    setIsAdmin(false);
    setToasts([]);
    setSearchQuery('');
    setActiveChallengeId('and-gate-demo');
    setAuthOpen(false);
    setUser(emptyProfile());
    setSession(null);
    setAuthUser(null);
    setCurrentRoute('dashboard');
    const snapshot = sessionSnapshot();
    const { error } = await supabase.auth.signOut();
    if (isCurrentSession(snapshot)) addToast({ type: error ? 'error' : 'info', title: error ? 'Sign-out failed' : 'Signed out' });
  };

  const resetPassword = async (email: string) => {
    try {
      const { error } = await supabase.auth.resetPasswordForEmail(email);
      if (error) {
        return { success: false, error: error.message };
      }
      return { success: true };
    } catch (err: unknown) {
      return { success: false, error: 'Password reset failed' };
    }
  };

  return (
    <AppContext.Provider
      value={{
        currentRoute,
        setCurrentRoute,
        activeChallengeId,
        openChallenge,
        theme,
        toggleTheme,
        searchQuery,
        setSearchQuery,
        user,
        toasts,
        addToast,
        removeToast,
        isAuthOpen,
        setAuthOpen,
        session,
        authUser,
        isAuthenticated,
        isAuthLoading,
        isAdmin,
        login,
        signup,
        logout,
        resetPassword,
        refreshProfile,
        sessionGeneration,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export const useApp = () => {
  const ctx = useContext(AppContext);
  if (!ctx) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return ctx;
};
