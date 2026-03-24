import React from 'react';
import { NavLink } from 'react-router-dom';
import { Search, Library, User } from 'lucide-react';

export default function MobileBottomNav() {
  const navItems = [
    { icon: <Search size={22} />, id: 'home', path: '/', label: 'Search' },
    { icon: <Library size={22} />, id: 'projects', path: '/projects', label: 'Library' },
    { icon: <User size={22} />, id: 'profile', path: '/profile', label: 'Profile' },
  ];

  return (
    <nav className="mobile-nav glass">
      <div className="bottom-nav-content">
        {navItems.map((item) => (
          <NavLink
            key={item.id}
            to={item.path}
            className={({ isActive }) => `bottom-nav-item ${isActive ? 'active' : ''}`}
          >
            <div className="icon-wrapper">{item.icon}</div>
            <span className="nav-label">{item.label}</span>
          </NavLink>
        ))}
      </div>

      <style>{`
        .mobile-nav {
          position: fixed;
          top: 10px;
          left: 0.75rem;
          right: 0.75rem;
          width: auto;
          max-width: none;
          height: 64px;
          z-index: 2000;
          border-radius: var(--radius-xl);
          display: none;
          align-items: center;
          padding: 0 0.5rem;
          background: var(--bg-sidebar);
          border: 1px solid var(--secondary-glow);
          box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
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
          flex-direction: column;
          align-items: center;
          gap: 4px;
          text-decoration: none;
          color: var(--text-sidebar);
          transition: var(--transition-base);
          padding: 0.5rem 1rem;
          border-radius: var(--radius-lg);
          min-width: 70px;
          opacity: 0.75;
        }

        .bottom-nav-item:hover {
          opacity: 1;
          background: rgba(255, 255, 255, 0.08);
        }

        .bottom-nav-item.active {
          color: var(--text-sidebar);
          background: var(--secondary-glow);
          opacity: 1;
        }

        .icon-wrapper {
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .nav-label {
          font-size: 0.65rem;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }
      `}</style>
    </nav>
  );
}
