import React from 'react';
import { NavLink } from 'react-router-dom';
import { Search, Library, User } from 'lucide-react';

export default function MobileNavbar() {
    const navItems = [
        { icon: <Search size={24} />, id: 'home', path: '/' },
        { icon: <Library size={24} />, id: 'projects', path: '/projects' },
        { icon: <User size={24} />, id: 'profile', path: '/profile' },
    ];

    return (
        <nav className="mobile-navbar glass">
            {navItems.map((item) => (
                <NavLink
                    key={item.id}
                    to={item.path}
                    className={({ isActive }) => `mobile-nav-item ${isActive ? 'active' : ''}`}
                >
                    {item.icon}
                </NavLink>
            ))}

            <style>{`
        .mobile-navbar {
          position: fixed;
          bottom: 20px;
          left: 50%;
          transform: translateX(-50%);
          width: calc(100% - 40px);
          max-width: 400px;
          height: var(--navbar-height);
          display: flex;
          align-items: center;
          justify-content: space-around;
          padding: 0 1rem;
          border-radius: var(--radius-full);
          z-index: 2000;
          display: none;
        }

        .mobile-nav-item {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 48px;
          height: 48px;
          border-radius: 50%;
          color: var(--text-muted);
          transition: var(--transition-base);
        }

        .mobile-nav-item.active {
          color: var(--secondary);
          background: var(--secondary-glow);
          transform: translateY(-4px);
        }

        @media (max-width: 768px) {
          .mobile-navbar {
            display: flex;
          }
        }
      `}</style>
        </nav>
    );
}
