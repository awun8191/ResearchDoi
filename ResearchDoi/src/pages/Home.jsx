import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import SearchInput from '../components/SearchInput';
import ArticleCard from '../components/ArticleCard';
import ArticleSkeleton from '../components/ArticleSkeleton';
import { fetchArticle, searchArticles } from '../services/arxiv';
import Logo from '../components/Logo';

export default function Home() {
  const location = useLocation();
  const navigate = useNavigate();
  const [article, setArticle] = useState(null);
  const [searchResults, setSearchResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalResults, setTotalResults] = useState(0);
  const [currentQuery, setCurrentQuery] = useState('');

  useEffect(() => {
    if (!location.state?.preloadedArticle) return;

    setError(null);
    setLoading(false);
    setArticle(location.state.preloadedArticle);
    navigate(location.pathname, { replace: true, state: null });
  }, [location.pathname, location.state, navigate]);

  const handleSearch = async (query, mode = 'auto', page = 1) => {
    setError(null);
    setArticle(null);
    if (page === 1) {
      setSearchResults([]);
      setTotalResults(0);
    }
    setCurrentQuery(query);
    setCurrentPage(page);

    const looksLikeId = (val) => {
      const clean = val.toLowerCase().trim();
      // DOI: starts with 10. or has doi: prefix
      if (clean.startsWith('10.') || clean.includes('doi:')) return true;
      // ArXiv: digits.digits or arxiv:
      if (/^(\d{4}\.\d{4,5}(v\d+)?|arxiv:[a-z.-]+\/\d+)/.test(clean)) return true;
      // Plain ArXiv IDs without prefix (e.g. 1706.03762)
      if (/^\d{4}\.\d{4,5}(v\d+)?$/.test(clean)) return true;
      return false;
    };

    try {
      setLoading(true);
      
      const shouldFetchDirect = 
        mode === 'id' || 
        (mode === 'auto' && looksLikeId(query));

      if (shouldFetchDirect) {
        const data = await fetchArticle(query);
        setArticle(data);
      } else {
        const limit = 10;
        const offset = (page - 1) * limit;
        const { results, total } = await searchArticles(query, limit, offset);
        setSearchResults(results);
        setTotalResults(total);
        if (results.length === 0) {
          setError('No results found for your query.');
        }
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const selectArticle = async (selectedArticle) => {
    setArticle(selectedArticle);
    // Optionally fetch more details if the search result was a summary
    if (!selectedArticle.abstract) {
      try {
        setLoading(true);
        const detailed = await fetchArticle(selectedArticle.doi);
        setArticle(detailed);
      } catch (err) {
        console.warn('Failed to fetch detailed abstract:', err);
      } finally {
        setLoading(false);
      }
    }
  };

  return (
    <div className={`home-content ${(article || searchResults.length > 0) ? 'split-view' : ''}`}>
      <div className="layout-wrapper">
        <div className="left-pane">
          <div className={`hero-section ${(article || searchResults.length > 0) ? 'compact' : ''}`}>
            <div className="brand-logo slide-up">
              <div className="brand-title">
                <Logo size={200} useGradient={true} useSchemeColor={true} />
              </div>
              <p className="brand-tagline">Research Analysis & Scholarly Tracking</p>
            </div>

            <div className="search-wrapper slide-up" style={{ animationDelay: '0.1s' }}>
              <div className="glass-search-container">
                <SearchInput onSearch={handleSearch} loading={loading} />
              </div>
              <div className="quick-actions">
                <button className="action-trigger" onClick={async () => {
                  try {
                    const text = await navigator.clipboard.readText();
                    if (text) {
                      // Trigger search immediately if it looks like a DOI/ArXiv ID
                      handleSearch(text.trim(), 'auto');
                    }
                  } catch {
                    console.error('Clipboard access denied');
                  }
                }}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
                  <span>PASTE IDENTIFIER</span>
                </button>
                <div className="action-divider"></div>
                <label className="action-trigger" style={{ cursor: 'pointer' }}>
                  <input type="file" style={{ display: 'none' }} onChange={(e) => {
                    const file = e.target.files[0];
                    if (file) {
                      alert(`File "${file.name}" received. Scientific batch analysis coming soon.`);
                    }
                  }} />
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="17 8 12 3 7 8"></polyline><line x1="12" y1="3" x2="12" y2="15"></line></svg>
                  <span>UPLOAD ARCHIVE</span>
                </label>
              </div>
            </div>

            {error && (
              <div className="error-toast glass slide-up">
                <div className="error-icon">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
                </div>
                <div className="error-content">
                  <span className="error-label">Initialization Error</span>
                  <p>{error}</p>
                </div>
              </div>
            )}
          </div>
        </div>

        <div className={`right-pane ${(article || searchResults.length > 0) ? 'visible' : ''}`}>
          <div className="results-container">
            {loading ? (
              <ArticleSkeleton />
            ) : article ? (
              <div className="detail-view slide-up">
                <button className="back-to-results" onClick={() => {
                  if (searchResults.length > 0) setArticle(null);
                  else setArticle(null); // Just clear if no results
                }}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6"/></svg>
                  <span> {searchResults.length > 0 ? 'BACK TO RESULTS' : 'CLEAR'}</span>
                </button>
                <ArticleCard article={article} />
              </div>
            ) : searchResults.length > 0 ? (
              <div className="search-results-list slide-up">
                <div className="results-header">
                  <span className="results-count">{totalResults > 10 ? 'MULTIPLE PAPERS FOUND' : `${searchResults.length} PAPERS FOUND`}</span>
                  <button className="clear-results" onClick={() => { setSearchResults([]); setTotalResults(0); setCurrentPage(1); setCurrentQuery(''); }}>CLEAR</button>
                </div>
                {searchResults.map((res, idx) => (
                  <div 
                    key={res.doi || idx} 
                    className="search-result-item"
                    onClick={() => selectArticle(res)}
                    style={{ animationDelay: `${idx * 0.05}s` }}
                  >
                    <div className="res-meta">
                      <span className="res-date">{res.date}</span>
                      <span className="res-venue">{res.journal}</span>
                      {res.pdfUrl && <span className="res-pdf-badge"><svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg> PDF AVAILABLE</span>}
                    </div>
                    <h3 className="res-title">{res.title}</h3>
                    <div className="res-authors">{res.authors.map(a => `${a.given} ${a.family}`).join(', ')}</div>
                  </div>
                ))}

                {/* Pagination Controls */}
                <div className="search-results-footer">
                  <div className="page-stats">
                    Page {currentPage} <span className="stat-divider">|</span> Showing {((currentPage - 1) * 10) + 1} - {Math.min(currentPage * 10, totalResults)}
                  </div>
                  <div className="pagination-controls">
                    <button 
                      className="page-btn" 
                      disabled={currentPage === 1 || loading} 
                      onClick={() => handleSearch(currentQuery, 'auto', currentPage - 1)}
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6"/></svg>
                      <span>Previous</span>
                    </button>
                    <button 
                      className="page-btn primary" 
                      disabled={currentPage * 10 >= totalResults || loading} 
                      onClick={() => handleSearch(currentQuery, 'auto', currentPage + 1)}
                    >
                      <span>Next</span>
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="m9 18 6-6-6-6"/></svg>
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              <div className="empty-results-lab">
                <div className="lab-placeholder">
                  <div className="lab-text">
                    <h3>IDLE</h3>
                    <p>SYSTEM READY FOR RESOLUTION</p>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      <style>{`
        .home-content {
          width: 100%;
          min-height: 100vh;
          background: transparent;
        }

        .layout-wrapper {
          display: flex;
          width: 100%;
          height: 100vh;
          overflow: hidden;
        }

        .left-pane {
          flex: 1;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 2rem;
          transition: flex 400ms var(--ease-out), background 400ms var(--ease-out), backdrop-filter 400ms var(--ease-out), border-right 400ms var(--ease-out);
          position: relative;
        }

        .split-view .left-pane {
          flex: 0 0 45%;
          border-right: 1px solid var(--glass-border);
          background: var(--bg-surface);
          backdrop-filter: blur(10px);
        }

        .right-pane {
          flex: 0;
          opacity: 0;
          visibility: hidden;
          background: transparent;
          transition: flex 400ms var(--ease-out), opacity 400ms var(--ease-out), visibility 400ms var(--ease-out);
          overflow-y: auto;
          display: flex;
          flex-direction: column;
        }

        .split-view .right-pane {
          flex: 1;
          opacity: 1;
          visibility: visible;
        }

        .hero-section {
          width: 100%;
          max-width: 640px;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 3.5rem;
          transition: var(--transition-base);
        }

        .hero-section.compact {
          transform: translateY(-10px);
        }

        .brand-logo {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 1rem;
          text-align: center;
        }

        .brand-title {
          font-size: 3rem;
          font-weight: 700;
          letter-spacing: -0.04em;
          color: #ffffff;
        }

        .brand-tagline {
          font-family: var(--font-mono);
          font-size: 0.7rem;
          color: var(--text-dim);
          text-transform: uppercase;
          letter-spacing: 0.25em;
          margin-top: -0.5rem;
        }

        .search-wrapper {
          width: 100%;
          display: flex;
          flex-direction: column;
          gap: 1.5rem;
        }

        .glass-search-container {
          position: relative;
          padding: 8px;
          border-radius: var(--radius-xl);
          background: var(--bg-surface);
          border: 1px solid var(--glass-border);
          backdrop-filter: var(--glass-blur);
          box-shadow: var(--shadow-inner), var(--shadow-md);
        }

        .quick-actions {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 1.25rem;
        }

        .action-trigger {
          background: transparent;
          border: none;
          display: flex;
          align-items: center;
          gap: 0.6rem;
          color: var(--text-muted);
          font-family: var(--font-mono);
          font-size: 0.65rem;
          font-weight: 700;
          letter-spacing: 0.1em;
          padding: 0.6rem 0.8rem;
          border-radius: var(--radius-sm);
          transition: var(--transition-base);
          cursor: pointer;
        }

        .action-trigger:hover {
          color: var(--secondary);
          background: var(--secondary-glow);
        }

        .action-divider {
          width: 1px;
          height: 12px;
          background: var(--border);
        }

        .results-container {
          padding: 3rem;
          min-height: 100%;
          max-width: 900px;
          margin: 0 auto;
        }

        .back-to-results {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          background: transparent;
          border: none;
          color: var(--text-dim);
          font-family: var(--font-mono);
          font-size: 0.65rem;
          font-weight: 700;
          cursor: pointer;
          margin-bottom: 2rem;
          transition: color 0.2s;
        }

        .back-to-results:hover {
          color: var(--secondary);
        }

        .search-results-list {
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }

        .search-results-footer {
          padding: 1.25rem 2rem;
          border-radius: var(--radius-lg);
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-top: 1.5rem;
          background: var(--bg-card);
          border: 1px solid var(--glass-border);
          backdrop-filter: var(--glass-blur);
          box-shadow: var(--shadow-inner), var(--shadow-sm);
        }

        .page-stats {
          font-family: var(--font-mono);
          font-size: 0.75rem;
          color: var(--text-dim);
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }

        .stat-divider {
          margin: 0 0.75rem;
          opacity: 0.3;
        }

        .pagination-controls {
          display: flex;
          gap: 0.75rem;
        }

        .page-btn {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.6rem 1.2rem;
          background: var(--bg-body);
          border: 1px solid var(--glass-border);
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

        .results-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 2rem;
          padding-bottom: 1rem;
          border-bottom: 1px solid var(--border);
        }

        .results-count {
          font-family: var(--font-mono);
          font-size: 0.7rem;
          font-weight: 800;
          color: var(--secondary);
          letter-spacing: 0.1em;
        }

        .clear-results {
          background: transparent;
          border: none;
          font-family: var(--font-mono);
          font-size: 0.6rem;
          color: var(--text-dim);
          cursor: pointer;
        }

        .search-result-item {
          padding: 1.5rem;
          border: 1px solid var(--glass-border);
          border-radius: var(--radius-lg);
          background: var(--bg-card);
          backdrop-filter: var(--glass-blur);
          cursor: pointer;
          transition: transform var(--transition-base), background var(--transition-base), border-color var(--transition-base), box-shadow var(--transition-base);
          animation: slide-up 0.5s var(--ease-out) backwards;
          box-shadow: var(--shadow-inner), var(--shadow-sm);
        }

        .search-result-item:hover {
          background: var(--bg-surface);
          border-color: var(--border-bright);
          transform: translateY(-4px);
          box-shadow: var(--shadow-inner), var(--shadow-md), var(--shadow-glow);
        }

        .res-meta {
          display: flex;
          gap: 1rem;
          font-family: var(--font-mono);
          font-size: 0.6rem;
          color: var(--text-dim);
          margin-bottom: 0.75rem;
          text-transform: uppercase;
        }

        .res-title {
          font-size: 1.1rem;
          font-weight: 700;
          color: var(--text-main);
          line-height: 1.4;
          margin-bottom: 0.5rem;
        }

        .res-authors {
          font-size: 0.8rem;
          color: var(--text-muted);
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .res-pdf-badge {
          display: flex;
          align-items: center;
          gap: 0.3rem;
          background: var(--accent-glow);
          color: var(--accent);
          padding: 0.15rem 0.5rem;
          border-radius: 4px;
          font-weight: 800;
          letter-spacing: 0.05em;
        }

        .empty-results-lab {
          height: 100%;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .lab-placeholder {
          padding: 3rem 4rem;
          border-radius: var(--radius-xl);
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 1.5rem;
          text-align: center;
          border: 1px solid var(--glass-border);
        }

        .pulse-circle {
          width: 12px;
          height: 12px;
          background: var(--secondary);
          border-radius: 50%;
          box-shadow: 0 0 20px var(--secondary);
          animation: pulse-glow 2s infinite;
        }

        .lab-text h3 {
          font-family: var(--font-mono);
          font-size: 0.9rem;
          letter-spacing: 0.3em;
          color: var(--text-main);
          margin-bottom: 0.5rem;
        }

        .lab-text p {
          font-size: 0.85rem;
          color: var(--text-dim);
        }

        .error-toast {
          display: flex;
          align-items: flex-start;
          gap: 1rem;
          padding: 1rem 1.25rem;
          border-radius: var(--radius-md);
          border-left: 3px solid #ef4444;
          background: rgba(239, 68, 68, 0.05);
        }

        .error-icon {
          color: #ef4444;
          margin-top: 2px;
        }

        .error-label {
          display: block;
          font-weight: 700;
          font-size: 0.75rem;
          color: #ef4444;
          text-transform: uppercase;
          margin-bottom: 0.25rem;
        }

        @media (max-width: 1024px) {
          .layout-wrapper {
            flex-direction: column;
            overflow-y: auto;
            height: auto;
          }
          .left-pane {
            min-height: 80vh;
          }
          .split-view .left-pane {
            flex: 0 0 auto;
            width: 100%;
            height: auto;
            padding: 4rem 1.5rem;
          }
          .results-container {
            padding: 1.5rem;
          }
        }


        @media (max-width: 768px) {
          .left-pane {
            min-height: calc(100vh - var(--navbar-height) - 24px);
            padding: 2rem 1rem;
            justify-content: center;
          }

          .split-view .left-pane {
            min-height: auto;
            padding: 1.4rem 1rem 1.1rem;
            justify-content: flex-start;
          }

          .split-view .right-pane {
            padding: 0 0.75rem 1rem;
          }

          .results-container {
            padding: 0.75rem 0;
          }
        }
      `}</style>
    </div>
  );
}
