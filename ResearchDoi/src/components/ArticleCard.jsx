import React, { useState, useEffect } from 'react';
import { onUserProjects, addSourceViaApi, createProject } from '../services/projectService';
import { ExternalLink, FolderPlus, Copy, Check, Calendar, FileText, Plus, X, Search } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion'; // eslint-disable-line no-unused-vars

const currentUser = { uid: "localUser" };

export default function ArticleCard({ article }) {
  const [copyStatus, setCopyStatus] = useState(null);
  const [projects, setProjects] = useState([]);
  const [showProjectModal, setShowProjectModal] = useState(false);
  const [addingToProject, setAddingToProject] = useState(false);
  const [newProjectName, setNewProjectName] = useState('');
  const [projectSearch, setProjectSearch] = useState('');

  useEffect(() => {
    const unsub = onUserProjects(currentUser.uid, setProjects);
    return () => unsub();
  }, []);

  if (!article) return null;

  const cleanAbstract = article.abstract
    ? article.abstract.replace(/<[^>]+>/g, '')
    : null;

  const copyToClipboard = (text, field) => {
    navigator.clipboard.writeText(text);
    setCopyStatus(field);
    setTimeout(() => setCopyStatus(null), 2000);
  };

  const handleAddToProject = async (projectId) => {
    try {
      setAddingToProject(true);
      await addSourceViaApi(currentUser.uid, projectId, {
        type: 'doi',
        doi: article.doi,
        title: article.title,
        authors: article.authors.map(a => typeof a === 'string' ? a : `${a.given} ${a.family}`.trim()),
        journal: article.journal,
        date: article.date,
        url: article.url,
        pdf_url: article.pdfUrl,
        document_url: article.pdfUrl
      });
      setCopyStatus('added');
      setShowProjectModal(false);
      setTimeout(() => setCopyStatus(null), 3000);
    } catch (err) {
      console.error('Failed to add source:', err);
    } finally {
      setAddingToProject(false);
    }
  };

  const handleCreateAndAdd = async () => {
    if (!newProjectName.trim()) return;
    try {
      setAddingToProject(true);
      const projectId = await createProject(currentUser.uid, { name: newProjectName.trim() });
      await handleAddToProject(projectId);
      setNewProjectName('');
    } catch (err) {
      console.error('Failed to create and add:', err);
    } finally {
      setAddingToProject(false);
    }
  };

  const filteredProjects = projects.filter(p => 
    p.name.toLowerCase().includes(projectSearch.toLowerCase())
  );

  const formatDate = (dateStr) => {
    try {
      const date = new Date(dateStr);
      if (isNaN(date.getTime())) return dateStr;
      return date.toLocaleDateString('en-GB', {
        day: 'numeric',
        month: 'short',
        year: 'numeric'
      });
    } catch {
      return dateStr;
    }
  };

  const formattedDate = formatDate(article.date);

  return (
    <div className="article-card-container">
      <div className="article-main-card">
        <header className="article-header">
          <div className="article-meta">
            <span className="type-badge">{article.type.replace('-', ' ')}</span>
            <span className="date-badge">
              <Calendar size={12} />
              {formattedDate}
            </span>
          </div>
          <h2 className="article-title">{article.title}</h2>
          
          <div className="article-authors">
            {article.authors?.map((author, i) => (
              <span key={i} className="author-name">
                {typeof author === 'string' ? author : `${author.given} ${author.family}`}
                {i < article.authors.length - 1 ? ", " : ""}
              </span>
            ))}
          </div>
        </header>

        {cleanAbstract && (
          <div className="article-abstract">
            <p>{cleanAbstract}</p>
          </div>
        )}

        <div className="article-footer">
          <div className="article-metrics">
            <div className="metric-pill" onClick={() => copyToClipboard(article.doi, 'doi')}>
              <span className="metric-label">DOI</span>
              <span className="metric-value">{article.doi}</span>
              {copyStatus === 'doi' ? <Check size={12} /> : <Copy size={12} />}
            </div>
            {article.journal && (
              <div className="metric-pill">
                <span className="metric-label">VENUE</span>
                <span className="metric-value">{article.journal}</span>
              </div>
            )}
            {article.url?.includes('arxiv.org') && (
              <div className="metric-pill accent">
                <span className="metric-label">SOURCE</span>
                <span className="metric-value">ArXiv</span>
              </div>
            )}
          </div>

          <div className="article-actions">
            <a href={article.url} target="_blank" rel="noopener noreferrer" className="action-btn primary">
              <ExternalLink size={16} />
              <span>Full Text</span>
            </a>

            {article.pdfUrl && (
              <a href={article.pdfUrl} target="_blank" rel="noopener noreferrer" className="action-btn secondary">
                <FileText size={16} />
                <span>View PDF</span>
              </a>
            )}
            
            <div className="project-selector-wrapper">
              <button 
                className={`action-btn secondary ${copyStatus === 'added' ? 'success' : ''}`}
                onClick={() => setShowProjectModal(true)}
                disabled={addingToProject}
              >
                <FolderPlus size={16} />
                <span>{copyStatus === 'added' ? 'Indexed' : 'Add to Project'}</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      <AnimatePresence>
        {showProjectModal && (
          <div className="modal-overlay">
            <motion.div 
              className="modal-backdrop"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowProjectModal(false)}
            />
            <motion.div 
              className="project-modal"
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
            >
              <div className="modal-header">
                <div>
                  <h3>Select Workspace</h3>
                  <p>Choose a project to house this research</p>
                </div>
                <button className="close-modal" onClick={() => setShowProjectModal(false)}>
                  <X size={20} />
                </button>
              </div>

              <div className="modal-body">
                <div className="create-project-section">
                  <div className="input-with-action">
                    <input 
                      type="text" 
                      placeholder="Create a new workspace..."
                      value={newProjectName}
                      onChange={(e) => setNewProjectName(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && handleCreateAndAdd()}
                    />
                    <button 
                      onClick={handleCreateAndAdd}
                      disabled={!newProjectName.trim() || addingToProject}
                    >
                      <Plus size={16} />
                      CREATE
                    </button>
                  </div>
                </div>

                <div className="project-search-bar">
                  <Search size={14} />
                  <input 
                    type="text" 
                    placeholder="Search existing projects..."
                    value={projectSearch}
                    onChange={(e) => setProjectSearch(e.target.value)}
                  />
                </div>

                <div className="project-grid">
                  {filteredProjects.map(p => (
                    <button 
                      key={p.id} 
                      className="project-card-option"
                      onClick={() => handleAddToProject(p.id)}
                      disabled={addingToProject}
                    >
                      <div className="proj-info">
                        <span className="proj-name">{p.name}</span>
                        <span className="proj-sources">{p.sources?.length || 0} sources</span>
                      </div>
                      <div className="proj-arrow">
                        <Plus size={14} />
                      </div>
                    </button>
                  ))}
                  {filteredProjects.length === 0 && (
                    <div className="empty-projects">
                      {projectSearch ? 'No matching projects' : 'No projects found'}
                    </div>
                  )}
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      <style>{`
        .article-card-container {
          width: 100%;
          max-width: 800px;
          margin: 0 auto;
        }

        .article-main-card {
          background: var(--bg-card);
          border: 1px solid var(--glass-border);
          backdrop-filter: var(--glass-blur);
          border-radius: var(--radius-lg);
          padding: 2.5rem;
          display: flex;
          flex-direction: column;
          gap: 1.75rem;
          box-shadow: var(--shadow-inner), var(--shadow-md);
        }
 
        .article-header {
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }
 
        .article-meta {
          display: flex;
          align-items: center;
          gap: 1rem;
        }
 
        .type-badge {
          font-family: var(--font-mono);
          font-size: 0.65rem;
          font-weight: 700;
          text-transform: uppercase;
          color: var(--secondary);
          background: var(--secondary-glow);
          padding: 0.3rem 0.7rem;
          border-radius: 6px;
        }
 
        .date-badge {
          display: flex;
          align-items: center;
          gap: 0.4rem;
          font-size: 0.8rem;
          color: var(--text-dim);
        }
 
        .article-title {
          font-size: 1.8rem;
          font-weight: 700;
          line-height: 1.25;
          color: var(--text-main);
          letter-spacing: -0.04em;
        }
 
        .article-abstract {
          font-size: 1rem;
          line-height: 1.7;
          color: var(--text-muted);
          background: var(--bg-surface);
          padding: 1.5rem;
          border-radius: var(--radius-lg);
          border: 1px solid var(--glass-border);
        }
 
        .article-authors {
          display: flex;
          flex-wrap: wrap;
          gap: 0.4rem;
          margin-top: 0.5rem;
        }
 
        .author-name {
          font-size: 0.9rem;
          font-weight: 500;
          color: var(--secondary);
          opacity: 0.9;
        }
 
        .article-footer {
          display: flex;
          flex-direction: column;
          gap: 1.5rem;
          padding-top: 1.5rem;
          border-top: 1px solid var(--glass-border);
        }
 
        .article-metrics {
          display: flex;
          flex-wrap: wrap;
          gap: 1rem;
        }
 
        .metric-pill {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          background: var(--bg-input);
          border: 1px solid var(--glass-border);
          padding: 0.5rem 1rem;
          border-radius: var(--radius-md);
          cursor: pointer;
          transition: border-color var(--transition-base), background var(--transition-base);
        }
 
        .metric-pill:hover {
          border-color: var(--secondary);
          background: var(--secondary-glow);
        }
 
        .metric-label {
          font-family: var(--font-mono);
          font-size: 0.65rem;
          font-weight: 700;
          color: var(--text-dim);
        }
 
        .metric-value {
          font-size: 0.85rem;
          font-weight: 600;
          color: var(--text-main);
        }
 
        .article-actions {
          display: flex;
          gap: 1rem;
        }
 
        .action-btn {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 0.6rem;
          padding: 0.85rem 1.5rem;
          border-radius: var(--radius-md);
          font-size: 0.9rem;
          font-weight: 500;
          transition: transform var(--transition-base), filter var(--transition-base), background var(--transition-base), border-color var(--transition-base);
          cursor: pointer;
          text-decoration: none;
        }
 
        .action-btn:active {
          transform: scale(0.97);
        }
 
        .action-btn.primary {
          background: var(--secondary);
          color: #fff;
        }
 
        .action-btn.secondary {
          background: rgba(255, 255, 255, 0.05);
          border: 1px solid var(--glass-border);
          color: var(--text-main);
        }
 
        .action-btn.secondary.success {
          background: var(--accent-glow);
          color: var(--accent);
          border-color: var(--accent);
        }
 
        .action-btn:hover {
          transform: translateY(-2px);
          filter: brightness(1.1);
        }
 
        .project-selector-wrapper {
          position: relative;
        }
 
        .modal-overlay {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 1000;
          padding: 2rem;
        }
 
        .modal-backdrop {
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0, 0, 0, 0.85);
          backdrop-filter: blur(16px);
        }
 
        .project-modal {
          position: relative;
          width: 100%;
          max-width: 480px;
          background: var(--bg-surface);
          border: 1px solid var(--glass-border);
          backdrop-filter: var(--glass-blur);
          border-radius: var(--radius-lg);
          overflow: hidden;
          box-shadow: var(--shadow-inner), var(--shadow-lg);
          animation: modal-enter 0.4s var(--ease-out);
        }
 
        @keyframes modal-enter {
          from { opacity: 0; transform: scale(0.95) translateY(10px); }
          to { opacity: 1; transform: scale(1) translateY(0); }
        }
 
        .modal-header {
          padding: 1.75rem 2rem;
          border-bottom: 1px solid var(--glass-border);
          display: flex;
          justify-content: space-between;
          align-items: center;
          background: linear-gradient(180deg, rgba(255,255,255,0.01) 0%, transparent 100%);
        }
 
        .modal-header h3 {
          font-size: 1.25rem;
          font-weight: 700;
          color: var(--text-main);
          margin-bottom: 0.25rem;
        }
 
        .modal-header p {
          font-size: 0.8rem;
          color: var(--text-dim);
        }
 
        .close-modal {
          background: transparent;
          border: none;
          color: var(--text-dim);
          cursor: pointer;
          padding: 0.5rem;
          border-radius: 50%;
          transition: background var(--transition-base), color var(--transition-base);
        }
 
        .close-modal:hover {
          background: rgba(255,255,255,0.05);
          color: #fff;
        }
 
        .modal-body {
          padding: 1.5rem 2rem 2.5rem;
          display: flex;
          flex-direction: column;
          gap: 1.5rem;
        }
 
        .create-project-section {
          width: 100%;
        }
 
        .input-with-action {
          display: flex;
          gap: 0.75rem;
          background: var(--bg-card);
          border: 1px solid var(--glass-border);
          padding: 0.5rem;
          border-radius: var(--radius-md);
          transition: border-color var(--transition-base), background var(--transition-base), box-shadow var(--transition-base);
        }
 
        .input-with-action:focus-within {
          border-color: var(--secondary);
          background: var(--bg-surface);
          box-shadow: 0 0 24px var(--secondary-glow);
        }
 
        .input-with-action input {
          flex: 1;
          background: transparent;
          border: none;
          color: #fff;
          font-size: 0.9rem;
          padding: 0 0.75rem;
          outline: none;
        }
 
        .input-with-action button {
          background: var(--secondary);
          color: #fff;
          border: none;
          padding: 0.6rem 1rem;
          border-radius: 10px;
          font-family: var(--font-mono);
          font-size: 0.65rem;
          font-weight: 800;
          letter-spacing: 0.05em;
          display: flex;
          align-items: center;
          gap: 0.5rem;
          cursor: pointer;
          transition: background var(--transition-base), color var(--transition-base), opacity var(--transition-base);
        }
 
        .input-with-action button:active {
          transform: scale(0.97);
        }
 
        .input-with-action button:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }
 
        .project-search-bar {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          padding: 0 0.75rem;
          height: 40px;
          border-bottom: 1px solid var(--glass-border);
          color: var(--text-dim);
        }
 
        .project-search-bar input {
          flex: 1;
          height: 100%;
          background: transparent;
          border: none;
          color: var(--text-muted);
          font-size: 0.85rem;
          outline: none;
        }
 
        .project-grid {
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
          max-height: 280px;
          overflow-y: auto;
          padding-right: 0.5rem;
        }
 
        .project-grid::-webkit-scrollbar {
          width: 4px;
        }
 
        .project-grid::-webkit-scrollbar-thumb {
          background: rgba(255,255,255,0.1);
          border-radius: 10px;
        }
 
        .project-card-option {
          display: flex;
          align-items: center;
          justify-content: space-between;
          background: var(--bg-card);
          border: 1px solid var(--glass-border);
          padding: 1.25rem 1.5rem;
          border-radius: var(--radius-md);
          cursor: pointer;
          text-align: left;
          transition: transform var(--transition-base), border-color var(--transition-base), background var(--transition-base);
        }
 
        .project-card-option:hover {
          background: var(--bg-surface);
          border-color: var(--secondary);
          transform: translateX(5px);
        }

        .proj-info {
          display: flex;
          flex-direction: column;
          gap: 0.25rem;
        }

        .proj-name {
          font-size: 0.95rem;
          font-weight: 600;
          color: var(--text-main);
        }

        .proj-sources {
          font-family: var(--font-mono);
          font-size: 0.65rem;
          color: var(--text-dim);
          text-transform: uppercase;
        }

        .proj-arrow {
          color: var(--text-dim);
          opacity: 0;
          transition: opacity 200ms var(--ease-out), transform 200ms var(--ease-out), color 200ms var(--ease-out);
          transform: rotate(-90deg);
        }

        .project-card-option:hover .proj-arrow {
          opacity: 1;
          color: var(--secondary);
          transform: rotate(0deg);
        }

        .empty-projects {
          padding: 2rem;
          text-align: center;
          font-size: 0.85rem;
          color: var(--text-dim);
          font-style: italic;
        }

        @media (max-width: 640px) {
          .article-main-card {
            padding: 1.5rem;
          }
          .article-title {
            font-size: 1.3rem;
          }
          .article-actions {
            flex-direction: column;
          }
          .project-selector-wrapper, .action-btn {
            width: 100%;
          }
        }
      `}</style>
    </div>
  );
}
