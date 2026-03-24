import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { onUserProjects, createProject, deleteProject } from '../services/projectService';
import { Plus, Trash2, FolderOpen, Folder, X, Loader2, Search } from 'lucide-react';

export default function Projects() {
  const { currentUser } = useAuth();
  const navigate = useNavigate();
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [creating, setCreating] = useState(false);
  const [formData, setFormData] = useState({ name: '', instructions: '' });
  const [searchTerm, setSearchTerm] = useState('');

  const filteredProjects = projects.filter(project =>
    project.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (project.instructions && project.instructions.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  useEffect(() => {
    if (!currentUser) return;
    const unsubscribe = onUserProjects(currentUser.uid, (data) => {
      setProjects(data);
      setLoading(false);
    });
    return unsubscribe;
  }, [currentUser]);

  async function handleCreate(e) {
    e.preventDefault();
    if (!formData.name.trim()) return;
    setCreating(true);
    try {
      const id = await createProject(currentUser.uid, {
        name: formData.name.trim(),
        instructions: formData.instructions.trim(),
      });
      setShowModal(false);
      setFormData({ name: '', instructions: '' });
      navigate(`/projects/${id}`);
    } catch (err) {
      console.error('Failed to create project:', err);
    } finally {
      setCreating(false);
    }
  }

  async function handleDelete(e, projectId) {
    e.stopPropagation();
    if (!window.confirm('Delete this project and all its sources?')) return;
    try {
      await deleteProject(currentUser.uid, projectId);
    } catch (err) {
      console.error('Failed to delete project:', err);
    }
  }

  function formatDate(timestamp) {
    if (!timestamp) return '';
    const date = timestamp.toDate ? timestamp.toDate() : new Date(timestamp);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  }

  return (
    <div className="projects-page">
      <header className="projects-header">
        <div>
          <h1 className="projects-title">Projects</h1>
          <p className="projects-subtitle">Your research workspaces</p>
        </div>
        <button className="btn-create" onClick={() => setShowModal(true)}>
          <Plus size={18} />
          New Project
        </button>
      </header>

      <div className="projects-actions">
        <div className="search-pill glass">
          <Search size={18} className="search-icon" />
          <input
            type="text"
            placeholder="Search projects..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="search-input"
          />
          {searchTerm && (
            <button className="clear-search" onClick={() => setSearchTerm('')}>
              <X size={14} />
            </button>
          )}
        </div>
      </div>

      {loading ? (
        <div className="projects-loading">
          <Loader2 size={32} className="spin" />
        </div>
      ) : projects.length === 0 ? (
        <div className="projects-empty">
          <FolderOpen size={64} strokeWidth={1} className="empty-icon" />
          <h2>No projects yet</h2>
          <p>Create your first research project to start organizing DOIs and sources.</p>
          <button className="btn-create-lg" onClick={() => setShowModal(true)}>
            <Plus size={20} />
            Create Your First Project
          </button>
        </div>
      ) : (
        <div className="projects-grid">
          {filteredProjects.length === 0 ? (
            <div className="no-results">
              <p>No projects match "{searchTerm}"</p>
            </div>
          ) : filteredProjects.map((project, i) => (
            <div
              key={project.id}
              className="project-card"
              onClick={() => navigate(`/projects/${project.id}`)}
              style={{ animationDelay: `${i * 0.05}s` }}
            >
              <div className="card-top">
                <div className="card-icon">
                  <Folder size={18} />
                </div>
                <button
                  className="card-delete"
                  onClick={(e) => handleDelete(e, project.id)}
                  title="Delete project"
                >
                  <Trash2 size={14} />
                </button>
              </div>
              <h3 className="card-name">{project.name}</h3>
              {project.instructions && (
                <p className="card-desc">{project.instructions}</p>
              )}
              <div className="card-meta">
                <span className="source-count">
                  {project.sources?.length || 0} source{(project.sources?.length || 0) !== 1 ? 's' : ''}
                </span>
                <span className="card-date">{formatDate(project.createdAt)}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Project Modal */}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal-content glass" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>New Project</h2>
              <button className="modal-close" onClick={() => setShowModal(false)}>
                <X size={18} />
              </button>
            </div>
            <form onSubmit={handleCreate}>
              <div className="form-group">
                <label htmlFor="project-name">Project Name</label>
                <input
                  id="project-name"
                  type="text"
                  placeholder="e.g. Final Year Research"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  autoFocus
                  required
                />
              </div>
              <div className="form-group">
                <label htmlFor="project-instructions">Instructions <span className="optional">(optional)</span></label>
                <textarea
                  id="project-instructions"
                  placeholder="Describe the project goals, research focus, or any specific instructions..."
                  value={formData.instructions}
                  onChange={(e) => setFormData({ ...formData, instructions: e.target.value })}
                  rows={4}
                />
              </div>
              <div className="modal-actions">
                <button type="button" className="btn-cancel" onClick={() => setShowModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn-submit" disabled={creating || !formData.name.trim()}>
                  {creating ? <Loader2 size={16} className="spin" /> : <Plus size={16} />}
                  {creating ? 'Creating...' : 'Create Project'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <style>{`
        .projects-page {
          padding: 2rem 3rem;
          width: 100%;
          margin: 0;
          min-height: 100vh;
          max-width: 1400px;
          margin: 0 auto;
        }

        .projects-actions {
          margin-bottom: 2rem;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 1rem;
          width: 100%;
        }

        .search-pill {
          display: flex;
          align-items: center;
          gap: 1rem;
          padding: 0.8rem 1.25rem;
          background: var(--bg-input);
          border: 1px solid var(--border);
          border-radius: var(--radius-full);
          width: 100%;
          max-width: 600px;
          transition: var(--transition-base);
          box-shadow: var(--shadow-sm);
        }

        .search-pill:focus-within {
          border-color: var(--secondary);
          box-shadow: 0 0 0 2px var(--secondary-glow), var(--shadow-md);
        }

        .search-icon {
          color: var(--text-dim);
          width: 20px;
          height: 20px;
        }

        .search-input {
          flex: 1;
          background: transparent;
          border: none;
          color: var(--text-main);
          font-size: 1.05rem;
          outline: none;
        }

        .search-input::placeholder {
          color: var(--text-dim);
        }

        .clear-search {
          color: var(--text-dim);
          padding: 0.25rem;
          display: flex;
          align-items: center;
          justify-content: center;
          border-radius: 50%;
          transition: var(--transition-fast);
        }

        .clear-search:hover {
          background: var(--primary-glow);
          color: var(--text-main);
        }

        .no-results {
          grid-column: 1 / -1;
          padding: 4rem 2rem;
          text-align: center;
          color: var(--text-dim);
          background: var(--bg-surface);
          border: 1px dashed var(--border);
          border-radius: var(--radius-xl);
        }

        .projects-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 2rem;
        }

        @media (max-width: 768px) {
           .projects-page {
              max-width: 100%;
              margin: 0;
              padding: 1.5rem !important;
              display: flex;
              flex-direction: column;
           }
           .projects-header {
              padding-top: 0;
              margin-bottom: 1.5rem;
              order: 2;
              justify-content: flex-end;
           }
           .projects-actions {
              order: 1;
              margin-bottom: 1.5rem;
              justify-content: center;
              padding: 0 0.5rem;
           }
           .search-pill {
              max-width: 100%;
           }
           .projects-loading,
           .projects-empty,
           .projects-grid {
              order: 3;
           }
           .projects-grid {
              grid-template-columns: 1fr;
           }
           .projects-header > div:first-child {
              display: none; /* Hide title/subtitle as AppBar has it */
           }
        }

        .projects-header h1.projects-title {
          font-size: 2rem;
          font-weight: 800;
          letter-spacing: -0.03em;
          margin-bottom: 0.25rem;
          color: var(--text-main);
        }

        .projects-subtitle {
          color: var(--text-dim);
          font-size: 0.9rem;
        }

        .btn-create {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.75rem 1.25rem;
          background: var(--btn-primary-bg);
          color: var(--btn-primary-text);
          font-weight: 600;
          font-size: 0.9rem;
          border-radius: var(--radius-lg);
          transition: var(--transition-fast);
          box-shadow: 0 4px 12px var(--secondary-glow);
        }

        .btn-create:hover {
          opacity: 0.95;
          transform: translateY(-2px);
          box-shadow: 0 6px 16px var(--secondary-glow);
        }

        /* Loading */
        .projects-loading {
          display: flex;
          justify-content: center;
          padding: 6rem 0;
          color: var(--text-dim);
        }

        .spin {
          animation: spin 1s linear infinite;
        }

        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }

        /* Empty State */
        .projects-empty {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          text-align: center;
          padding: 6rem 2rem;
          gap: 1rem;
        }

        .empty-icon {
          color: var(--text-dim);
          opacity: 0.4;
          margin-bottom: 1rem;
        }

        .projects-empty h2 {
          font-size: 1.5rem;
          font-weight: 600;
          color: var(--text-main);
        }

        .projects-empty p {
          color: var(--text-dim);
          max-width: 400px;
          line-height: 1.5;
        }

        .btn-create-lg {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.85rem 1.75rem;
          background: var(--btn-primary-bg);
          color: var(--btn-primary-text);
          font-weight: 600;
          font-size: 1rem;
          border-radius: var(--radius-lg);
          margin-top: 1rem;
          transition: var(--transition-fast);
          box-shadow: 0 4px 15px var(--secondary-glow);
        }

        .btn-create-lg:hover {
          opacity: 0.95;
          transform: translateY(-2px);
          box-shadow: 0 8px 20px var(--secondary-glow);
        }

        /* Project Grid */
        .projects-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
          gap: 1.25rem;
        }

        .project-card {
          cursor: pointer;
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
          padding: 1.5rem;
          animation: slideUp 0.4s ease forwards;
          opacity: 0;
          background: var(--bg-surface);
          border: 1px solid var(--border);
          border-radius: var(--radius-xl);
          transition: var(--transition-fast);
        }

        .project-card:hover {
          border-color: var(--border-bright);
        }

        .card-top {
          display: flex;
          align-items: center;
          justify-content: space-between;
        }

        .card-icon {
          width: 36px;
          height: 36px;
          border-radius: var(--radius-md);
          background: var(--secondary-glow);
          display: flex;
          align-items: center;
          justify-content: center;
          color: var(--secondary);
        }

        .card-delete {
          width: 28px;
          height: 28px;
          border-radius: var(--radius-sm);
          display: flex;
          align-items: center;
          justify-content: center;
          background: transparent;
          color: var(--text-dim);
          opacity: 0;
          transition: var(--transition-fast);
        }

        .project-card:hover .card-delete {
          opacity: 1;
        }

        .card-delete:hover {
          color: #fb7185;
          background: rgba(244, 63, 94, 0.1);
        }

        .card-name {
          font-size: 1.1rem;
          font-weight: 600;
          line-height: 1.3;
        }

        .card-desc {
          font-size: 0.85rem;
          color: var(--text-muted);
          line-height: 1.5;
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
          overflow: hidden;
        }

        .card-meta {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-top: auto;
          padding-top: 0.75rem;
          border-top: 1px solid var(--border);
          font-size: 0.75rem;
          color: var(--text-dim);
          font-family: var(--font-mono);
        }

        .source-count {
          background: var(--primary-glow);
          padding: 0.2rem 0.5rem;
          border-radius: var(--radius-sm);
        }

        /* Modal */
        .modal-overlay {
          position: fixed;
          inset: 0;
          background: rgba(0, 0, 0, 0.7);
          backdrop-filter: blur(4px);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 2000;
          animation: fadeIn 0.2s ease;
        }

        .modal-content {
          width: 100%;
          max-width: 520px;
          padding: 2rem;
          border-radius: var(--radius-xl);
          background: var(--bg-surface);
          border: 1px solid var(--border);
          animation: slideUp 0.3s cubic-bezier(0.16, 1, 0.3, 1);
        }

        .modal-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 1.75rem;
        }

        .modal-header h2 {
          font-size: 1.35rem;
          font-weight: 700;
        }

        .modal-close {
          width: 32px;
          height: 32px;
          border-radius: var(--radius-md);
          display: flex;
          align-items: center;
          justify-content: center;
          background: transparent;
          color: var(--text-dim);
          transition: var(--transition-fast);
        }

        .modal-close:hover {
          background: var(--primary-glow);
          color: var(--text-main);
        }

        .form-group {
          margin-bottom: 1.25rem;
        }

        .form-group label {
          display: block;
          font-size: 0.85rem;
          font-weight: 500;
          color: var(--text-muted);
          margin-bottom: 0.5rem;
        }

        .optional {
          color: var(--text-dim);
          font-weight: 400;
        }

        .form-group input,
        .form-group textarea {
          width: 100%;
          padding: 0.85rem 1rem;
          background: var(--bg-input);
          border: 1px solid var(--border);
          border-radius: var(--radius-md);
          color: var(--text-main);
          font-size: 0.95rem;
          font-family: var(--font-body);
          outline: none;
          transition: var(--transition-fast);
        }

        .form-group input:focus,
        .form-group textarea:focus {
          border-color: var(--border-bright);
          box-shadow: 0 0 0 3px var(--primary-glow);
        }

        .form-group textarea {
          resize: vertical;
          min-height: 100px;
        }

        .modal-actions {
          display: flex;
          justify-content: flex-end;
          gap: 0.75rem;
          margin-top: 1.5rem;
        }

        .btn-cancel {
          padding: 0.7rem 1.25rem;
          background: transparent;
          color: var(--text-muted);
          border: 1px solid var(--border);
          border-radius: var(--radius-md);
          font-size: 0.9rem;
          transition: var(--transition-fast);
        }

        .btn-cancel:hover {
          background: var(--primary-glow);
          color: var(--text-main);
        }

        .btn-submit {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.7rem 1.25rem;
          background: var(--btn-primary-bg);
          color: var(--btn-primary-text);
          font-weight: 600;
          font-size: 0.9rem;
          border-radius: var(--radius-md);
          transition: var(--transition-fast);
        }

        .btn-submit:hover:not(:disabled) {
          transform: translateY(-1px);
          box-shadow: 0 4px 12px var(--secondary-glow);
        }

        .btn-submit:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

      `}</style>
    </div>
  );
}
