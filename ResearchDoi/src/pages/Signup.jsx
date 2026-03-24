import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { motion as Motion } from 'framer-motion';
import { UserPlus, Mail, Lock, Chrome, ArrowRight, AlertCircle, CheckCircle2 } from 'lucide-react';
import ParticleBackground from '../components/ParticleBackground';
import Logo from '../components/Logo';

export default function Signup() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { signup, loginWithGoogle } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();

    if (password !== confirmPassword) {
      return setError('Passwords do not match');
    }

    try {
      setError('');
      setLoading(true);
      await signup(email, password);
      navigate('/');
    } catch (err) {
      if (err.code === 'auth/email-already-in-use') {
        setError('Email already in use.');
      } else if (err.code === 'auth/weak-password') {
        setError('Password should be at least 6 characters.');
      } else {
        setError('Failed to create an account.');
      }
      console.error(err);
    }
    setLoading(false);
  }

  async function handleGoogleLogin() {
    try {
      setError('');
      setLoading(true);
      await loginWithGoogle();
      navigate('/');
    } catch (err) {
      setError('Failed to sign up with Google.');
      console.error(err);
    }
    setLoading(false);
  }

  return (
    <div className="auth-layout">
      <div className="auth-visuals">
        <ParticleBackground
          particleColor="rgba(255, 255, 255, 0.8)"
          backgroundColor="#000000"
        />
        <div className="auth-visuals-overlay" style={{ background: 'none' }}></div>
      </div>
      <div className="auth-container">
        <Motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: "easeOut" }}
          className="auth-card glass"
        >
          <div className="auth-header">
            <div className="auth-logo" style={{ color: 'var(--text-main)' }}>
              <Logo useGradient={false} useSchemeColor={false} />
            </div>
            <h1>Create Account</h1>
            <p>Join the next generation of DOI analysis</p>
          </div>

          {error && (
            <Motion.div
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              className="auth-error"
            >
              <AlertCircle size={18} />
              <span>{error}</span>
            </Motion.div>
          )}

          <form onSubmit={handleSubmit} className="auth-form">
            <div className="form-group">
              <label>Email Address</label>
              <div className="input-wrapper">
                <Mail className="input-icon" size={18} />
                <input
                  type="email"
                  placeholder="name@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>
            </div>

            <div className="form-group">
              <label>Password</label>
              <div className="input-wrapper">
                <Lock className="input-icon" size={18} />
                <input
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </div>
            </div>

            <div className="form-group">
              <label>Confirm Password</label>
              <div className="input-wrapper">
                <Lock className="input-icon" size={18} />
                <input
                  type="password"
                  placeholder="••••••••"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              className="btn-primary auth-submit"
              disabled={loading}
            >
              {loading ? 'Creating account...' : (
                <>
                  Get Started <ArrowRight size={18} />
                </>
              )}
            </button>
          </form>

          <div className="auth-divider">
            <span>or join with</span>
          </div>

          <button
            onClick={handleGoogleLogin}
            className="btn-secondary google-btn"
            disabled={loading}
          >
            <Chrome size={18} /> Google
          </button>

          <div className="auth-benefits">
            <div className="benefit">
              <CheckCircle2 size={14} /> <span>Unlimited DOI lookups</span>
            </div>
            <div className="benefit">
              <CheckCircle2 size={14} /> <span>Save research history</span>
            </div>
          </div>

          <p className="auth-footer">
            Already have an account? <Link to="/login">Sign in</Link>
          </p>
        </Motion.div>

        <style>{`
        .auth-layout {
          display: flex;
          flex-direction: column;
          min-height: 100vh;
          min-height: 100svh;
          width: 100%;
          position: relative;
          isolation: isolate;
          z-index: 2000;
          background: transparent;
          overflow-y: auto;
          overflow-x: hidden;
        }

        .auth-visuals {
          position: fixed;
          inset: 0;
          width: 100vw;
          height: 100vh;
          height: 100svh;
          z-index: 0;
          pointer-events: none;
          overflow: hidden;
        }

        .auth-visuals-overlay {
          position: absolute;
          inset: 0;
          background: none;
          pointer-events: none;
        }

        .auth-container {
          flex: 1;
          display: flex;
          align-items: flex-end;
          justify-content: center;
          padding: 30vh 1.25rem calc(2rem + env(safe-area-inset-bottom)) 1.25rem;
          background: linear-gradient(to bottom, transparent 0%, rgba(0, 0, 0, 0.45) 15%, rgba(4, 4, 6, 0.85) 35%, #000000 65%, #000000 100%);
          position: relative;
          z-index: 1;
        }

        @media (max-width: 480px) {
          .auth-container {
            padding-bottom: calc(2.5rem + env(safe-area-inset-bottom));
          }
        }

        @media (min-width: 900px) {
          .auth-layout {
            flex-direction: row;
            overflow: hidden;
          }
          .auth-visuals {
            position: relative;
            inset: auto;
            height: 100vh;
            flex: 1 1 50%;
            width: 50%;
            min-height: auto;
            pointer-events: auto;
            background: #000000;
            overflow: hidden;
          }
          .auth-visuals-overlay {
            background: none;
          }
          .auth-container {
            flex: 1 1 50%;
            width: 50%;
            align-items: center;
            justify-content: center;
            padding: 4rem 3rem;
            background: var(--bg-surface);
            border-left: 1px solid var(--border);
          }
        }

        .auth-card {
          width: 100%;
          max-width: 400px;
          padding: 0;
          background: transparent;
          border: none;
          box-shadow: none;
          margin: 0 auto;
        }

        @media (min-width: 900px) {
          .auth-card {
            max-width: 420px;
          }
        }

        .auth-header {
          text-align: center;
          margin-bottom: 2.5rem;
        }

        .auth-logo {
          color: var(--text-main);
          margin-bottom: 1.5rem;
          display: inline-flex;
          width: 140px;
          height: auto;
        }

        .auth-header h1 {
          color: var(--text-main);
          font-size: 2.25rem;
          font-weight: 700;
          margin-bottom: 0.5rem;
          letter-spacing: -0.03em;
        }

        .auth-header p {
          color: var(--text-muted);
          font-size: 0.95rem;
        }

        .auth-error {
          background: rgba(244, 63, 94, 0.1);
          border: 1px solid rgba(244, 63, 94, 0.2);
          color: #fb7185;
          padding: 0.875rem 1rem;
          border-radius: 9999px;
          display: flex;
          align-items: center;
          gap: 0.75rem;
          font-size: 0.9rem;
          margin-bottom: 1.5rem;
        }

        .auth-form {
          display: flex;
          flex-direction: column;
          gap: 1.25rem;
        }

        .form-group {
          display: flex;
          flex-direction: column;
          gap: 0.6rem;
        }

        .form-group label {
          font-size: 0.85rem;
          font-weight: 500;
          color: var(--text-muted);
          padding: 0 0.25rem;
        }

        .input-wrapper {
          position: relative;
          display: flex;
          align-items: center;
        }

        .input-icon {
          position: absolute;
          left: 1.25rem;
          color: var(--text-dim);
          pointer-events: none;
        }

        .input-wrapper input {
          width: 100%;
          padding: 1rem 1.25rem 1rem 3rem;
          background: var(--bg-input);
          border: 1px solid var(--border);
          border-radius: 9999px;
          color: var(--text-main);
          font-size: 1rem;
          transition: all 0.2s ease;
          -webkit-text-fill-color: var(--text-main);
        }

        .input-wrapper input:focus {
          outline: none;
          border-color: var(--secondary);
          background: var(--bg-input);
        }

        .input-wrapper input::placeholder {
          color: var(--text-dim);
        }

        .input-wrapper input:-webkit-autofill,
        .input-wrapper input:-webkit-autofill:hover,
        .input-wrapper input:-webkit-autofill:focus {
          -webkit-text-fill-color: var(--text-main);
          box-shadow: 0 0 0px 1000px var(--bg-input) inset;
          transition: background-color 9999s ease-in-out 0s;
        }

        .btn-primary {
          background: var(--text-main);
          color: var(--bg-body);
          font-weight: 600;
          padding: 1rem;
          border-radius: 9999px;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 0.5rem;
          transition: var(--transition-base);
          font-size: 1rem;
          margin-top: 0.5rem;
        }

        .btn-primary:hover:not(:disabled) {
          transform: translateY(-1px);
          box-shadow: 0 8px 16px rgba(255, 255, 255, 0.15);
        }

        .btn-primary:disabled {
          opacity: 0.7;
          cursor: not-allowed;
        }

        .auth-divider {
          display: flex;
          align-items: center;
          margin: 1.75rem 0;
          color: var(--text-dim);
          font-size: 0.8rem;
        }

        .auth-divider::before,
        .auth-divider::after {
          content: "";
          flex: 1;
          height: 1px;
          background: var(--border);
        }

        .auth-divider span {
          padding: 0 1rem;
        }

        .google-btn {
          background: transparent;
          color: var(--text-main);
          border: 1px solid var(--border);
          padding: 1rem;
          border-radius: 9999px;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 0.75rem;
          font-weight: 500;
          font-size: 1rem;
          transition: all 0.2s ease;
        }

        .google-btn:hover:not(:disabled) {
          background: rgba(255, 255, 255, 0.05);
          border-color: var(--border-bright);
        }

        .auth-benefits {
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
          margin-top: 1.5rem;
          padding: 1.25rem;
          background: rgba(255, 255, 255, 0.02);
          border-radius: 16px;
          border: 1px solid rgba(255, 255, 255, 0.05);
        }

        .benefit {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          font-size: 0.9rem;
          color: var(--text-muted);
        }

        .benefit span {
          color: white;
        }

        .auth-footer {
          text-align: center;
          margin-top: 2.5rem;
          color: var(--text-muted);
          font-size: 0.95rem;
        }

        .auth-footer a {
          color: var(--secondary);
          text-decoration: none;
          font-weight: 600;
          margin-left: 0.25rem;
        }
        .auth-footer a:hover {
          text-decoration: underline;
        }
      `}</style>
      </div>
    </div>
  );
}
