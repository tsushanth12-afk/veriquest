/* ==========================================================================
   VeriQuest Auth — Inset Neumorphic Login & Signup Modal
   ========================================================================== */

import React, { useState, useEffect } from 'react';
import { useApp } from '../../context/AppContext';
import { X, Lock, Mail, User, ArrowRight, Loader2 } from 'lucide-react';

export const AuthModal: React.FC = () => {
  const { isAuthOpen, setAuthOpen, addToast, login, signup, resetPassword } = useApp();
  const [mode, setMode] = useState<'login' | 'signup' | 'forgot'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  // Accessibility: Dismiss modal on Escape key
  useEffect(() => {
    if (!isAuthOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setAuthOpen(false);
        resetForm();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isAuthOpen, setAuthOpen]);

  if (!isAuthOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      if (mode === 'login') {
        const result = await login(email, password);
        if (result.success) {
          addToast({ type: 'success', title: 'Welcome back!', description: 'Logged into your VeriQuest hardware track.' });
          setAuthOpen(false);
          resetForm();
        } else {
          setError(result.error || 'Login failed');
        }
      } else if (mode === 'signup') {
        const result = await signup(email, password, name);
        if (result.success) {
          addToast({ type: 'success', title: 'Account created!', description: 'Check your email to verify your account.' });
          setAuthOpen(false);
          resetForm();
        } else {
          setError(result.error || 'Signup failed');
        }
      } else {
        const result = await resetPassword(email);
        if (result.success) {
          addToast({ type: 'info', title: 'Reset link dispatched', description: 'Check your email for password reset instructions.' });
          setAuthOpen(false);
          resetForm();
        } else {
          setError(result.error || 'Reset failed');
        }
      }
    } catch {
      setError('An unexpected error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  const resetForm = () => {
    setEmail('');
    setPassword('');
    setName('');
    setError('');
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="auth-modal-title"
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(23, 21, 19, 0.45)',
        backdropFilter: 'blur(4px)',
        zIndex: 10000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '20px',
      }}
    >
      <div
        className="neu-card"
        style={{
          width: '100%',
          maxWidth: '400px',
          padding: '28px',
          display: 'flex',
          flexDirection: 'column',
          gap: '20px',
          backgroundColor: 'var(--surface)',
          position: 'relative',
        }}
      >
        {/* Close */}
        <button
          onClick={() => { setAuthOpen(false); resetForm(); }}
          className="neu-btn-ghost"
          aria-label="Close authentication modal"
          style={{ position: 'absolute', top: '16px', right: '16px', padding: '4px' }}
        >
          <X size={18} />
        </button>

        {/* Title */}
        <div>
          <div style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--accent)', fontWeight: 600 }}>
            VERIQUEST IDENTITY
          </div>
          <h2 id="auth-modal-title" style={{ fontSize: '20px', margin: '4px 0 0 0' }}>
            {mode === 'login' ? 'Engineer Sign In' : mode === 'signup' ? 'Create HDL Account' : 'Reset Credentials'}
          </h2>
          <p style={{ margin: '4px 0 0 0', fontSize: '12px', color: 'var(--text-muted)' }}>
            {mode === 'login' ? 'Continue your Verilog synthesis journey.' : 'Join the hardware learning community.'}
          </p>
        </div>

        {/* Error */}
        {error && (
          <div style={{
            padding: '8px 12px',
            fontSize: '12px',
            color: 'var(--status-error)',
            backgroundColor: 'rgba(220, 50, 50, 0.1)',
            borderRadius: '6px',
            border: '1px solid rgba(220, 50, 50, 0.2)',
          }}>
            {error}
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {mode === 'signup' && (
            <div>
              <label style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                USERNAME
              </label>
              <div className="neu-inset" style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 12px' }}>
                <User size={15} style={{ color: 'var(--text-muted)' }} />
                <input
                  type="text"
                  required
                  placeholder="alex_chen"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  disabled={isLoading}
                  style={{ background: 'none', border: 'none', outline: 'none', width: '100%', fontSize: '13px', color: 'var(--text-main)' }}
                />
              </div>
            </div>
          )}

          <div>
            <label style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
              ACADEMIC / WORK EMAIL
            </label>
            <div className="neu-inset" style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 12px' }}>
              <Mail size={15} style={{ color: 'var(--text-muted)' }} />
              <input
                type="email"
                required
                placeholder="alex@university.edu"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={isLoading}
                style={{ background: 'none', border: 'none', outline: 'none', width: '100%', fontSize: '13px', color: 'var(--text-main)' }}
              />
            </div>
          </div>

          {mode !== 'forgot' && (
            <div>
              <label style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                PASSWORD
              </label>
              <div className="neu-inset" style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 12px' }}>
                <Lock size={15} style={{ color: 'var(--text-muted)' }} />
                <input
                  type="password"
                  required
                  minLength={6}
                  placeholder="••••••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={isLoading}
                  style={{ background: 'none', border: 'none', outline: 'none', width: '100%', fontSize: '13px', color: 'var(--text-main)' }}
                />
              </div>
            </div>
          )}

          <button
            type="submit"
            className="neu-btn neu-btn-primary"
            disabled={isLoading}
            style={{ width: '100%', padding: '10px', marginTop: '6px', opacity: isLoading ? 0.7 : 1 }}
          >
            {isLoading ? (
              <Loader2 size={15} style={{ animation: 'spin 1s linear infinite' }} />
            ) : (
              <>
                <span>{mode === 'login' ? 'Sign In' : mode === 'signup' ? 'Create Account' : 'Dispatch Reset Email'}</span>
                <ArrowRight size={15} />
              </>
            )}
          </button>
        </form>

        {/* Mode switcher */}
        <div style={{ textAlign: 'center', fontSize: '12px', color: 'var(--text-muted)' }}>
          {mode === 'login' ? (
            <div>
              New to VeriQuest?{' '}
              <button
                type="button"
                onClick={() => { setMode('signup'); setError(''); }}
                style={{ background: 'none', border: 'none', color: 'var(--accent)', fontWeight: 600, cursor: 'pointer' }}
              >
                Create an account
              </button>
              <br />
              <button
                type="button"
                onClick={() => { setMode('forgot'); setError(''); }}
                style={{ background: 'none', border: 'none', color: 'var(--text-muted)', fontSize: '11px', cursor: 'pointer', marginTop: '6px' }}
              >
                Forgot password?
              </button>
            </div>
          ) : (
            <div>
              Already registered?{' '}
              <button
                type="button"
                onClick={() => { setMode('login'); setError(''); }}
                style={{ background: 'none', border: 'none', color: 'var(--accent)', fontWeight: 600, cursor: 'pointer' }}
              >
                Sign in
              </button>
            </div>
          )}
        </div>
      </div>

      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};
