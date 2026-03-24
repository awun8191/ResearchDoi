import React, { useState } from 'react';

/**
 * @param {Object} props
 * @param {function(string): void} props.onSearch
 * @param {boolean} props.loading
 */
export default function SearchInput({ onSearch, loading }) {
  const [doi, setDoi] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (doi.trim()) onSearch(doi.trim());
  };

  return (
    <form onSubmit={handleSubmit} className="search-form-grok">
      <div className="input-pill">
        <div className="pill-left">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="pill-icon">
            <path d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
          </svg>
          <input
            type="text"
            className="grok-input"
            placeholder="Search with DOI or keyword..."
            value={doi}
            onChange={(e) => setDoi(e.target.value)}
          />
        </div>

        <div className="pill-actions">
          <button type="submit" className="pill-submit" disabled={loading || !doi.trim()}>
            {loading ? (
              <div className="loader-ring"></div>
            ) : (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="12" y1="5" x2="12" y2="19"></line>
                <polyline points="19 12 12 19 5 12"></polyline>
              </svg>
            )}
          </button>
        </div>
      </div>

      <style>{`
        .search-form-grok {
          width: 100%;
          max-width: 600px;
          margin: 0 auto;
        }
:root {
  --font-heading: 'Outfit', sans-serif;
  --font-body: 'Inter', sans-serif;
}
        .input-pill {
          display: flex;
          align-items: center;
          justify-content: space-between;
          background: var(--bg-input);
          border: 1px solid var(--border);
          border-radius: var(--radius-full);
          padding: 0.65rem 0.65rem 0.65rem 1.75rem;
          transition: var(--transition-base);
          box-shadow: var(--shadow-sm);
          position: relative;
          overflow: hidden;
        }

        .input-pill::before {
          content: '';
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: linear-gradient(90deg, transparent, rgba(255,255,255,0.03), transparent);
          transform: translateX(-100%);
          transition: transform 0.8s ease;
          pointer-events: none;
        }

        .input-pill:hover::before {
          transform: translateX(100%);
        }

        .input-pill:focus-within {
          border-color: var(--secondary);
          background: var(--bg-surface);
          box-shadow: 0 0 0 2px var(--secondary-glow), 0 0 35px var(--secondary-glow);
        }

        .pill-left {
          display: flex;
          align-items: center;
          gap: 1.25rem;
          flex: 1;
        }

        .pill-icon {
          color: var(--text-dim);
          transition: var(--transition-fast);
        }

        .input-pill:focus-within .pill-icon {
          color: var(--secondary);
          transform: scale(1.1);
        }

        .grok-input {
          flex: 1;
          background: transparent;
          border: none;
          color: var(--text-main);
          font-size: 1.05rem;
          font-weight: 500;
          outline: none;
          width: 100%;
          font-family: var(--font-body);
        }

        .grok-input::placeholder {
          color: var(--text-dim);
        }

        .pill-actions {
          display: flex;
          align-items: center;
          gap: 0.85rem;
        }


        .pill-submit {
          width: 42px;
          height: 42px;
          border-radius: 50%;
          background: var(--text-main);
          color: var(--text-inverse);
          display: flex;
          align-items: center;
          justify-content: center;
          transition: var(--transition-base);
          box-shadow: var(--shadow-md);
        }

        .pill-submit:hover:not(:disabled) {
          transform: scale(1.05) translateY(-1px);
          box-shadow: 0 4px 20px rgba(255,255,255,0.2);
        }

        .pill-submit:active:not(:disabled) {
          transform: scale(0.95);
        }

        .pill-submit:disabled {
          background: var(--bg-surface);
          color: var(--text-dim);
          cursor: not-allowed;
          opacity: 0.5;
        }

        .loader-ring {
          width: 20px;
          height: 20px;
          border: 2px solid rgba(0,0,0,0.1);
          border-top-color: currentColor;
          border-radius: 50%;
          animation: spin 0.8s linear infinite;
        }

        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </form>
  );
}
