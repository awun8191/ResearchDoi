import React, { useState } from 'react';

/**
 * @param {Object} props
 * @param {function(string): void} props.onSearch
 * @param {boolean} props.loading
 */
export default function SearchInput({ onSearch, loading }) {
  const [query, setQuery] = useState('');
  const [searchMode, setSearchMode] = useState('auto'); // auto, id, topic

  const handleSubmit = (e) => {
    e.preventDefault();
    if (query.trim()) onSearch(query.trim(), searchMode);
  };

  return (
    <form onSubmit={handleSubmit} className="search-form-lab">
      <div className="search-mode-selector slide-up">
        <button 
          type="button"
          className={`mode-btn ${searchMode === 'auto' ? 'active' : ''}`}
          onClick={() => setSearchMode('auto')}
        >
          AUTO
        </button>
        <button 
          type="button"
          className={`mode-btn ${searchMode === 'id' ? 'active' : ''}`}
          onClick={() => setSearchMode('id')}
        >
          IDENTIFIER
        </button>
        <button 
          type="button"
          className={`mode-btn ${searchMode === 'topic' ? 'active' : ''}`}
          onClick={() => setSearchMode('topic')}
        >
          TOPIC
        </button>
      </div>

      <div className="input-lab glass">
        <div className="lab-left">
          <div className="id-tag">
            {searchMode === 'auto' ? 'AI DETECT' : searchMode.toUpperCase()}
          </div>
          <input
            type="text"
            className="lab-input"
            placeholder={
              searchMode === 'id' ? "Enter DOI or ArXiv ID..." :
              searchMode === 'topic' ? "Enter research topic..." :
              "Search scholarly DOI or keyword..."
            }
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>

        <div className="lab-actions">
          <button type="submit" className="lab-submit" disabled={loading || !query.trim()}>
            {loading ? (
              <div className="loader-ring"></div>
            ) : (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M5 12h14"></path>
                <path d="m12 5 7 7-7 7"></path>
              </svg>
            )}
          </button>
        </div>
      </div>

      <style>{`
        .search-form-lab {
          width: 100%;
          max-width: 600px;
          margin: 0 auto;
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }

        .search-mode-selector {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.25rem;
          background: rgba(255, 255, 255, 0.03);
          border: 1px solid var(--border);
          border-radius: 12px;
          width: fit-content;
          align-self: center;
        }

        .mode-btn {
          background: transparent;
          border: none;
          padding: 0.5rem 1rem;
          border-radius: 8px;
          font-family: var(--font-mono);
          font-size: 0.6rem;
          font-weight: 700;
          color: var(--text-dim);
          cursor: pointer;
          transition: all 0.2s ease;
          letter-spacing: 0.05em;
        }

        .mode-btn:hover {
          color: var(--text-main);
          background: rgba(255, 255, 255, 0.05);
        }

        .mode-btn.active {
          background: var(--secondary);
          color: #fff;
          box-shadow: 0 4px 12px var(--secondary-glow);
        }

        .input-lab {
          display: flex;
          align-items: center;
          justify-content: space-between;
          background: rgba(0, 0, 0, 0.6);
          border: 1px solid var(--border);
          border-radius: 18px;
          padding: 0.65rem 0.65rem 0.65rem 1.25rem;
          transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
          box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
          position: relative;
        }

        .input-lab:focus-within {
          border-color: var(--secondary);
          background: rgba(15, 23, 42, 0.6);
          box-shadow: 0 0 40px var(--secondary-glow);
          transform: translateY(-2px);
        }

        .lab-left {
          display: flex;
          align-items: center;
          gap: 1.25rem;
          flex: 1;
        }

        .id-tag {
          font-family: var(--font-mono);
          font-size: 0.6rem;
          font-weight: 800;
          color: var(--secondary);
          background: var(--secondary-glow);
          padding: 0.25rem 0.6rem;
          border-radius: 4px;
          letter-spacing: 0.15em;
          border: 1px solid var(--secondary-glow);
          opacity: 0.8;
        }

        .lab-input {
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

        .lab-input::placeholder {
          color: var(--text-dim);
          font-weight: 400;
        }

        .lab-actions {
          display: flex;
          align-items: center;
        }

        .lab-submit {
          width: 44px;
          height: 44px;
          border-radius: var(--radius-md);
          background: var(--secondary);
          color: #ffffff;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: var(--transition-base);
          border: none;
          cursor: pointer;
          box-shadow: 0 4px 12px var(--secondary-glow);
        }

        .lab-submit:hover:not(:disabled) {
          transform: scale(1.05);
          filter: brightness(1.1);
          box-shadow: 0 0 20px var(--secondary);
        }

        .lab-submit:active:not(:disabled) {
          transform: scale(0.95);
        }

        .lab-submit:disabled {
          background: rgba(255,255,255,0.05);
          color: var(--text-dim);
          cursor: not-allowed;
          opacity: 0.5;
          box-shadow: none;
        }

        .loader-ring {
          width: 20px;
          height: 20px;
          border: 2px solid rgba(255,255,255,0.1);
          border-top-color: #ffffff;
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
