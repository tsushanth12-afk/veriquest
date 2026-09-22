import React from 'react';
import { useApp } from '../../context/AppContext';
import { CheckCircle2, AlertTriangle, AlertCircle, Info, X } from 'lucide-react';

export const ToastContainer: React.FC = () => {
  const { toasts, removeToast } = useApp();

  if (toasts.length === 0) return null;

  return (
    <div
      style={{
        position: 'fixed',
        bottom: '24px',
        right: '24px',
        zIndex: 9999,
        display: 'flex',
        flexDirection: 'column',
        gap: '10px',
        maxWidth: '360px',
      }}
    >
      {toasts.map((toast) => {
        let Icon = Info;
        let color = 'var(--text-main)';
        if (toast.type === 'success') {
          Icon = CheckCircle2;
          color = 'var(--status-success)';
        } else if (toast.type === 'warning') {
          Icon = AlertTriangle;
          color = 'var(--status-warning)';
        } else if (toast.type === 'error') {
          Icon = AlertCircle;
          color = 'var(--status-error)';
        }

        return (
          <div
            key={toast.id}
            className="neu-card"
            style={{
              padding: '12px 14px',
              display: 'flex',
              alignItems: 'flex-start',
              gap: '10px',
              backgroundColor: 'var(--surface)',
            }}
          >
            <Icon size={18} style={{ color, flexShrink: 0, marginTop: '2px' }} />
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontWeight: 600, fontSize: '13px', color: 'var(--text-main)' }}>
                {toast.title}
              </div>
              {toast.description && (
                <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>
                  {toast.description}
                </div>
              )}
            </div>
            <button
              onClick={() => removeToast(toast.id)}
              style={{
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                color: 'var(--text-dim)',
                padding: '2px',
              }}
            >
              <X size={14} />
            </button>
          </div>
        );
      })}
    </div>
  );
};
