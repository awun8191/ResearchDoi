import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { onUserProjects, createProject, deleteProject } from '../services/projectService';
import { Plus, Trash2, FolderOpen, Folder, X, Loader2, Search } from 'lucide-react';
import { CircularProgress } from '@mui/material';

const currentUser = { uid: "localUser" };

export default function Projects() {
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
  }, []);

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
    return date.toLocaleDateString('en-GB', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  }

  return (
    <div className="projects-lab stagger-in">
      <header className="projects-header">
        <div className="header-info">
          <h1>Projects</h1>
          <p>Manage your research workspaces.</p>
        </div>
        <button className="btn-new-project" onClick={() => setShowModal(true)}>
          <Plus size={18} />
          <span>New Project</span>
        </button>
      </header>

      <div className="lab-search-zone">
        <div className="lab-search-pill glass">
          <Search size={18} className="search-icon" />
          <input
            type="text"
            placeholder="FILTER WORKSPACES..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="lab-search-input"
          />
          {searchTerm && (
            <button className="clear-lab-search" onClick={() => setSearchTerm('')}>
              <X size={14} />
            </button>
          )}
        </div>
      </div>

      {loading ? (
        <div className="lab-loading">
          <CircularProgress size={32} sx={{ color: 'var(--secondary)' }} />
          <p>SYNCHRONIZING REGISTRY...</p>
        </div>
      ) : projects.length === 0 && !loading ? (
        <div className="lab-empty glass stagger-in">
          <div className="lab-empty-icon">
            <Folder size={64} strokeWidth={1} />
          </div>
          <h3>REGISTRY EMPTY</h3>
          <p>No analytical workspaces identified. Initialize a project to begin indexing research data.</p>
          <button className="btn-init-large" onClick={() => setShowModal(true)}>
            <Plus size={20} />
            INITIALIZE WORKSPACE
          </button>
        </div>
      ) : (
        <div className="lab-grid stagger-in">
          {filteredProjects.length === 0 ? (
            <div className="lab-no-results glass">
              <p>NO WORKSPACES MATCHING SPECIFIED CRITERIA</p>
            </div>
          ) : filteredProjects.map((project, i) => (
            <div
              key={project.id}
              className="lab-project-card interactable"
              onClick={() => navigate(`/projects/${project.id}`)}
              style={{ animationDelay: `${i * 0.05}s` }}
            >
              <div className="card-top">
                <div className="lab-icon-box">
                  <FolderOpen size={20} />
                </div>
                <button
                  className="btn-terminate"
                  onClick={(e) => handleDelete(e, project.id)}
                  title="Terminate workspace"
                >
                  <Trash2 size={16} />
                </button>
              </div>
              <div className="card-main">
                <h3 className="project-title">{project.name}</h3>
                <p className="project-instructions">
                  {project.instructions || "General research and DOI analysis workspace."}
                </p>
              </div>
              <div className="card-meta-row">
                <div className="meta-item">
                  <span className="meta-val">{project.sources?.length || 0}</span>
                  <span className="meta-lbl">DATA SOURCES</span>
                </div>
                <div className="meta-date">{formatDate(project.createdAt)}</div>
              </div>
              <div className="lab-accent-glow"></div>
            </div>
          ))}
        </div>
      )}

      {/* Initialize Workspace Modal */}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal-content-lab glass" onClick={(e) => e.stopPropagation()}>
            <div className="modal-head">
              <div className="modal-id-group">
                <div className="modal-pulse"></div>
                <h2>WORKSPACE CONFIGURATION</h2>
              </div>
              <button className="modal-close" onClick={() => setShowModal(false)}>
                <X size={20} />
              </button>
            </div>
            <form onSubmit={handleCreate} className="lab-form">
              <div className="lab-group">
                <label>IDENTIFIER</label>
                <input
                  type="text"
                  placeholder="E.G. QUANTUM_PHYSICS_2026"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  autoFocus
                  required
                />
              </div>
              <div className="lab-group">
                <label>STRATEGIC INSTRUCTIONS</label>
                <textarea
                  placeholder="DEFINE ANALYTICAL FOCUS OR GROUNDING PARAMETERS..."
                  value={formData.instructions}
                  onChange={(e) => setFormData({ ...formData, instructions: e.target.value })}
                  rows={5}
                />
              </div>
              <div className="modal-ops">
                <button type="button" className="btn-lab-cancel" onClick={() => setShowModal(false)}>
                  ABORT
                </button>
                <button type="submit" className="btn-lab-submit" disabled={creating || !formData.name.trim()}>
                  {creating ? <CircularProgress size={16} color="inherit" /> : <Plus size={18} />}
                  <span>{creating ? 'INITIALIZING...' : 'INITIALIZE'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <style>{`
        .projects-lab {
    padding: 2.5rem;
    width: 100%;
    max-width: 1000px;
    margin: 0 auto;
    display: flex;
    flex-direction: column;
    gap: 2rem;
    min-height: 100vh;
  }

  .projects-header {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    padding-bottom: 2rem;
    border-bottom: 1px solid var(--border);
  }

  .header-info h1 {
    font-size: 2rem;
    font-weight: 700;
    margin-bottom: 0.5rem;
    color: var(--text-main);
  }

  .header-info p {
    color: var(--text-muted);
    font-size: 0.9rem;
  }

  .btn-new-project {
    background: var(--secondary);
    color: #fff;
    padding: 0.75rem 1.25rem;
    border-radius: 10px;
    font-size: 0.85rem;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    transition: transform 0.2s ease, filter 0.2s ease;
  }

  .btn-new-project:hover {
    filter: brightness(1.1);
    transform: translateY(-1px);
  }

        .lab-search-zone {
          display: flex;
          justify-content: center;
        }

        .lab-search-pill {
          width: 100%;
          max-width: 600px;
          display: flex;
          align-items: center;
          gap: 1rem;
          padding: 0.8rem 1.5rem;
          border-radius: var(--radius-lg);
          transition: all 0.3s ease;
        }

        .lab-search-pill:focus-within {
          border-color: var(--secondary);
          background: rgba(0, 0, 0, 0.2);
          box-shadow: 0 0 40px var(--secondary-glow);
        }

        .lab-search-input {
          flex: 1;
          background: transparent;
          border: none;
          color: var(--text-main);
          font-family: var(--font-mono);
          font-size: 0.85rem;
          font-weight: 700;
          letter-spacing: 0.1em;
          outline: none;
        }

        .lab-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
          gap: 1.5rem;
        }

        .lab-project-card {
          background: var(--bg-card);
          backdrop-filter: var(--glass-blur);
          border: 1px solid var(--glass-border);
          border-radius: var(--radius-lg);
          padding: 2rem;
          display: flex;
          flex-direction: column;
          gap: 1.75rem;
          min-height: 260px;
          cursor: pointer;
          position: relative;
          overflow: hidden;
          transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
          box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
        }

        .lab-project-card:hover {
          border-color: var(--secondary);
          transform: translateY(-5px);
          background: rgba(30, 41, 59, 0.6);
        }

        .card-top {
          display: flex;
          align-items: center;
          justify-content: space-between;
        }

        .lab-icon-box {
          width: 44px;
          height: 44px;
          background: var(--bg-body);
          border: 1px solid var(--glass-border);
          border-radius: var(--radius-md);
          display: flex;
          align-items: center;
          justify-content: center;
          color: var(--secondary);
          transition: all 0.3s ease;
        }

        .lab-project-card:hover .lab-icon-box {
          border-color: var(--secondary);
          box-shadow: 0 0 15px var(--secondary-glow);
        }

        .btn-terminate {
          background: transparent;
          border: none;
          color: var(--text-dim);
          padding: 0.5rem;
          border-radius: var(--radius-sm);
          transition: var(--transition-fast);
          opacity: 0;
        }

        .lab-project-card:hover .btn-terminate {
          opacity: 1;
        }

        .btn-terminate:hover {
          color: #ef4444;
          background: rgba(239, 68, 68, 0.1);
        }

        .project-title {
          font-family: var(--font-heading);
          font-size: 1.4rem;
          font-weight: 800;
          color: var(--text-main);
          margin-bottom: 0.6rem;
          letter-spacing: -0.03em;
        }

        .project-instructions {
          font-size: 0.9rem;
          color: var(--text-muted);
          line-height: 1.6;
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
          overflow: hidden;
        }

        .card-meta-row {
          margin-top: auto;
          display: flex;
          align-items: flex-end;
          justify-content: space-between;
          padding-top: 1.25rem;
          border-top: 1px solid var(--border);
        }

        .meta-item {
          display: flex;
          flex-direction: column;
        }

        .meta-val {
          font-family: var(--font-mono);
          font-size: 1.25rem;
          font-weight: 800;
          color: var(--text-main);
        }

        .meta-lbl {
          font-family: var(--font-mono);
          font-size: 0.55rem;
          font-weight: 800;
          letter-spacing: 0.15em;
          color: var(--text-dim);
        }

        .meta-date {
          font-family: var(--font-mono);
          font-size: 0.65rem;
          color: var(--text-dim);
          text-transform: uppercase;
        }

        .lab-accent-glow {
          position: absolute;
          bottom: 0;
          left: 0;
          right: 0;
          height: 2px;
          background: var(--secondary);
          opacity: 0;
          transition: 0.4s ease;
          box-shadow: 0 -4px 15px var(--secondary);
        }

        .lab-project-card:hover .lab-accent-glow {
          opacity: 1;
        }

        .lab-loading {
          padding: 6rem;
          text-align: center;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 1.5rem;
        }

        .lab-loading p {
          font-family: var(--font-mono);
          font-size: 0.8rem;
          letter-spacing: 0.2em;
          color: var(--text-dim);
        }

        .lab-empty {
          padding: 5rem 3rem;
          text-align: center;
          border-radius: var(--radius-xl);
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 2rem;
          border: 1px dashed var(--glass-border);
        }

        .lab-empty-icon {
          color: var(--text-dim);
          opacity: 0.3;
        }

        .lab-empty h3 {
          font-family: var(--font-mono);
          font-size: 1.1rem;
          letter-spacing: 0.4em;
          color: var(--text-main);
        }

        .lab-empty p {
          max-width: 420px;
          color: var(--text-muted);
          line-height: 1.6;
        }

        .btn-init-large {
          background: var(--secondary);
          color: #fff;
          border: none;
          padding: 1.25rem 2.5rem;
          border-radius: var(--radius-md);
          font-family: var(--font-mono);
          font-weight: 800;
          font-size: 0.8rem;
          letter-spacing: 0.15em;
          display: flex;
          align-items: center;
          gap: 1rem;
          cursor: pointer;
          transition: all 0.4s ease;
          box-shadow: 0 10px 30px var(--secondary-glow);
        }

        .lab-no-results {
          grid-column: 1 / -1;
          padding: 4rem;
          text-align: center;
          font-family: var(--font-mono);
          font-size: 0.75rem;
          color: var(--text-dim);
          letter-spacing: 0.1em;
        }

        /* Modal Lab Styles */
        .modal-content-lab {
          width: 100%;
          max-width: 560px;
          background: rgba(15, 23, 42, 0.95);
          backdrop-filter: blur(30px);
          border: 1px solid var(--glass-border);
          border-radius: var(--radius-xl);
          padding: 2.5rem;
          display: flex;
          flex-direction: column;
          gap: 2.5rem;
          animation: slideUp 0.4s cubic-bezier(0.16, 1, 0.3, 1);
          box-shadow: 0 20px 60px rgba(0, 0, 0, 0.6);
        }

        .modal-head {
          display: flex;
          align-items: center;
          justify-content: space-between;
        }

        .modal-id-group {
          display: flex;
          align-items: center;
          gap: 1rem;
        }

        .modal-pulse {
          width: 10px;
          height: 10px;
          background: var(--secondary);
          border-radius: 50%;
          box-shadow: 0 0 15px var(--secondary);
          animation: pulse-glow 2s infinite;
        }

        .modal-head h2 {
          font-family: var(--font-mono);
          font-size: 0.9rem;
          font-weight: 800;
          letter-spacing: 0.2em;
          color: var(--text-main);
          margin: 0;
        }

        .lab-form {
          display: flex;
          flex-direction: column;
          gap: 2rem;
        }

        .lab-group {
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
        }

        .lab-group label {
          font-family: var(--font-mono);
          font-size: 0.65rem;
          font-weight: 800;
          color: var(--text-dim);
          letter-spacing: 0.2em;
        }

        .lab-group input, .lab-group textarea {
          background: rgba(0, 0, 0, 0.3);
          border: 1px solid var(--glass-border);
          border-radius: var(--radius-md);
          padding: 1rem;
          color: var(--text-main);
          font-family: var(--font-body);
          font-size: 1rem;
          outline: none;
          transition: all 0.3s ease;
        }

        .lab-group input:focus, .lab-group textarea:focus {
          border-color: var(--secondary);
          background: rgba(0, 0, 0, 0.5);
          box-shadow: 0 0 20px var(--secondary-glow);
        }

        .modal-ops {
          display: flex;
          gap: 1.25rem;
          margin-top: 1rem;
        }

        .btn-lab-cancel {
          flex: 1;
          background: transparent;
          border: 1px solid var(--glass-border);
          color: var(--text-dim);
          padding: 1rem;
          border-radius: var(--radius-md);
          font-family: var(--font-mono);
          font-weight: 800;
          font-size: 0.75rem;
          letter-spacing: 0.1em;
          cursor: pointer;
          transition: all 0.3s ease;
        }

        .btn-lab-cancel:hover {
          color: #fff;
          border-color: #fff;
          background: rgba(255, 255, 255, 0.05);
        }

        .btn-lab-submit {
          flex: 2;
          background: var(--secondary);
          color: #fff;
          border: none;
          padding: 1rem;
          border-radius: var(--radius-md);
          font-family: var(--font-mono);
          font-weight: 800;
          font-size: 0.75rem;
          letter-spacing: 0.1em;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 0.75rem;
          cursor: pointer;
          transition: all 0.4s ease;
          box-shadow: 0 10px 25px var(--secondary-glow);
        }

        .btn-lab-submit:hover:not(:disabled) {
          filter: brightness(1.2);
          transform: translateY(-2px);
        }

        @media (max-width: 768px) {
          .projects-lab { padding: 1.5rem; }
          .projects-lab-header { flex-direction: column; align-items: stretch; padding: 2rem; }
          .btn-init-lab { justify-content: center; }
          .lab-grid { grid-template-columns: 1fr; }
        }
      `}</style>
    </div>
  );
}
