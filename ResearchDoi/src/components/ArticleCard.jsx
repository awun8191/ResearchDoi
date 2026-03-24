import React, { useState } from 'react';

export default function ArticleCard({ article }) {
  const [copyStatus, setCopyStatus] = useState(null);

  if (!article) return null;

  const cleanAbstract = article.abstract
    ? article.abstract.replace(/<[^>]+>/g, '')
    : null;

  const copyToClipboard = (text, field) => {
    navigator.clipboard.writeText(text);
    setCopyStatus(field);
    setTimeout(() => setCopyStatus(null), 2000);
  };


  const formatDate = (dateStr) => {
    // Attempt to format date to "1 June 2025" style
    try {
      const date = new Date(dateStr);
      if (isNaN(date.getTime())) return dateStr;
      return date.toLocaleDateString('en-GB', {
        day: 'numeric',
        month: 'long',
        year: 'numeric'
      });
    } catch {
      return dateStr;
    }
  };

  const formattedDate = formatDate(article.date);

  return (
    <div className="article-bento stagger-in">
      {/* Box 1: Title & Abstract */}
      <div
        className={`bento-item main-content-box interactable ${copyStatus === 'title' ? 'copied' : ''}`}
        onClick={() => copyToClipboard(article.title, 'title')}
      >
        <header className="article-header-premium">
          <div className="meta-row">
            <span className="type-badge">{article.type.replace('-', ' ')}</span>
            <span className="dot"></span>
            <span className={`date-badge ${copyStatus === 'date' ? 'active' : ''}`}>{formattedDate}</span>
            {article.pdfUrl && (
              <>
                <span className="dot"></span>
                <span className="oa-badge">PDF Available</span>
              </>
            )}
          </div>
          <h2 className="article-title-premium">
            {article.title}
            {copyStatus === 'title' && <span className="copy-notif">Title Copied</span>}
          </h2>
        </header>

        {cleanAbstract && (
          <div className="abstract-container">
            <label className="bento-label">Summary Intelligence</label>
            <p className="abstract-text-premium">{cleanAbstract}</p>
          </div>
        )}
      </div>

      {/* Box 2: Metadata */}
      <div
        className={`bento-item meta-box interactable ${copyStatus === 'journal' ? 'copied' : ''}`}
        onClick={() => copyToClipboard(article.journal, 'journal')}
      >
        <label className="bento-label">Journal / Publisher</label>
        <p className="journal-name-premium">
          {article.journal}
          {copyStatus === 'journal' && <span className="copy-notif">Journal Copied</span>}
        </p>
      </div>

      {/* Box 3: DOI Box */}
      <div
        className={`bento-item doi-box interactable ${copyStatus === 'doi' ? 'copied' : ''}`}
        onClick={() => copyToClipboard(article.doi, 'doi')}
      >
        <label className="bento-label">Identification (DOI)</label>
        <div className="doi-badge-premium">
          <span className="doi-text-premium">{article.doi}</span>
          <div className={`copy-indicator ${copyStatus === 'doi' ? 'active' : ''}`}>
            {copyStatus === 'doi' ? '✓' : <CopyIcon />}
          </div>
        </div>
      </div>

      {/* Box 4: Authors / Contributors */}
      <div className="bento-item authors-box no-grow">
        <label className="bento-label">Contributors (Click name to copy)</label>
        <div className="authors-list-premium">
          {article.authors.length > 0 ? (
            article.authors.slice(0, 12).map((author, i) => {
              const fullName = `${author.family}, ${author.given}`;
              const isCopied = copyStatus === `author-${i}`;
              return (
                <div
                  key={i}
                  className={`author-pill-premium interactable ${isCopied ? 'copied' : ''}`}
                  onClick={() => copyToClipboard(fullName, `author-${i}`)}
                >
                  <span className="name">{author.family}</span>
                  <span className="initials">{author.given?.charAt(0)}</span>
                  {isCopied && <span className="pill-check">✓</span>}
                </div>
              );
            })
          ) : (
            <span className="text-dim">No contributors listed</span>
          )}
          {article.authors.length > 12 && (
            <div className="author-pill-premium more">
              +{article.authors.length - 12} others
            </div>
          )}
        </div>
      </div>

      {/* Box 5: Actions */}
      <div className="bento-item actions-box">
        <div className={`action-buttons-premium ${article.pdfUrl ? 'has-pdf' : ''}`}>
          <a href={article.url} target="_blank" rel="noopener noreferrer" className="btn-read-premium">
            <span>FULL PUBLICATION</span>
            <ExternalIcon />
          </a>
          {article.pdfUrl && (
            <a href={article.pdfUrl} target="_blank" rel="noopener noreferrer" className="btn-pdf-premium">
              <PdfIcon />
              <span>DOWNLOAD PDF</span>
            </a>
          )}
          <button className="btn-icon-premium" onClick={() => copyToClipboard(formattedDate, 'date')}>
            <span className="mini-label">COPY DATE</span>
            {copyStatus === 'date' && <span className="mini-check">✓</span>}
          </button>
        </div>
      </div>

      <style>{`
        .interactable {
          cursor: pointer;
          position: relative;
          transition: var(--transition-fast);
        }

        .interactable:hover {
          background: rgba(255, 255, 255, 0.05);
        }

        .interactable:active {
          transform: scale(0.98);
        }

        .copy-notif {
          position: absolute;
          top: 0.75rem;
          right: 1rem;
          font-size: 0.6rem;
          font-weight: 700;
          color: var(--secondary);
          background: var(--secondary-glow);
          padding: 0.2rem 0.5rem;
          border-radius: var(--radius-sm);
          text-transform: uppercase;
          letter-spacing: 0.05em;
          animation: fadeIn 0.2s ease;
          border: 1px solid var(--secondary-glow);
        }

        .copy-notif.bottom {
          top: auto;
          bottom: 0.75rem;
        }

        .article-bento {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          grid-auto-rows: auto;
          gap: 1px;
          background: var(--border);
          border: 1px solid var(--border);
          border-radius: var(--radius-lg);
          overflow: hidden;
        }

        .bento-item {
          background: var(--bg-card);
          padding: 1.5rem;
          display: flex;
          flex-direction: column;
        }

        .main-content-box {
          grid-column: span 4;
          gap: 1.25rem;
          border-bottom: 1px solid var(--border);
        }

        .meta-box { grid-column: span 2; border-right: 1px solid var(--border); }
        .doi-box { grid-column: span 2; }
        .authors-box { 
          grid-column: span 4;
          border-top: 1px solid var(--border);
          border-bottom: 1px solid var(--border);
        }
        .actions-box { grid-column: span 4; background: var(--bg-surface); }

        .article-header-premium {
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }

        .meta-row {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          font-size: 0.65rem;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.1em;
          color: var(--text-dim);
          font-family: var(--font-mono);
        }

        .type-badge {
          color: var(--secondary);
          background: var(--secondary-glow);
          border: 1px solid var(--secondary-glow);
          padding: 0.15rem 0.5rem;
          border-radius: var(--radius-sm);
        }

        .dot {
          width: 3px;
          height: 3px;
          border-radius: 50%;
          background: var(--text-dim);
          opacity: 0.5;
        }

        .article-title-premium {
          font-family: var(--font-heading);
          font-size: 1.5rem;
          font-weight: 700;
          line-height: 1.3;
          letter-spacing: -0.02em;
          margin: 0;
          color: var(--text-main);
        }

        .bento-label {
          display: block;
          font-size: 0.6rem;
          font-weight: 700;
          color: var(--text-dim);
          text-transform: uppercase;
          letter-spacing: 0.15em;
          margin-bottom: 1rem;
          font-family: var(--font-mono);
        }

        .abstract-text-premium {
          font-size: 0.95rem;
          line-height: 1.6;
          color: var(--text-muted);
          margin: 0;
          display: -webkit-box;
          -webkit-line-clamp: 4;
          -webkit-box-orient: vertical;
          overflow: hidden;
        }

        .journal-name-premium {
          font-size: 0.95rem;
          font-weight: 600;
          color: var(--text-main);
          margin: 0;
        }

        .doi-badge-premium {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 1rem;
        }

        .doi-text-premium {
          font-family: var(--font-mono);
          font-size: 0.75rem;
          color: var(--text-muted);
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .copy-indicator {
          width: 24px;
          height: 24px;
          display: flex;
          align-items: center;
          justify-content: center;
          color: var(--text-dim);
        }

        .copy-indicator.active {
          color: var(--secondary);
        }

        .authors-list-premium {
          display: flex;
          flex-wrap: wrap;
          gap: 0.5rem;
        }

        .author-pill-premium {
          display: flex;
          align-items: center;
          gap: 0.4rem;
          background: rgba(255,255,255,0.03);
          border: 1px solid var(--border);
          padding: 0.3rem 0.6rem;
          border-radius: var(--radius-sm);
          font-size: 0.75rem;
          font-weight: 500;
        }

        .author-pill-premium .initials {
          opacity: 0.5;
          font-family: var(--font-mono);
          font-weight: 400;
        }

        .author-pill-premium.copied {
          border-color: var(--secondary);
          color: var(--secondary);
          background: var(--secondary-glow);
          box-shadow: 0 0 10px var(--secondary-glow);
        }

        .pill-check {
          font-size: 0.7rem;
          margin-left: 0.2rem;
        }

        .action-buttons-premium {
          display: grid;
          grid-template-columns: 1fr auto;
          gap: 1rem;
        }

        .btn-read-premium {
          background: var(--btn-primary-bg);
          color: var(--btn-primary-text);
          text-decoration: none;
          padding: 0.75rem 1.25rem;
          border-radius: var(--radius-md);
          font-weight: 700;
          font-size: 0.75rem;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 0.5rem;
          letter-spacing: 0.05em;
          box-shadow: 0 4px 12px var(--secondary-glow);
        }

        .btn-icon-premium {
          background: transparent;
          border: 1px solid var(--border);
          border-radius: var(--radius-md);
          padding: 0.75rem 1rem;
          display: flex;
          align-items: center;
          gap: 0.5rem;
          color: var(--text-muted);
          transition: var(--transition-fast);
        }

        .btn-icon-premium:hover {
          border-color: var(--border-bright);
          color: var(--text-main);
        }

        .mini-label {
          font-size: 0.65rem;
          font-weight: 700;
          letter-spacing: 0.05em;
        }

        .mini-check {
          color: var(--secondary);
          font-size: 0.75rem;
        }

        .action-buttons-premium {
          display: grid;
          grid-template-columns: 1fr 50px;
          gap: 0.75rem;
        }

        .action-buttons-premium.has-pdf {
          grid-template-columns: 1fr 1fr 50px;
        }

        .oa-badge {
          color: #34d399;
          border: 1px solid rgba(52, 211, 153, 0.25);
          padding: 0.15rem 0.5rem;
          border-radius: var(--radius-sm);
          font-size: 0.6rem;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.05em;
          background: rgba(52, 211, 153, 0.08);
        }

        .btn-pdf-premium {
          background: rgba(52, 211, 153, 0.08);
          border: 1px solid rgba(52, 211, 153, 0.2);
          color: #34d399;
          text-decoration: none;
          padding: 1rem;
          border-radius: 12px;
          font-weight: 700;
          font-size: 0.85rem;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 0.5rem;
          transition: var(--transition-base);
          letter-spacing: 0.03em;
        }

        .btn-pdf-premium:hover {
          background: rgba(52, 211, 153, 0.15);
          border-color: rgba(52, 211, 153, 0.4);
          transform: translateY(-2px);
          box-shadow: 0 4px 20px rgba(52, 211, 153, 0.1);
        }

        .btn-read-premium {
          background: var(--btn-primary-bg);
          color: var(--btn-primary-text);
          text-decoration: none;
          padding: 1rem;
          border-radius: 12px;
          font-weight: 700;
          font-size: 0.95rem;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 0.75rem;
          transition: var(--transition-base);
          box-shadow: 0 4px 15px var(--secondary-glow);
        }

        .btn-read-premium:hover {
          transform: translateY(-2px);
          box-shadow: 0 8px 25px var(--secondary-glow);
          filter: brightness(1.1);
        }

        .btn-icon-premium {
          background: rgba(255,255,255,0.03);
          border: 1px solid var(--border);
          border-radius: 12px;
          display: flex;
          align-items: center;
          justify-content: center;
          color: var(--text-main);
          transition: var(--transition-base);
        }

        .btn-icon-premium:hover {
          background: rgba(255,255,255,0.08);
          border-color: var(--border-bright);
        }

        @media (max-width: 600px) {
          .article-bento {
            grid-template-columns: 1fr;
            gap: 0.75rem;
            background: transparent;
            border: none;
            border-radius: 0;
            overflow: visible;
          }

          .bento-item {
            border: 1px solid var(--border);
            border-radius: var(--radius-lg);
            padding: 1rem 0.95rem;
          }

          .main-content-box, .meta-box, .doi-box, .authors-box, .actions-box {
            grid-column: span 1;
            border: none;
          }

          .article-title-premium {
            font-size: 1.2rem;
            line-height: 1.35;
          }

          .meta-row {
            flex-wrap: wrap;
            row-gap: 0.35rem;
          }

          .bento-label {
            margin-bottom: 0.65rem;
          }

          .doi-badge-premium {
            align-items: flex-start;
          }

          .doi-text-premium {
            white-space: normal;
            overflow-wrap: anywhere;
            line-height: 1.4;
          }

          .action-buttons-premium,
          .action-buttons-premium.has-pdf {
            grid-template-columns: 1fr;
            gap: 0.6rem;
          }

          .btn-read-premium,
          .btn-pdf-premium {
            padding: 0.8rem;
            font-size: 0.8rem;
          }

          .btn-icon-premium {
            min-height: 42px;
          }
        }
      `}</style>
    </div>
  );
}

const CopyIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
);

const ExternalIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>
);

const PdfIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="12" y1="18" x2="12" y2="12"></line><line x1="9" y1="15" x2="15" y2="15"></line></svg>
);

const ShareIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="18" cy="5" r="3"></circle><circle cx="6" cy="12" r="3"></circle><circle cx="18" cy="19" r="3"></circle><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"></line><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"></line></svg>
);
