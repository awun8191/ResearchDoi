import React from 'react';

export default function ArticleSkeleton() {
  return (
    <div className="skeleton-compact animate-pulse">
      <div className="skeleton-header-mini">
        <div className="skeleton-line title-lh"></div>
        <div className="skeleton-meta-mini">
          <div className="skeleton-block small"></div>
          <div className="skeleton-dot"></div>
          <div className="skeleton-block small"></div>
        </div>
      </div>

      <div className="skeleton-section">
        <div className="skeleton-label-mini"></div>
        <div className="skeleton-line val-lh"></div>
      </div>

      <div className="skeleton-section">
        <div className="skeleton-label-mini"></div>
        <div className="skeleton-block-doi"></div>
      </div>

      <div className="skeleton-section">
        <div className="skeleton-label-mini"></div>
        <div className="skeleton-cloud-mini">
          <div className="skeleton-tag-mini"></div>
          <div className="skeleton-tag-mini"></div>
          <div className="skeleton-tag-mini"></div>
        </div>
      </div>

      <div className="skeleton-section">
        <div className="skeleton-label-mini"></div>
        <div className="skeleton-line-multi"></div>
        <div className="skeleton-line-multi"></div>
        <div className="skeleton-line-multi"></div>
      </div>

      <style>{`
        .skeleton-compact {
          display: flex;
          flex-direction: column;
          gap: 1.75rem;
        }

        .skeleton-line {
          background: var(--bg-input);
          border-radius: 4px;
        }

        .title-lh { height: 1.5rem; width: 90%; margin-bottom: 0.75rem; }
        .val-lh { height: 1.25rem; width: 70%; }

        .skeleton-meta-mini {
          display: flex;
          align-items: center;
          gap: 0.5rem;
        }

        .skeleton-block { background: var(--bg-input); height: 12px; border-radius: 4px; }
        .skeleton-block.small { width: 60px; }

        .skeleton-dot { width: 4px; height: 4px; border-radius: 50%; background: var(--border); }

        .skeleton-label-mini {
          width: 80px;
          height: 10px;
          background: var(--bg-input);
          margin-bottom: 0.5rem;
          border-radius: 2px;
        }

        .skeleton-block-doi {
          width: 100%;
          height: 32px;
          background: var(--bg-input);
          border-radius: 8px;
        }

        .skeleton-cloud-mini {
          display: flex;
          gap: 0.5rem;
        }

        .skeleton-tag-mini {
          width: 70px;
          height: 24px;
          background: var(--bg-input);
          border-radius: 6px;
        }

        .skeleton-line-multi {
          height: 12px;
          background: var(--bg-input);
          border-radius: 4px;
          margin-bottom: 0.5rem;
          width: 100%;
        }

        .skeleton-line-multi:last-child { width: 60%; }

        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }

        .animate-pulse {
          animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
        }
      `}</style>
    </div>
  );
}
