import React from 'react';

export default function SidePanel({ isOpen, onClose, children }) {
    return (
        <div className={`side-panel-container ${isOpen ? 'active' : ''}`}>
            <div className="side-panel-content glass">
                <header className="panel-header">
                    <div className="panel-status">
                        <span className="status-dot"></span>
                        Result Found
                    </div>
                    <button className="panel-close" onClick={onClose}>
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <line x1="18" y1="6" x2="6" y2="18"></line>
                            <line x1="6" y1="6" x2="18" y2="18"></line>
                        </svg>
                    </button>
                </header>

                <div className="panel-body">
                    {children}
                </div>
            </div>

            <style>{`
        .side-panel-container {
          position: fixed;
          top: 0;
          right: 0;
          height: 100vh;
          width: 500px;
          z-index: 1001;
          pointer-events: none;
          display: flex;
          justify-content: flex-end;
          padding: 1rem;
        }

        .side-panel-container.active {
          pointer-events: all;
        }

        .side-panel-content {
          width: 100%;
          height: 100%;
          display: flex;
          flex-direction: column;
          border-radius: var(--radius-xl);
          transform: translateX(120%);
          transition: var(--transition-slow);
          overflow: hidden;
          box-shadow: -20px 0 40px rgba(0, 0, 0, 0.4);
        }

        .side-panel-container.active .side-panel-content {
          transform: translateX(0);
        }

        .panel-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 1.25rem 1.5rem;
          border-bottom: 1px solid var(--border);
        }

        .panel-status {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          font-size: 0.85rem;
          font-weight: 600;
          color: var(--text-main);
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }

        .status-dot {
          width: 8px;
          height: 8px;
          background: #10b981;
          border-radius: 50%;
          box-shadow: 0 0 10px #10b981;
        }

        .panel-close {
          background: transparent;
          border: none;
          color: var(--text-dim);
          cursor: pointer;
          padding: 0.25rem;
          border-radius: 6px;
          transition: var(--transition-fast);
        }

        .panel-close:hover {
          background: rgba(255, 255, 255, 0.05);
          color: white;
        }

        .panel-body {
          flex: 1;
          overflow-y: auto;
          padding: 1.5rem;
        }

        @media (max-width: 768px) {
          .side-panel-container {
            width: 100%;
            padding: 0;
          }
          .side-panel-content {
            border-radius: 0;
          }
        }
      `}</style>
        </div>
    );
}
