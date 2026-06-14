import React, { useMemo } from 'react';
import { useTheme } from '../context/ThemeContext';
import { Palette, Check } from 'lucide-react';

export default function Profile() {
  const { colorScheme, setColorScheme } = useTheme();

  const colorOptions = useMemo(() => ([
    { id: 'default', name: 'Blue', color: '#0ea5e9' },
    { id: 'red', name: 'Red', color: '#dc2626' },
    { id: 'orange', name: 'Orange', color: '#ea580c' },
    { id: 'brown', name: 'Brown', color: '#a16207' },
  ]), []);

  return (
    <div className="profile-shell">
      <h1 className="profile-heading">Settings</h1>

      <section className="profile-card">
        <div className="card-title-row">
          <Palette size={16} />
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

      <style>{`
        .profile-shell {
          width: 100%;
          max-width: 560px;
          margin: 0 auto;
          padding: 2.5rem 1.5rem;
          overflow-y: auto;
          min-height: 100%;
        }

        .profile-heading {
          font-size: 1.5rem;
          font-weight: 700;
          color: var(--text-main);
          margin-bottom: 1.5rem;
          letter-spacing: -0.02em;
        }

        .profile-card {
          background: var(--bg-card);
          border: 1px solid var(--border);
          border-radius: 14px;
          padding: 1.25rem;
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }

        .card-title-row {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          color: var(--text-muted);
          padding-bottom: 0.75rem;
          border-bottom: 1px solid var(--border);
        }

        .card-title-row svg {
          color: var(--text-dim);
        }

        .card-title-row h2 {
          font-size: 0.85rem;
          font-weight: 600;
          letter-spacing: 0.02em;
        }

        .color-selection {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 0.5rem;
        }

        .swatch {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 0.5rem;
          min-height: 44px;
          border-radius: 10px;
          border: 1px solid var(--border);
          background: var(--bg-input);
          cursor: pointer;
          transition: border-color 0.2s ease, background 0.2s ease;
          padding: 0.5rem;
        }

        .swatch:hover {
          border-color: var(--border-bright);
        }

        .swatch.active {
          border-color: var(--secondary);
          background: var(--secondary-glow);
        }

        .swatch-dot {
          width: 16px;
          height: 16px;
          border-radius: 50%;
          background: var(--swatch-color);
          display: inline-flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
        }

        .swatch-name {
          font-size: 0.78rem;
          font-weight: 600;
          color: var(--text-muted);
        }

        .swatch.active .swatch-name {
          color: var(--secondary);
        }

        .swatch-check {
          color: #fff;
          width: 11px;
          height: 11px;
          stroke-width: 3px;
        }

        @media (max-width: 768px) {
          .profile-shell {
            padding: 1.5rem 1rem;
          }

          .color-selection {
            grid-template-columns: repeat(2, 1fr);
          }
        }
      `}</style>
    </div>
  );
}
