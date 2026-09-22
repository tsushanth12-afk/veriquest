/* ==========================================================================
   VeriQuest Context — Global State, Routing, Auth & Theme
   ========================================================================== */

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { UserProfile } from '../types/user';
import { MOCK_USER } from '../api/mockData';
import { supabase } from '../lib/supabase';
import { Session, User } from '@supabase/supabase-js';
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
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [currentRoute, setCurrentRoute] = useState<PageRoute>('dashboard');
  const [activeChallengeId, setActiveChallengeId] = useState<string>('and-gate-demo');
  const [theme, setTheme] = useState<'light' | 'dark'>('light');
  const [searchQuery, setSearchQuery] = useState('');
  const [user, setUser] = useState<UserProfile>(MOCK_USER);
  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  const [isAuthOpen, setAuthOpen] = useState(false);

  // Supabase auth state
  const [session, setSession] = useState<Session | null>(null);
  const [authUser, setAuthUser] = useState<User | null>(null);
  const [isAuthLoading, setIsAuthLoading] = useState(true);
  const [isAdmin, setIsAdmin] = useState(false);

  const isAuthenticated = !!session;

  // Initialize auth on mount
  useEffect(() => {
    // Get initial session
    supabase.auth.getSession().then(({ data: { session: s } }) => {
      setSession(s);
      setAuthUser(s?.user || null);
      setIsAdmin(
        s?.user?.app_metadata?.role === 'admin' ||
        s?.user?.user_metadata?.role === 'admin' ||
        false
      );
      setIsAuthLoading(false);
      if (s?.user) {
        loadProfile(s.user);
      }
    });

    // Listen for auth state changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (_event, s) => {
        setSession(s);
        setAuthUser(s?.user || null);
        setIsAdmin(
          s?.user?.app_metadata?.role === 'admin' ||
          s?.user?.user_metadata?.role === 'admin' ||
          false
        );
        if (s?.user) {
          loadProfile(s.user);
        } else {
          setUser(MOCK_USER);
        }
      }
    );

    return () => subscription.unsubscribe();
  }, []);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  const loadProfile = useCallback(async (currentAuth?: User | null) => {
    try {
      const { data, error } = await api.getProfile();
      if (data && !error) {
        setUser(data as unknown as UserProfile);
        return;
      }
    } catch {
      // Profile API request failed or backend offline
    }

    // When authenticated but backend profile endpoint is pending,
    // construct profile details from auth metadata instead of hardcoded mock user
    if (currentAuth) {
      const username =
        currentAuth.user_metadata?.username ||
        currentAuth.email?.split('@')[0] ||
        'Student';
      const fullName =
        currentAuth.user_metadata?.display_name ||
        currentAuth.user_metadata?.full_name ||
        username;

      setUser((prev) => ({
        ...prev,
        id: currentAuth.id,
        username,
        fullName,
      }));
    }
  }, []);

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

  const addToast = (toast: Omit<ToastMessage, 'id'>) => {
    const id = `t_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`;
    setToasts((prev) => [...prev, { ...toast, id }]);
    setTimeout(() => {
      removeToast(id);
    }, 4500);
  };

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
    await supabase.auth.signOut();
    setSession(null);
    setAuthUser(null);
    setUser(MOCK_USER);
    setCurrentRoute('dashboard');
    addToast({ type: 'info', title: 'Signed out' });
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
