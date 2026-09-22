/* ==========================================================================
   VeriQuest Layout — Persistent Sidebar
   ========================================================================== */

import React from 'react';
import { useApp, PageRoute } from '../../context/AppContext';
import {
  LayoutDashboard,
  BookOpen,
  Code2,
  Route,
  Trophy,
  Medal,
  User,
  Bookmark,
  Settings,
  HelpCircle,
  Activity,
  Shield,
  LogOut,
} from 'lucide-react';

export const AppSidebar: React.FC = () => {
  const { currentRoute, setCurrentRoute, addToast, isAdmin, isAuthenticated, logout, setAuthOpen } = useApp();

  const navItems: { route: PageRoute; label: string; icon: React.ElementType }[] = [
    { route: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { route: 'learn', label: 'Learn', icon: BookOpen },
    { route: 'challenges', label: 'Challenges', icon: Code2 },
    { route: 'quests', label: 'Quests', icon: Route },
    { route: 'leaderboard', label: 'Leaderboard', icon: Trophy },
    { route: 'achievements', label: 'Achievements', icon: Medal },
    { route: 'profile', label: 'Profile', icon: User },
    { route: 'admin', label: 'Admin', icon: Shield },
  ];

  return (
    <aside className="app-sidebar">
      {/* Brand Header */}
      <div
        className="sidebar-brand"
        onClick={() => setCurrentRoute('dashboard')}
        style={{ cursor: 'pointer' }}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') setCurrentRoute('dashboard'); }}
      >
        <div className="brand-icon-box">
          <Activity size={18} strokeWidth={2.5} />
        </div>
        <div>
          <div className="brand-text">
            <span>VERIQUEST</span>
            <span className="brand-badge">HDL</span>
          </div>
        </div>
      </div>

      {/* Main Navigation */}
      <nav className="sidebar-nav">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentRoute === item.route;
          return (
            <button
              key={item.route}
              onClick={() => setCurrentRoute(item.route)}
              className={`nav-link ${isActive ? 'active' : ''}`}
            >
              <Icon size={17} strokeWidth={isActive ? 2.2 : 1.8} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      {/* Secondary / Footer Navigation */}
      <div className="sidebar-footer">
        <button
          onClick={() => addToast({ type: 'info', title: 'Saved challenges feature in development' })}
          className="nav-link"
        >
          <Bookmark size={16} />
          <span>Saved</span>
        </button>
        <button
          onClick={() => setCurrentRoute('settings')}
          className={`nav-link ${currentRoute === 'settings' ? 'active' : ''}`}
        >
          <Settings size={16} />
          <span>Settings</span>
        </button>
        <button
          onClick={() => addToast({ type: 'info', title: 'VeriQuest EDA Docs v1.4', description: 'IEEE 1364-2005 Verilog reference manual available in docs.' })}
          className="nav-link"
        >
          <HelpCircle size={16} />
          <span>Help</span>
        </button>
        {isAuthenticated ? (
          <button onClick={logout} className="nav-link">
            <LogOut size={16} />
            <span>Sign Out</span>
          </button>
        ) : (
          <button onClick={() => setAuthOpen(true)} className="nav-link">
            <User size={16} />
            <span>Sign In</span>
          </button>
        )}
      </div>
    </aside>
  );
};
