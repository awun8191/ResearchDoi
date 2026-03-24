import React, { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { User, Palette, Moon, Sun, Check, LogOut, Mail, Fingerprint } from 'lucide-react';

export default function Profile() {
  const navigate = useNavigate();
  const { currentUser, logout } = useAuth();
  const { theme, setTheme, colorScheme, setColorScheme } = useTheme();
  const [loggingOut, setLoggingOut] = useState(false);
  const [logoutError, setLogoutError] = useState('');

  const colorOptions = useMemo(() => ([
    { id: 'default', name: 'Blue', color: '#3b82f6' },
    { id: 'red', name: 'Red', color: '#b91c1c' },
    { id: 'orange', name: 'Orange', color: '#f97316' },
    { id: 'brown', name: 'Brown', color: '#a16207' },
  ]), []);

  const userInitial = currentUser?.email?.charAt(0)?.toUpperCase() || 'U';

  async function handleLogout() {
    if (loggingOut) return;
    setLogoutError('');
    setLoggingOut(true);
    try {
      await logout();
      navigate('/login');
    } catch (err) {
      setLogoutError('Unable to sign out right now. Please try again.');
      console.error('Failed to log out', err);
    } finally {
      setLoggingOut(false);
    }
  }

  return (
    <div className="profile-shell">
      <header className="profile-hero">
        <div className="profile-avatar">{userInitial}</div>
        <div className="hero-copy">
          <h1>Your Profile</h1>
          <p>Manage account settings, visual theme, and app accent style.</p>
        </div>
      </header>

      <div className="profile-grid">
        <section className="profile-card account-card">
          <div className="card-title-row">
            <User size={18} />
            <h2>Account</h2>
          </div>

          <div className="detail-row">
            <span className="detail-label"><Mail size={14} /> Email</span>
            <span className="detail-value">{currentUser?.email || 'No email'}</span>
          </div>

          <div className="detail-row">
            <span className="detail-label"><Fingerprint size={14} /> User ID</span>
            <span className="detail-value mono">{currentUser?.uid || 'N/A'}</span>
          </div>
        </section>

        <section className="profile-card">
          <div className="card-title-row">
            <Moon size={18} />
            <h2>Theme</h2>
          </div>

          <div className="theme-switch">
            <button
              className={`theme-chip ${theme === 'light' ? 'active' : ''}`}
              onClick={() => setTheme('light')}
            >
              <Sun size={16} />
              Light
            </button>
            <button
              className={`theme-chip ${theme === 'dark' ? 'active' : ''}`}
              onClick={() => setTheme('dark')}
            >
              <Moon size={16} />
              Dark
            </button>
          </div>
        </section>

        <section className="profile-card accent-card">
          <div className="card-title-row">
            <Palette size={18} />
            <h2>Accent Color</h2>
          </div>

          <div className="color-selection">
            {colorOptions.map((opt) => (
              <button
                key={opt.id}
                className={`swatch ${colorScheme === opt.id ? 'active' : ''}`}
                onClick={() => setColorScheme(opt.id)}
                style={{ '--swatch-color': opt.color }}
                title={opt.name}
                aria-label={opt.name}
              >
                <span className="swatch-dot">
                  {colorScheme === opt.id && <Check className="swatch-check" />}
                </span>
                <span className="swatch-name">{opt.name}</span>
              </button>
            ))}
          </div>
        </section>
      </div>

      <div className="profile-actions">
        <button className="signout-btn" onClick={handleLogout} disabled={loggingOut}>
          <LogOut size={16} />
          {loggingOut ? 'Signing Out...' : 'Sign Out'}
        </button>
        {logoutError && <p className="logout-error">{logoutError}</p>}
      </div>

      <style>{`
        .profile-shell {
          width: 100%;
          min-height: 100%;
          padding: 1.25rem 1rem 2.5rem;
          overflow-y: auto;
        }

        .profile-hero {
          position: relative;
          overflow: hidden;
          border: 1px solid var(--glass-border);
          background: var(--bg-card);
          border-radius: 18px;
          padding: 1.25rem;
          display: flex;
          align-items: center;
          gap: 1rem;
          margin-bottom: 1rem;
        }

        .profile-avatar {
          width: 56px;
          height: 56px;
          border-radius: 16px;
          background: var(--bg-sidebar);
          color: var(--text-sidebar);
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: 800;
          font-size: 1.1rem;
          border: 1px solid var(--secondary-glow);
          flex: 0 0 auto;
        }

        .hero-copy h1 {
          font-size: 1.2rem;
          margin-bottom: 0.25rem;
          letter-spacing: -0.01em;
        }

        .hero-copy p {
          color: var(--text-muted);
          font-size: 0.9rem;
          line-height: 1.45;
        }

        .profile-grid {
          display: grid;
          gap: 0.9rem;
        }

        .profile-card {
          background: var(--bg-card);
          border: 1px solid var(--border);
          border-radius: 16px;
          padding: 1rem;
          display: flex;
          flex-direction: column;
          gap: 0.85rem;
        }

        .card-title-row {
          display: flex;
          align-items: center;
          gap: 0.55rem;
          color: var(--text-main);
          padding-bottom: 0.75rem;
          border-bottom: 1px solid var(--border);
        }

        .card-title-row svg {
          color: var(--secondary);
        }

        .card-title-row h2 {
          font-size: 0.95rem;
          font-weight: 700;
          letter-spacing: 0.01em;
        }

        .detail-row {
          display: flex;
          flex-direction: column;
          gap: 0.4rem;
          padding: 0.7rem;
          border-radius: 12px;
          border: 1px solid var(--border);
          background: var(--bg-input);
        }

        .detail-label {
          display: inline-flex;
          align-items: center;
          gap: 0.4rem;
          color: var(--text-dim);
          font-size: 0.72rem;
          font-weight: 700;
          letter-spacing: 0.08em;
          text-transform: uppercase;
        }

        .detail-value {
          color: var(--text-main);
          font-size: 0.9rem;
          line-height: 1.4;
          overflow-wrap: anywhere;
        }

        .detail-value.mono {
          font-family: var(--font-mono);
          font-size: 0.78rem;
          color: var(--text-muted);
        }

        .signout-btn {
          margin-top: 0.25rem;
          width: 100%;
          min-height: 44px;
          border-radius: 12px;
          border: 1px solid rgba(244, 63, 94, 0.35);
          background: rgba(244, 63, 94, 0.1);
          color: #fb7185;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 0.45rem;
          font-weight: 700;
          transition: var(--transition-base);
        }

        .signout-btn:hover:not(:disabled) {
          background: rgba(244, 63, 94, 0.16);
          transform: translateY(-1px);
        }

        .signout-btn:disabled {
          opacity: 0.65;
          cursor: not-allowed;
        }

        .logout-error {
          color: #fb7185;
          font-size: 0.78rem;
        }

        .theme-switch {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 0.6rem;
        }

        .theme-chip {
          min-height: 42px;
          border-radius: 12px;
          border: 1px solid var(--border);
          background: var(--bg-input);
          color: var(--text-muted);
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 0.5rem;
          font-weight: 600;
          transition: var(--transition-base);
        }

        .theme-chip:hover {
          border-color: var(--border-bright);
          color: var(--text-main);
        }

        .theme-chip.active {
          border-color: var(--secondary);
          background: var(--secondary-glow);
          color: var(--secondary);
        }

        .profile-actions {
          margin-top: 1.5rem;
          max-width: 400px;
          margin-inline: auto;
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }

        .color-selection {
          display: flex;
          flex-direction: row;
          gap: 1rem;
          flex-wrap: wrap;
          padding-top: 0.25rem;
        }

        .swatch {
          width: 38px;
          height: 38px;
          border-radius: 50%;
          border: none;
          background: var(--swatch-color);
          display: flex;
          align-items: center;
          justify-content: center;
          transition: transform 0.2s ease, box-shadow 0.2s ease;
          cursor: pointer;
          box-shadow: var(--shadow-sm);
          padding: 0;
        }

        .swatch-name {
          display: none;
        }

        .swatch-dot {
          display: contents;
        }

        .swatch:hover {
          transform: scale(1.1);
        }

        .swatch.active {
          transform: scale(1.1);
          box-shadow: 0 0 0 3px var(--bg-card), 0 0 0 5px var(--text-main);
        }

        .swatch-check {
          color: #fff;
          width: 18px;
          height: 18px;
          stroke-width: 3px;
        }

        @media (min-width: 769px) {
          .profile-shell {
            max-width: 940px;
            margin: 0 auto;
            padding: 2rem 2rem 3rem;
          }

          .profile-hero {
            margin-bottom: 1.25rem;
            padding: 1.5rem;
          }

          .hero-copy h1 {
            font-size: 1.5rem;
          }

          .profile-grid {
            grid-template-columns: 1.2fr 1fr;
            gap: 1rem;
          }

          .account-card {
            grid-row: span 2;
          }

          .profile-card {
            padding: 1.1rem;
          }

          .color-selection {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0.6rem;
            padding-top: 0;
          }

          .swatch {
            width: auto;
            height: auto;
            border: 1px solid var(--border);
            background: var(--bg-input);
            border-radius: 12px;
            min-height: 46px;
            padding: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.55rem;
            transition: var(--transition-base);
            box-shadow: none;
          }

          .swatch-name {
            display: inline;
            color: var(--text-main);
            font-size: 0.82rem;
            font-weight: 600;
          }

          .swatch-dot {
            display: inline-flex;
            width: 18px;
            height: 18px;
            border-radius: 999px;
            background: var(--swatch-color);
            align-items: center;
            justify-content: center;
            box-shadow: var(--shadow-sm);
          }

          .swatch:hover {
            transform: none;
            border-color: var(--border-bright);
            background: var(--bg-input);
          }

          .swatch.active {
            transform: none;
            box-shadow: none;
            border-color: var(--secondary);
            background: var(--secondary-glow);
          }

          .swatch-check {
            width: 13px;
            height: 13px;
            stroke-width: 2.5px;
          }
        }
      `}</style>
    </div>
  );
}
