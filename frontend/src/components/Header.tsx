import React from 'react';
import { Menu, X, AlertCircle } from 'lucide-react';

interface HeaderProps {
  isBackendConnected: boolean;
  isMobileMenuOpen: boolean;
  onToggleMobileMenu: () => void;
  title?: string;
  description?: string;
  breadcrumb?: string;
}

export const Header: React.FC<HeaderProps> = ({
  isBackendConnected,
  isMobileMenuOpen,
  onToggleMobileMenu,
  title = 'Business Intelligence',
  description = 'Explore enterprise sales performance through natural-language queries.',
  breadcrumb = 'Sales Workspace / Analytics Engine',
}) => {
  return (
    <header className="page-header">
      <div className="header-top">
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <button
            type="button"
            className="mobile-menu-btn"
            onClick={onToggleMobileMenu}
            aria-label={isMobileMenuOpen ? 'Close navigation menu' : 'Open navigation menu'}
            aria-expanded={isMobileMenuOpen}
            aria-controls="mobile-sidebar"
          >
            {isMobileMenuOpen ? <X size={18} /> : <Menu size={18} />}
          </button>
          <div className="breadcrumb">{breadcrumb}</div>
        </div>

        {/* Status indicator: only show alert if backend is disconnected */}
        {!isBackendConnected && (
          <div className="header-badge" style={{ borderColor: 'var(--accent-red-border)' }}>
            <AlertCircle size={13} style={{ color: 'var(--accent-red)' }} />
            <span style={{ color: 'var(--accent-red)' }}>Offline</span>
          </div>
        )}
      </div>

      <h1 className="page-title">{title}</h1>

      <p className="page-description">{description}</p>
    </header>
  );
};
