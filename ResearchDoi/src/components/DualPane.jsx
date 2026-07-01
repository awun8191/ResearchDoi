import React from 'react';

export default function DualPane({ thesisState }) {
    // Determine the sections from the state
    const sections = Object.entries(thesisState || {});

    return (
        <div className="dual-pane-editor glass">
            <div className="dual-pane-header">
                <h3>LIVE THESIS SYNTHESIS</h3>
                <span className="live-indicator">● LIVE</span>
            </div>
            
            <div className="dual-pane-content">
                {sections.length === 0 ? (
                    <div className="empty-state">
                        <p>No thesis content generated yet.</p>
                        <p className="empty-hint">Start collaborating with the AI in the chat pane to generate sections.</p>
                    </div>
                ) : (
                    sections.map(([sectionId, content]) => (
                        <div key={sectionId} className="thesis-section">
                            <h4 className="section-title">{formatSectionId(sectionId)}</h4>
                            <div className="section-content">
                                {renderContent(content)}
                            </div>
                        </div>
                    ))
                )}
            </div>

            <style>{`
                .dual-pane-editor {
                    flex: 1;
                    display: flex;
                    flex-direction: column;
                    background: rgba(0, 0, 0, 0.4);
                    border-left: 1px solid var(--border);
                    min-width: 400px;
                    max-width: 50%;
                }

                .dual-pane-header {
                    padding: 1rem 1.5rem;
                    border-bottom: 1px solid var(--border);
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                }

                .dual-pane-header h3 {
                    font-family: var(--font-mono);
                    font-size: 0.85rem;
                    font-weight: 800;
                    letter-spacing: 0.1em;
                    color: var(--secondary);
                }

                .live-indicator {
                    font-family: var(--font-mono);
                    font-size: 0.7rem;
                    color: #ff3366;
                    animation: blink 2s infinite;
                }

                @keyframes blink {
                    0% { opacity: 1; }
                    50% { opacity: 0.3; }
                    100% { opacity: 1; }
                }

                .dual-pane-content {
                    flex: 1;
                    padding: 2rem;
                    overflow-y: auto;
                    display: flex;
                    flex-direction: column;
                    gap: 2rem;
                }

                .empty-state {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    height: 100%;
                    color: var(--text-dim);
                    text-align: center;
                }

                .empty-hint {
                    font-size: 0.85rem;
                    margin-top: 0.5rem;
                    color: var(--text-muted);
                }

                .thesis-section {
                    display: flex;
                    flex-direction: column;
                    gap: 1rem;
                }

                .section-title {
                    font-family: var(--font-mono);
                    font-size: 0.9rem;
                    font-weight: 700;
                    color: var(--text-main);
                    text-transform: uppercase;
                    border-bottom: 1px solid var(--glass-border);
                    padding-bottom: 0.5rem;
                }

                .section-content {
                    font-size: 1rem;
                    line-height: 1.6;
                    color: var(--text-main);
                }

                .section-content p {
                    margin-bottom: 1rem;
                }

                .citation-badge {
                    display: inline-block;
                    background: rgba(255, 51, 102, 0.15);
                    color: #ff3366;
                    border: 1px solid rgba(255, 51, 102, 0.3);
                    border-radius: 4px;
                    padding: 0 4px;
                    margin: 0 2px;
                    font-size: 0.8em;
                    font-family: var(--font-mono);
                    cursor: help;
                    transition: all 0.2s ease;
                }

                .citation-badge:hover {
                    background: rgba(255, 51, 102, 0.3);
                }
            `}</style>
        </div>
    );
}

function formatSectionId(id) {
    return id.replace(/_/g, ' ');
}

function renderContent(content) {
    if (!content) return null;
    const lines = content.split('\n');
    return lines.map((line, i) => {
        const parts = line.split(/(\[Cite:\s*.*?\])/g);
        return (
            <p key={i}>
                {parts.map((part, j) => {
                    if (part.startsWith('[Cite:')) {
                        const citeText = part.slice(6, -1).trim();
                        // Truncate citeText if too long for the badge
                        const displayCite = citeText.length > 30 ? citeText.substring(0, 30) + '...' : citeText;
                        return (
                            <span key={j} className="citation-badge" title={citeText}>
                                [{displayCite}]
                            </span>
                        );
                    }
                    return part;
                })}
            </p>
        );
    });
}
