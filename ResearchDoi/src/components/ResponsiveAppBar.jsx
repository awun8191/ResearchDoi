import React from 'react';
import { useNavigate, useLocation, NavLink } from 'react-router-dom';
import { ArrowLeft, Search, Library, User } from 'lucide-react';
import Logo from './Logo';

export default function ResponsiveAppBar({ title, rightAction }) {
  const navigate = useNavigate();
  const location = useLocation();
  const isProjectWorkspace = location.pathname.startsWith('/projects/');

  // Title mapping based on path
  const getPageTitle = () => {
    if (title) return title;
    const path = location.pathname;
    if (path === '/') return 'A.I Knowledge Graph';
    if (path === '/projects') return 'Projects';
    if (path === '/profile') return 'Profile';
    if (path.startsWith('/projects/')) return 'Workspace';
    return 'ResearchDoi';
  };

  const navItems = [
    { icon: <Search size={20} />, id: 'home', path: '/' },
    { icon: <Library size={20} />, id: 'projects', path: '/projects' },
    { icon: <User size={20} />, id: 'profile', path: '/profile' },
  ];

  return (
    <header className="responsive-app-bar glass">
      <div className="app-bar-content">
        <div className="app-bar-left">
          {isProjectWorkspace ? (
            <button onClick={() => navigate('/projects')} className="back-btn">
              <ArrowLeft size={20} />
            </button>
          ) : (
            <div className="mobile-logo-container">
              <Logo variant="icon" size={40} useSchemeColor={true} />
            </div>
          )}
          <h1 className="page-title">{getPageTitle()}</h1>
        </div>

        <div className="app-bar-right">
          {rightAction && <div className="app-bar-action">{rightAction}</div>}
        </div>
      </div>

      <style>{`
        .responsive-app-bar {
          position: sticky;
          top: 10px;
          margin: 0 0.75rem 0.75rem;
          height: var(--appbar-height);
          z-index: 1500;
          display: flex;
          align-items: center;
          padding: 0 1rem;
          background: rgba(var(--bg-body-rgb, 9, 9, 11), 0.6);
          backdrop-filter: blur(12px);
          border: 1px solid var(--glass-border);
          border-radius: var(--radius-xl);
          transition: var(--transition-base);
          box-shadow: var(--shadow-md);
        }

        @media (max-width: 768px) {
          .responsive-app-bar {
            display: flex;
          }
        }

        @media (min-width: 769px) {
          .responsive-app-bar {
            display: none;
          }
        }

        .app-bar-left {
          display: flex;
          align-items: center;
          gap: 1rem;
        }

        .app-bar-right {
           display: flex;
           align-items: center;
           gap: 1rem;
        }

        .page-title {
          font-size: 1.1rem;
          font-weight: 600;
          color: var(--text-main);
          letter-spacing: -0.01em;
        }

        .back-btn {
          width: 36px;
          height: 36px;
          border-radius: var(--radius-md);
          display: flex;
          align-items: center;
          justify-content: center;
          background: var(--primary-glow);
          color: var(--text-main);
          transition: var(--transition-base);
        }

        .back-btn:hover {
          background: var(--secondary-glow);
          color: var(--secondary);
        }

          justify-content: space-between;
        }

        .mobile-logo-container {
          display: none;
        }

        .mobile-nav-link {
          width: 40px;
          height: 40px;
          display: flex;
          align-items: center;
          justify-content: center;
          border-radius: var(--radius-md);
          color: var(--text-muted);
          transition: var(--transition-base);
        }

        .mobile-nav-link:hover {
          background: rgba(255, 255, 255, 0.05);
          color: var(--text-main);
        }

        .mobile-nav-link.active {
          color: var(--secondary);
          background: var(--secondary-glow);
        }

        @media (max-width: 768px) {
          .responsive-app-bar {
             padding: 0 1rem;
             justify-content: center;
          }
          .mobile-logo-container {
            display: block;
            margin: 0 auto;
          }
          .app-bar-left {
            flex: 1;
            justify-content: center;
          }
          .app-bar-right {
             position: absolute;
             right: 1.5rem;
          }
        }
        
        @media (max-width: 480px) {
           .page-title { display: none; }
        }
      `}</style>
    </header>
  );
}
