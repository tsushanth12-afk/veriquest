/* ==========================================================================
   VeriQuest Layout — Responsive Mobile Navigation Drawer
   ========================================================================== */

import React, { useEffect } from 'react';
import { useApp, PageRoute } from '../../context/AppContext';
import {
  LayoutDashboard,
  BookOpen,
  Code2,
  Route,
  Trophy,
  Medal,
  User,
  Settings,
  X,
  Activity,
  Shield,
} from 'lucide-react';

interface MobileNavProps {
  isOpen: boolean;
  onClose: () => void;
}

export const MobileNav: React.FC<MobileNavProps> = ({ isOpen, onClose }) => {
  const { currentRoute, setCurrentRoute } = useApp();

  // Accessibility: Dismiss mobile nav on Escape key
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const navItems: { route: PageRoute; label: string; icon: React.ElementType }[] = [
    { route: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { route: 'learn', label: 'Learn Roadmap', icon: BookOpen },
    { route: 'challenges', label: 'Challenge Library', icon: Code2 },
    { route: 'quests', label: 'Quests', icon: Route },
    { route: 'leaderboard', label: 'Leaderboard', icon: Trophy },
    { route: 'achievements', label: 'Achievements', icon: Medal },
    { route: 'profile', label: 'Profile', icon: User },
    { route: 'admin', label: 'Admin Panel', icon: Shield },
    { route: 'settings', label: 'Settings', icon: Settings },
  ];

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(23, 21, 19, 0.45)',
        backdropFilter: 'blur(4px)',
        zIndex: 1000,
        display: 'flex',
      }}
      onClick={onClose}
    >
      <div
        className="neu-card"
        style={{
          width: '280px',
          height: '100%',
          backgroundColor: 'var(--surface)',
          display: 'flex',
          flexDirection: 'column',
          padding: '20px 16px',
          gap: '16px',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Activity size={18} style={{ color: 'var(--accent)' }} />
            <span style={{ fontWeight: 700, fontSize: '15px' }}>VERIQUEST</span>
          </div>
          <button onClick={onClose} className="neu-btn-ghost" style={{ padding: '4px' }}>
            <X size={18} />
          </button>
        </div>

        <nav style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentRoute === item.route;

            return (
              <button
                key={item.route}
                onClick={() => {
                  setCurrentRoute(item.route);
                  onClose();
                }}
                className={`nav-link ${isActive ? 'active' : ''}`}
                style={{ width: '100%', textAlign: 'left' }}
              >
                <Icon size={16} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
      </div>
    </div>
  );
};
