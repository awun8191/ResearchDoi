import { useState } from 'react';
import SearchInput from '../components/SearchInput';
import ArticleCard from '../components/ArticleCard';
import ArticleSkeleton from '../components/ArticleSkeleton';
import { fetchArticle } from '../services/crossref';
import Logo from '../components/Logo';

export default function Home() {
  const [article, setArticle] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSearch = async (doi) => {
    setError(null);
    setArticle(null);

    try {
      setLoading(true);
      const data = await fetchArticle(doi);
      setArticle(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={`home-content ${article ? 'split-view' : ''}`}>
      <div className="layout-wrapper">
        <div className="left-pane">
          <div className={`hero-section ${article ? 'compact' : ''}`}>
            <div className="brand-logo slide-up">
              <div className="brand-title">
                <Logo size={180} useGradient={true} useSchemeColor={true} />
              </div>
            </div>

            <div className="search-wrapper slide-up" style={{ animationDelay: '0.1s' }}>
              <SearchInput onSearch={handleSearch} loading={loading} />
            </div>

            {error && (
              <div className="error-toast glass slide-up">
                <span className="error-label">Analysis Error</span>
                <p>{error}</p>
              </div>
            )}
          </div>
        </div>

        <div className={`right-pane ${article ? 'visible' : ''}`}>
          <div className="results-container glass">
            {loading ? (
              <ArticleSkeleton />
            ) : article ? (
              <ArticleCard article={article} />
            ) : (
              <div className="empty-results">
                <p>Enter a DOI to begin technical analysis</p>
              </div>
            )}
          </div>
        </div>
      </div>

      <style>{`
        .home-content {
          width: 100%;
          min-height: 100vh;
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
          transition: all 0.6s cubic-bezier(0.16, 1, 0.3, 1);
          background: var(--bg-body);
          position: relative;
        }

        .split-view .left-pane {
          flex: 0 0 50%;
          border-right: 1px solid var(--border);
        }

        .right-pane {
          flex: 0;
          opacity: 0;
          visibility: hidden;
          background: var(--bg-surface);
          transition: all 0.6s cubic-bezier(0.16, 1, 0.3, 1);
          overflow-y: auto;
          display: flex;
          flex-direction: column;
        }

        .split-view .right-pane {
          flex: 0 0 50%;
          opacity: 1;
          visibility: visible;
        }

        .hero-section {
          width: 100%;
          max-width: 600px;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 2.5rem;
          transition: var(--transition-base);
        }

        .hero-section.compact {
          transform: translateY(-20px);
        }

        .brand-logo {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 1.5rem;
          color: var(--text-main);
          z-index: 10;
        }

        .brand-logo svg {
          filter: drop-shadow(var(--shadow-glow));
          animation: float 6s ease-in-out infinite;
        }

        @keyframes float {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-10px); }
        }

        .brand-title {
          width: 420px;
          height: auto;
          display: flex;
          align-items: center;
          justify-content: center;
          filter: drop-shadow(var(--shadow-glow));
        }

        .search-wrapper {
          width: 100%;
          z-index: 10;
        }

        .results-container {
          padding: 2rem;
          min-height: 100%;
          border: none;
          background: transparent;
          backdrop-filter: none;
        }

        .empty-results {
          height: 100%;
          display: flex;
          align-items: center;
          justify-content: center;
          color: var(--text-dim);
          font-style: italic;
        }

        @media (max-width: 1024px) {
          .layout-wrapper {
            flex-direction: column;
            overflow-y: auto;
            height: auto;
          }
          .left-pane {
            flex: 1;
            min-height: 80vh;
            padding: 3rem 1.5rem;
            border-right: none;
            align-items: center;
            justify-content: center;
            text-align: center;
          }
          .split-view .left-pane {
            flex: 0 0 auto;
            width: 100%;
            height: auto;
            padding: 3rem 1.5rem;
            border-right: none;
            border-bottom: 1px solid var(--border);
          }
          .split-view .right-pane {
            flex: 1;
            width: 100%;
            opacity: 1;
            visibility: visible;
            padding: 0 1rem 1.25rem;
          }
          .hero-section {
            gap: 1.5rem;
          }
          .brand-title {
            width: 300px;
          }
          .results-container {
            width: 100%;
            max-width: 760px;
            margin: 0 auto;
            padding: 1.25rem;
            min-height: auto;
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
