import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  InputAdornment,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { ExternalLink, Search, Clock, ChevronRight, ChevronLeft, ArrowUpRight } from 'lucide-react';
import { apiFetch } from '../services/api';

const PAGE_SIZE = 12;

function formatDate(value) {
  if (!value) return 'Unknown';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  }).format(date);
}

function formatAuthors(authors) {
  if (!Array.isArray(authors) || authors.length === 0) return 'No authors recorded';
  return authors.join(', ');
}

function buildArticle(entry) {
  return {
    title: entry.title || 'Untitled Article',
    authors: Array.isArray(entry.authors)
      ? entry.authors.map((name) => {
          const parts = String(name).trim().split(/\s+/);
          return {
            given: parts.slice(0, -1).join(' '),
            family: parts.at(-1) ?? '',
          };
        })
      : [],
    journal: entry.raw?.journal || entry.raw?.venue || 'Unknown Journal',
    date: entry.raw?.publication_year || entry.date || 'Unknown Date',
    doi: entry.doi,
    url: entry.url || (entry.doi ? `https://doi.org/${entry.doi}` : ''),
    abstract: entry.raw?.abstract || null,
    type: entry.raw?.type || 'article',
    pdfUrl: entry.raw?.pdfUrl || entry.raw?.pdf_url || null,
    isOpenAccess: Boolean(entry.raw?.isOpenAccess || entry.raw?.is_open_access),
    oaStatus: entry.raw?.oaStatus || entry.raw?.oa_status || null,
    resolvedVia: entry.raw?.resolvedVia || entry.raw?.resolved_via || null,
  };
}

