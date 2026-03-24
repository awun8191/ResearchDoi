import React, { useState } from 'react';
import { NavLink, useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { LogOut, User } from 'lucide-react';
import Logo from './Logo';

export default function Sidebar({ isOpen }) {
  const { currentUser, logout } = useAuth();
  const navigate = useNavigate();
  const [showUserMenu, setShowUserMenu] = useState(false);

  async function handleLogout() {
    try {
      await logout();
      navigate('/login');
    } catch (err) {
      console.error('Failed to log out', err);
    }
  }

  const navItems = [
    { icon: <SearchIcon />, id: 'search', path: '/' },
    { icon: <LibraryIcon />, id: 'files', path: '/projects' },
  ];

  return (
    <aside className={`sidebar glass ${isOpen ? 'active' : ''}`}>
      <div className="sidebar-top">
        <NavLink to="/" className="logo-rail">
          <Logo size={44} variant="icon" useSchemeColor={true} />
        </NavLink>
      </div>

      <nav className="nav-rail">
        {navItems.map((item) => (
          <NavLink
            key={item.id}
            to={item.path}
            className={({ isActive }) => `rail-item ${isActive ? 'active' : ''}`}
            title={item.id.charAt(0).toUpperCase() + item.id.slice(1)}
          >
            {item.icon}
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-bottom">
        <div className="user-rail-container">
          {showUserMenu && (
            <div className="user-popup glass">
              <div className="user-info-section">
                <p className="user-email">{currentUser?.email}</p>
              </div>
              <div className="popup-divider"></div>
              <Link to="/profile" className="popup-item profile-link" onClick={() => setShowUserMenu(false)}>
                <User size={14} /> Profile & Settings
              </Link>
              <div className="popup-divider"></div>
              <button className="popup-item logout-btn" onClick={handleLogout}>
                <LogOut size={14} /> Log Out
              </button>
            </div>
          )}
          <div
            className="avatar-rail"
            onClick={() => setShowUserMenu(!showUserMenu)}
          >
            {currentUser?.email?.charAt(0).toUpperCase() || 'U'}
          </div>
        </div>
      </div>

      <style>{`
        .sidebar {
          position: fixed;
          top: 20px;
          left: 20px;
          height: calc(100vh - 40px);
          width: 72px;
          background: var(--bg-sidebar);
          border: 1px solid var(--secondary-glow);
          border-radius: var(--radius-xl);
          display: flex;
          flex-direction: column;
          align-items: center;
          padding: 1.25rem 0;
          z-index: 1000;
          transition: var(--transition-base);
          box-shadow: var(--shadow-xl);
          backdrop-filter: blur(20px);
        }

        .sidebar:hover {
          border-color: var(--secondary);
          box-shadow: 0 0 40px var(--secondary-glow);
        }

        .logo-rail {
          width: 48px;
          height: 48px;
          display: flex;
          align-items: center;
          justify-content: center;
          color: var(--text-sidebar);
          margin-bottom: 2rem;
          transition: var(--transition-fast);
          cursor: pointer;
          text-decoration: none;
        }

        .logo-rail:hover {
          transform: scale(1.05);
          color: var(--secondary);
        }

        .nav-rail {
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
          flex: 1;
          align-items: center;
        }

        .rail-item {
          width: 48px;
          height: 48px;
          display: flex;
          align-items: center;
          justify-content: center;
          border-radius: var(--radius-lg);
          color: var(--text-sidebar);
          background: transparent;
          border: none;
          cursor: pointer;
          transition: var(--transition-fast);
          position: relative;
          text-decoration: none;
          opacity: 0.7;
        }

        .rail-item:hover {
          color: var(--text-sidebar);
          background: rgba(255, 255, 255, 0.08);
          opacity: 1;
        }

        .rail-item.active {
          color: var(--secondary);
          background: var(--secondary-glow);
          opacity: 1;
        }

        .rail-item.active::after {
          content: '';
          position: absolute;
          left: 0;
          top: 12px;
          bottom: 12px;
          width: 3px;
          background: var(--secondary);
          border-radius: 0 4px 4px 0;
        }

        .sidebar-bottom {
          margin-top: auto;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 1.25rem;
        }

        .avatar-rail {
          width: 40px;
          height: 40px;
          border-radius: 50%;
          background: rgba(255, 255, 255, 0.08);
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: 700;
          font-size: 0.8rem;
          color: var(--text-sidebar);
          border: 1px solid var(--border);
          font-family: var(--font-mono);
          cursor: pointer;
          transition: var(--transition-base);
        }

        .avatar-rail:hover {
          border-color: var(--secondary);
          background: var(--secondary-glow);
          transform: scale(1.05);
        }

        .user-rail-container {
          position: relative;
        }

        .user-popup {
          position: absolute;
          bottom: 0;
          left: calc(100% + 16px);
          width: 220px;
          padding: 0.75rem;
          border-radius: var(--radius-lg);
          border: 1px solid var(--border);
          background: var(--bg-surface);
          backdrop-filter: blur(20px);
          z-index: 2001;
          display: flex;
          flex-direction: column;
          gap: 4px;
          animation: slideUp 0.3s cubic-bezier(0.16, 1, 0.3, 1);
          box-shadow: var(--shadow-lg);
        }

        .user-info-section {
          padding: 0.5rem 0.75rem;
          margin-bottom: 0.25rem;
        }

        .user-email {
          font-size: 0.75rem;
          color: var(--text-main);
          font-weight: 500;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .popup-item {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          padding: 0.75rem;
          width: 100%;
          background: transparent;
          color: var(--text-main);
          font-size: 0.85rem;
          border-radius: var(--radius-md);
          text-align: left;
          transition: var(--transition-fast);
          border: none;
          cursor: pointer;
        }

        .popup-item:hover {
          background: var(--primary-glow);
        }

        .popup-divider {
          height: 1px;
          background: var(--border);
          margin: 0.25rem 0.5rem;
        }

        .logout-btn {
          color: #fb7185;
        }

        .logout-btn:hover {
          background: rgba(244, 63, 94, 0.1);
        }

        @media (max-width: 768px) {
          .sidebar {
            display: none;
          }
        }
      `}</style>
    </aside>
  );
}

const SearchIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
);

const LibraryIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M7 8H5a2 2 0 0 0-2 2v10a2 2 0 0 0 2-2v-2"></path>
    <rect x="8" y="2" width="12" height="14" rx="2" ry="2"></rect>
  </svg>
);
