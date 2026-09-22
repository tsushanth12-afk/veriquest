/* ==========================================================================
   VeriQuest Layout — Top Header
   ========================================================================== */

import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';
import { Search, Bell, Sun, Moon, CheckCircle2, Menu } from 'lucide-react';

interface TopHeaderProps {
  onMobileToggle?: () => void;
}

export const TopHeader: React.FC<TopHeaderProps> = ({ onMobileToggle }) => {
  const { searchQuery, setSearchQuery, theme, toggleTheme, user, setCurrentRoute, addToast } = useApp();
  const [showNotifications, setShowNotifications] = useState(false);

  return (
    <header className="app-header">
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
        {onMobileToggle && (
          <button
            onClick={onMobileToggle}
            className="neu-btn-ghost"
            style={{ display: 'flex', padding: '6px', cursor: 'pointer' }}
          >
            <Menu size={20} />
          </button>
        )}

        {/* Search Bar */}
        <div className="header-search neu-inset">
          <Search size={15} style={{ color: 'var(--text-muted)' }} />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search challenges, Verilog topics..."
          />
          <span className="header-shortcut">⌘K</span>
        </div>
      </div>

      {/* Right Telemetry & Actions */}
      <div className="header-actions">
        {/* Simulator status */}
        <div className="header-badge neu-card-sm" style={{ display: 'flex', alignItems: 'center' }}>
          <span className="pulse-dot"></span>
          <span>Icarus 12.0 Ready</span>
        </div>

        {/* Theme Toggle */}
        <button
          onClick={toggleTheme}
          className="neu-btn"
          title={theme === 'light' ? 'Switch to Warm Dark mode' : 'Switch to Warm Light mode'}
          style={{ padding: '6px 10px', height: '32px' }}
        >
          {theme === 'light' ? <Moon size={15} /> : <Sun size={15} />}
        </button>

        {/* Notifications */}
        <div style={{ position: 'relative' }}>
          <button
            onClick={() => setShowNotifications(!showNotifications)}
            className="neu-btn"
            style={{ padding: '6px 10px', height: '32px', position: 'relative' }}
          >
            <Bell size={15} />
            <span
              style={{
                position: 'absolute',
                top: '4px',
                right: '4px',
                width: '6px',
                height: '6px',
                borderRadius: '50%',
                backgroundColor: 'var(--accent)',
              }}
            />
          </button>

          {showNotifications && (
            <div
              className="neu-card"
              style={{
                position: 'absolute',
                top: '42px',
                right: 0,
                width: '280px',
                padding: '12px',
                zIndex: 100,
                display: 'flex',
                flexDirection: 'column',
                gap: '8px',
              }}
            >
              <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                Notifications
              </div>
              <div
                style={{
                  fontSize: '12px',
                  padding: '8px',
                  borderRadius: 'var(--radius-sm)',
                  backgroundColor: 'var(--surface-hover)',
                  display: 'flex',
                  gap: '8px',
                  alignItems: 'flex-start',
                }}
              >
                <CheckCircle2 size={16} style={{ color: 'var(--status-success)', flexShrink: 0, marginTop: '2px' }} />
                <div>
                  <div style={{ fontWeight: 600 }}>Testbench Accepted</div>
                  <div style={{ color: 'var(--text-muted)', fontSize: '11px' }}>
                    4-bit Ripple Carry Adder passed all test vectors.
                  </div>
                </div>
              </div>
              <button
                onClick={() => {
                  setShowNotifications(false);
                  addToast({ type: 'info', title: 'All caught up!' });
                }}
                className="neu-btn-ghost"
                style={{ fontSize: '11px', textAlign: 'center', width: '100%', marginTop: '4px' }}
              >
                Mark all as read
              </button>
            </div>
          )}
        </div>

        {/* Profile Chip */}
        <div
          onClick={() => setCurrentRoute('profile')}
          className="header-profile-btn"
        >
          <div className="avatar-chip">
            {user.username.substring(0, 2).toUpperCase()}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', textAlign: 'left', lineHeight: 1.1 }}>
            <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-main)' }}>
              {user.username}
            </span>
            <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
              Lvl {user.stats.level}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
};