export default function History() {
  const navigate = useNavigate();
  const [entries, setEntries] = useState([]);
  const [searchInput, setSearchInput] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [offset, setOffset] = useState(0);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setOffset(0);
      setSearchTerm(searchInput.trim());
    }, 250);
    return () => window.clearTimeout(timer);
  }, [searchInput]);

  useEffect(() => {
    let active = true;
    async function loadHistory() {
      try {
        setLoading(true);
        setError('');
        const params = new URLSearchParams({
          limit: String(PAGE_SIZE),
          offset: String(offset),
        });
        if (searchTerm) params.set('q', searchTerm);
        const res = await apiFetch(`/api/history?${params.toString()}`);
        const payload = await res.json();
        if (!active) return;
        setEntries(Array.isArray(payload?.items) ? payload.items : []);
        setTotal(Number(payload?.total) || 0);
      } catch (err) {
        if (!active) return;
        setError(err.message || 'Failed to load history.');
        setEntries([]);
        setTotal(0);
      } finally {
        if (active) setLoading(false);
      }
    }
    loadHistory();
    return () => { active = false; };
  }, [offset, searchTerm]);

  const page = useMemo(() => Math.floor(offset / PAGE_SIZE) + 1, [offset]);
  const pageCount = useMemo(() => Math.max(1, Math.ceil(total / PAGE_SIZE)), [total]);

  const handleView = (entry) => {
    navigate('/', {
      state: {
        historyEntryId: entry.id,
        preloadedArticle: buildArticle(entry),
      },
    });
  };

  return (
    <div className="history-page stagger-in">
      <header className="history-header glass">
        <div className="header-info">
          <div className="activity-tag">
            <Clock size={14} />
            <span>Activity Logs</span>
          </div>
          <h1>Research History</h1>
          <p>Retrieve and re-initialize previously analyzed scholarly identifiers.</p>
        </div>

        <div className="history-search">
          <Search size={18} className="search-icon" />
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Filter by DOI, title, or researcher..."
            className="history-input"
          />
        </div>
      </header>

      {error && <Alert severity="error" className="glass">{error}</Alert>}

      <div className="history-content">
        {loading ? (
          <div className="history-loader">
            <CircularProgress size={32} sx={{ color: 'var(--secondary)' }} />
            <p>Accessing archive...</p>
          </div>
        ) : entries.length === 0 ? (
          <div className="history-empty glass">
            <h3>No entries found</h3>
            <p>{searchTerm ? 'The archive contains no logs matching your query.' : 'Initialize a search to populate your activity logs.'}</p>
          </div>
        ) : (
          <div className="history-grid">
            {entries.map((entry) => (
              <div key={entry.id} className="history-card bento-item interactable" onClick={() => handleView(entry)}>
                <div className="card-header">
                  <span className="card-doi">{entry.doi || 'N/A'}</span>
                  <div className="card-actions">
                    <button className="icon-btn" onClick={(e) => {
                      e.stopPropagation();
                      if (entry.url) window.open(entry.url, '_blank');
                    }}>
                      <ExternalLink size={14} />
                    </button>
                    <button className="view-btn">
                      <ArrowUpRight size={16} />
                    </button>
                  </div>
                </div>
                <div className="card-body">
                  <h3 className="card-title">{entry.title || 'Untitled Archive'}</h3>
                  <p className="card-authors">{formatAuthors(entry.authors)}</p>
                </div>
                <div className="card-footer">
                  <span className="card-date">{formatDate(entry.date)}</span>
                  <div className="card-accent"></div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {entries.length > 0 && (
        <footer className="history-footer glass">
          <div className="page-stats">
            Log segment {page} of {pageCount} <span className="stat-divider">|</span> {total} total records
          </div>
          <div className="pagination-controls">
            <button 
              className="page-btn" 
              disabled={offset === 0} 
              onClick={() => setOffset(v => Math.max(0, v - PAGE_SIZE))}
            >
              <ChevronLeft size={18} />
              <span>Previous</span>
            </button>
            <button 
              className="page-btn primary" 
              disabled={offset + PAGE_SIZE >= total} 
              onClick={() => setOffset(v => v + PAGE_SIZE)}
            >
              <span>Next</span>
              <ChevronRight size={18} />
            </button>
          </div>
        </footer>
      )}

      <style>{`
        .history-page {
          padding: 2rem;
          width: 100%;
          max-width: 1400px;
          margin: 0 auto;
          display: flex;
          flex-direction: column;
          gap: 2rem;
          min-height: 100vh;
        }

        .history-header {
          padding: 2.5rem;
          border-radius: var(--radius-xl);
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 2rem;
        }

        .header-info h1 {
          font-size: 2.5rem;
          font-weight: 800;
          margin: 0.5rem 0;
          letter-spacing: -0.04em;
        }

        .header-info p {
          color: var(--text-muted);
          font-size: 0.95rem;
        }

        .activity-tag {
          display: inline-flex;
          align-items: center;
          gap: 0.5rem;
          background: var(--secondary-glow);
          color: var(--secondary);
          padding: 0.25rem 0.75rem;
          border-radius: var(--radius-full);
          font-family: var(--font-mono);
          font-size: 0.65rem;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.1em;
          border: 1px solid var(--secondary-glow);
        }

        .history-search {
          flex: 1;
          max-width: 450px;
          position: relative;
          display: flex;
          align-items: center;
        }

        .search-icon {
          position: absolute;
          left: 1.25rem;
          color: var(--text-dim);
          pointer-events: none;
        }

        .history-input {
          width: 100%;
          padding: 1rem 1.25rem 1rem 3.5rem;
          background: rgba(0,0,0,0.2);
          border: 1px solid var(--border);
          border-radius: var(--radius-lg);
          color: var(--text-main);
          font-family: var(--font-body);
          outline: none;
          transition: var(--transition-base);
        }

        .history-input:focus {
          border-color: var(--secondary);
          box-shadow: 0 0 0 4px var(--secondary-glow);
          background: rgba(0,0,0,0.4);
        }

        .history-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
          gap: 1.5rem;
        }

        .history-card {
          display: flex;
          flex-direction: column;
          gap: 1.5rem;
          min-height: 240px;
          cursor: pointer;
        }

        .card-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
        }

        .card-doi {
          font-family: var(--font-mono);
          font-size: 0.7rem;
          color: var(--secondary);
          background: var(--secondary-glow);
          padding: 0.2rem 0.5rem;
          border-radius: var(--radius-sm);
          opacity: 0.8;
        }

        .card-actions {
          display: flex;
          gap: 0.5rem;
        }

        .icon-btn, .view-btn {
          background: var(--bg-body);
          border: 1px solid var(--border);
          color: var(--text-dim);
          width: 32px;
          height: 32px;
          border-radius: var(--radius-sm);
          display: flex;
          align-items: center;
          justify-content: center;
          cursor: pointer;
          transition: var(--transition-fast);
        }

        .icon-btn:hover, .view-btn:hover {
          color: var(--text-main);
          border-color: var(--border-bright);
          background: var(--primary-glow);
        }

        .card-title {
          font-size: 1.15rem;
          font-weight: 700;
          line-height: 1.3;
          margin-bottom: 0.75rem;
          display: -webkit-box;
          -webkit-line-clamp: 3;
          -webkit-box-orient: vertical;
          overflow: hidden;
        }

        .card-authors {
          font-size: 0.85rem;
          color: var(--text-muted);
          line-height: 1.5;
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
          overflow: hidden;
        }

        .card-footer {
          margin-top: auto;
          padding-top: 1rem;
          border-top: 1px solid var(--border);
          display: flex;
          align-items: center;
          justify-content: space-between;
        }

        .card-date {
          font-family: var(--font-mono);
          font-size: 0.65rem;
          color: var(--text-dim);
          text-transform: uppercase;
        }

        .card-accent {
          width: 4px;
          height: 4px;
          border-radius: 50%;
          background: var(--secondary);
          box-shadow: 0 0 8px var(--secondary);
        }

        .history-loader, .history-empty {
          padding: 6rem 2rem;
          text-align: center;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 1.5rem;
          border-radius: var(--radius-xl);
        }

        .history-loader p {
          font-family: var(--font-mono);
          font-size: 0.8rem;
          color: var(--text-dim);
          text-transform: uppercase;
          letter-spacing: 0.1em;
        }

        .history-footer {
          padding: 1.5rem 2.5rem;
          border-radius: var(--radius-xl);
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-top: auto;
        }

        .page-stats {
          font-family: var(--font-mono);
          font-size: 0.75rem;
          color: var(--text-dim);
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }

        .stat-divider {
          margin: 0 1rem;
          opacity: 0.3;
        }

        .pagination-controls {
          display: flex;
          gap: 1rem;
        }

        .page-btn {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          padding: 0.75rem 1.25rem;
          background: var(--bg-body);
          border: 1px solid var(--border);
          color: var(--text-muted);
          border-radius: var(--radius-md);
          font-weight: 700;
          font-size: 0.75rem;
          text-transform: uppercase;
          letter-spacing: 0.05em;
          transition: var(--transition-base);
          cursor: pointer;
        }

        .page-btn:hover:not(:disabled) {
          border-color: var(--border-bright);
          color: var(--text-main);
          background: var(--primary-glow);
        }

        .page-btn.primary {
          background: var(--secondary);
          color: white;
          border: none;
        }

        .page-btn.primary:hover:not(:disabled) {
          filter: brightness(1.1);
          transform: translateY(-1px);
        }

        .page-btn:disabled {
          opacity: 0.3;
          cursor: not-allowed;
        }

        @media (max-width: 1024px) {
          .history-header {
            flex-direction: column;
            align-items: stretch;
            padding: 2rem;
          }
          .history-search {
            max-width: 100%;
          }
        }

        @media (max-width: 768px) {
          .history-page {
            padding: 1rem;
          }
          .history-header h1 {
            font-size: 1.75rem;
          }
          .history-footer {
            flex-direction: column;
            gap: 1.5rem;
            text-align: center;
          }
        }
      `}</style>
    </div>
  );
}
