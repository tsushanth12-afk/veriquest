/* ==========================================================================
   VeriQuest View — Settings & Preferences
   ========================================================================== */

import React from 'react';
import { useApp } from '../context/AppContext';
import { Sun, Moon, Monitor, Sliders, Shield } from 'lucide-react';

export const SettingsView: React.FC = () => {
  const { theme, toggleTheme, user, addToast } = useApp();

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', maxWidth: '800px' }}>
      {/* Header */}
      <div className="neu-card" style={{ padding: '24px 28px' }}>
        <div style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--accent)', fontWeight: 600, textTransform: 'uppercase', marginBottom: '4px' }}>
          PLATFORM CONFIGURATION
        </div>
        <h1 style={{ fontSize: '22px', margin: 0 }}>System Settings</h1>
        <p style={{ margin: '4px 0 0 0', fontSize: '13px', color: 'var(--text-muted)' }}>
          Manage your interface appearance, editor telemetry, and account security.
        </p>
      </div>

      {/* Appearance Section */}
      <div className="neu-card" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Monitor size={18} style={{ color: 'var(--accent)' }} />
          <h2 style={{ fontSize: '16px', margin: 0 }}>Theme & Visual Identity</h2>
        </div>

        <p style={{ fontSize: '13px', color: 'var(--text-muted)', margin: 0 }}>
          VeriQuest uses a warm neumorphic design language engineered for long hardware verification sessions without eye strain.
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px', marginTop: '4px' }}>
          {/* Warm Light Card */}
          <div
            onClick={() => {
              if (theme !== 'light') toggleTheme();
            }}
            className={`neu-card-sm neu-card-interactive ${theme === 'light' ? 'neu-inset' : ''}`}
            style={{
              padding: '16px',
              display: 'flex',
              flexDirection: 'column',
              gap: '10px',
              border: theme === 'light' ? '2px solid var(--accent)' : '1px solid var(--border-subtle)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Sun size={16} style={{ color: 'var(--accent)' }} />
                <span style={{ fontWeight: 600, fontSize: '13px' }}>Warm Light</span>
              </div>
              {theme === 'light' && <span className="neu-badge" style={{ color: 'var(--accent)' }}>Active</span>}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
              Ivory canvas (#E8E0D3) with terracotta accents and tactile soft ambient shadows.
            </div>
          </div>

          {/* Warm Dark Card */}
          <div
            onClick={() => {
              if (theme !== 'dark') toggleTheme();
            }}
            className={`neu-card-sm neu-card-interactive ${theme === 'dark' ? 'neu-inset' : ''}`}
            style={{
              padding: '16px',
              display: 'flex',
              flexDirection: 'column',
              gap: '10px',
              border: theme === 'dark' ? '2px solid var(--accent)' : '1px solid var(--border-subtle)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Moon size={16} style={{ color: 'var(--accent)' }} />
                <span style={{ fontWeight: 600, fontSize: '13px' }}>Warm Dark</span>
              </div>
              {theme === 'dark' && <span className="neu-badge" style={{ color: 'var(--accent)' }}>Active</span>}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
              Deep espresso canvas (#171513) with copper highlights and low-contrast surfaces.
            </div>
          </div>
        </div>
      </div>

      {/* Editor Preferences */}
      <div className="neu-card" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Sliders size={18} style={{ color: 'var(--accent)' }} />
          <h2 style={{ fontSize: '16px', margin: 0 }}>Monaco RTL Editor Preferences</h2>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '13px' }}>
            <div>
              <div style={{ fontWeight: 600 }}>Editor Font Family</div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>JetBrains Mono with tabular numbers</div>
            </div>
            <span className="neu-badge">JetBrains Mono</span>
          </div>

          <div className="neu-divider" style={{ margin: '4px 0' }} />

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '13px' }}>
            <div>
              <div style={{ fontWeight: 600 }}>Tab Indentation</div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Default spaces per indentation level</div>
            </div>
            <span className="neu-badge">4 Spaces</span>
          </div>

          <div className="neu-divider" style={{ margin: '4px 0' }} />

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '13px' }}>
            <div>
              <div style={{ fontWeight: 600 }}>Auto-Save Drafts</div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Automatically preserve in-progress Verilog in session storage</div>
            </div>
            <span className="neu-badge" style={{ color: 'var(--status-success)' }}>Enabled</span>
          </div>
        </div>
      </div>

      {/* Account & Security */}
      <div className="neu-card" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Shield size={18} style={{ color: 'var(--accent)' }} />
          <h2 style={{ fontSize: '16px', margin: 0 }}>Account & Authentication</h2>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <div style={{ fontSize: '13px', fontWeight: 600 }}>Logged in as {user.fullName}</div>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>sushanth@engineering.edu</div>
          </div>

          <button
            onClick={() => addToast({ type: 'info', title: 'Account credentials synced' })}
            className="neu-btn"
            style={{ fontSize: '12px', padding: '6px 14px' }}
          >
            Update Credentials
          </button>
        </div>
      </div>
    </div>
  );
};
