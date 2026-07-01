import React from 'react';
import { NavLink } from 'react-router-dom';
import { Search, Clock, FolderOpen, User } from 'lucide-react';
import Logo from './Logo';

export default function Sidebar() {
  const navItems = [
    { icon: <Search size={22} />, path: '/', label: 'Console' },
    { icon: <Clock size={22} />, path: '/history', label: 'History' },
    { icon: <FolderOpen size={22} />, path: '/projects', label: 'Projects' },
    { icon: <User size={22} />, path: '/profile', label: 'Profile' },
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-top">
        <NavLink to="/" className="sidebar-logo">
          <Logo size={32} useSchemeColor={true} />
        </NavLink>

        <nav className="nav-stack">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
              title={item.label}
            >
              <div className="nav-icon-wrapper">
                {item.icon}
                <div className="nav-indicator" />
              </div>
            </NavLink>
          ))}
        </nav>
      </div>

      <style>{`
        .sidebar {
          width: var(--sidebar-width);
          height: 100vh;
          background: var(--bg-sidebar);
          backdrop-filter: var(--glass-blur);
          -webkit-backdrop-filter: var(--glass-blur);
          border-right: 1px solid var(--glass-border);
          position: fixed;
          left: 0;
          top: 0;
          display: flex;
          flex-direction: column;
          align-items: center;
          padding: 1.5rem 0;
          z-index: 100;
          box-shadow: var(--shadow-inner);
        }

        @media (max-width: 768px) {
          .sidebar {
            display: none;
          }
        }

        .sidebar-top {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 2.5rem;
          width: 100%;
        }

        .sidebar-logo {
          transition: transform 0.3s ease;
        }

        .sidebar-logo:hover {
          transform: rotate(10deg) scale(1.1);
        }

        .nav-stack {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 0.75rem;
          width: 100%;
        }

        .nav-item {
          width: 50px;
          height: 50px;
          display: flex;
          align-items: center;
          justify-content: center;
          color: var(--text-dim);
          border-radius: 14px;
          transition: all 0.2s ease;
          position: relative;
        }

        .nav-item:hover {
          color: var(--text-main);
          background: rgba(255, 255, 255, 0.05);
        }

        .nav-item.active {
          color: var(--secondary);
          background: var(--secondary-glow);
        }

        .nav-icon-wrapper {
          position: relative;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .nav-indicator {
          position: absolute;
          left: -12px;
          width: 3px;
          height: 0;
          background: var(--secondary);
          border-radius: 0 4px 4px 0;
          transition: height 0.3s ease, opacity 0.3s ease;
          opacity: 0;
          box-shadow: 0 0 10px var(--secondary);
        }

        .nav-item.active .nav-indicator {
          height: 20px;
          opacity: 1;
        }
      `}</style>
    </aside>
  );
}
