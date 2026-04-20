import React from 'react';
import { NavLink } from 'react-router-dom';
import { Search, Clock, FolderOpen, User } from 'lucide-react';

export default function MobileBottomNav() {
  const navItems = [
    { icon: <Search size={22} />, path: '/', label: 'Search' },
    { icon: <Clock size={22} />, path: '/history', label: 'History' },
    { icon: <FolderOpen size={22} />, path: '/projects', label: 'Projects' },
    { icon: <User size={22} />, path: '/profile', label: 'Profile' },
  ];

  return (
    <nav className="mobile-nav">
      <div className="bottom-nav-content">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) => `bottom-nav-item ${isActive ? 'active' : ''}`}
          >
            {item.icon}
          </NavLink>
        ))}
      </div>

      <style>{`
        .mobile-nav {
          position: fixed;
          bottom: 1.5rem;
          left: 50%;
          transform: translateX(-50%);
          width: calc(100% - 3rem);
          max-width: 320px;
          height: 60px;
          z-index: 2000;
          border-radius: 20px;
          display: none;
          align-items: center;
          padding: 0 0.5rem;
          background: rgba(10, 10, 10, 0.8);
          backdrop-filter: blur(20px);
          border: 1px solid var(--border);
          box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
        }

        @media (max-width: 768px) {
          .mobile-nav {
            display: flex;
          }
        }

        .bottom-nav-content {
          width: 100%;
          display: flex;
          justify-content: space-around;
          align-items: center;
        }

        .bottom-nav-item {
          display: flex;
          align-items: center;
          justify-content: center;
          color: var(--text-dim);
          transition: var(--transition-base);
          padding: 0.75rem;
          border-radius: 14px;
          text-decoration: none;
        }

        .bottom-nav-item.active {
          color: var(--secondary);
          background: var(--secondary-glow);
        }
      `}</style>
    </nav>
  );
}
