import React from 'react';
import {
  BarChart3,
  MessageSquareText,
  Database,
  Layers,
  X,
  RefreshCw,
} from 'lucide-react';

interface SidebarProps {
  activeTab: 'overview' | 'ask';
  onSelectTab: (tab: 'overview' | 'ask') => void;
  isBackendConnected: boolean;
  onRefreshHealth: () => void;
  isCheckingHealth: boolean;
  isOpenOnMobile: boolean;
  onCloseMobile: () => void;
  ordersCounted?: number;
  timeframeLabel?: string | null;
  isLoadingMetadata?: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  onSelectTab,
  isBackendConnected,
  onRefreshHealth,
  isCheckingHealth,
  isOpenOnMobile,
  onCloseMobile,
  ordersCounted,
  timeframeLabel,
  isLoadingMetadata,
}) => {
  return (
    <aside
      id="mobile-sidebar"
      className={`sidebar ${isOpenOnMobile ? 'open' : ''}`}
      aria-label="Main sidebar navigation"
    >
      {/* Product Identity Header */}
      <div className="sidebar-header">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div className="brand-badge">
            <div className="brand-icon-box">
              <Layers size={18} />
            </div>
            <div className="brand-titles">
              <span className="brand-name">Mini BI</span>
              <span className="brand-subtitle">Business Intelligence</span>
            </div>
          </div>
          {isOpenOnMobile && (
            <button
              type="button"
              onClick={onCloseMobile}
              className="sidebar-close-btn"
              aria-label="Close navigation drawer"
            >
              <X size={18} />
            </button>
          )}
        </div>
      </div>

      {/* Navigation */}
      <nav className="sidebar-nav" aria-label="Main navigation">
        <button
          className={`sidebar-nav-item ${activeTab === 'overview' ? 'active' : ''}`}
          onClick={() => {
            onSelectTab('overview');
            onCloseMobile();
          }}
        >
          <BarChart3 size={15} className="icon" />
          <span>Overview</span>
        </button>

        <button
          className={`sidebar-nav-item ${activeTab === 'ask' ? 'active' : ''}`}
          onClick={() => {
            onSelectTab('ask');
            onCloseMobile();
          }}
        >
          <MessageSquareText size={15} className="icon" />
          <span>Ask Analytics</span>
        </button>
      </nav>

      {/* Dataset Info */}
      <div className="sidebar-section-title">Dataset Reference</div>
      <div className="dataset-card">
        <div className="dataset-header">
          <Database size={14} style={{ color: 'var(--text-muted)' }} />
          <span className="dataset-title">sales.csv</span>
          <span className="dataset-badge">SQLITE</span>
        </div>
        <div className="dataset-meta">
          <div className="dataset-meta-item">
            <span className="dataset-meta-label">Total Orders</span>
            <span style={{ fontFamily: 'var(--font-mono)' }}>
              {ordersCounted !== undefined ? ordersCounted : '48'}
            </span>
          </div>
          <div className="dataset-meta-item">
            <span className="dataset-meta-label">Timeframe</span>
            <span style={{ fontFamily: 'var(--font-mono)' }}>
              {isLoadingMetadata ? '...' : timeframeLabel || 'Jan – Jun 2026'}
            </span>
          </div>
          <div className="dataset-meta-item">
            <span className="dataset-meta-label">Access Mode</span>
            <span style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>Read-Only</span>
          </div>
        </div>
      </div>

      {/* System Status Footer */}
      <div className="sidebar-footer">
        <div className="status-indicator-box">
          <div className="status-left">
            <div className={`status-dot ${isBackendConnected ? 'connected' : ''}`} />
            <span>Connection</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span className={`status-badge ${isBackendConnected ? 'connected' : 'disconnected'}`}>
              {isBackendConnected ? 'Connected' : 'Offline'}
            </span>
            <button
              type="button"
              onClick={onRefreshHealth}
              disabled={isCheckingHealth}
              title="Re-check backend health"
              aria-label="Re-check backend connection"
              style={{
                padding: 2,
                color: 'var(--text-muted)',
                opacity: isCheckingHealth ? 0.5 : 1,
                display: 'flex',
                alignItems: 'center',
                cursor: isCheckingHealth ? 'not-allowed' : 'pointer',
              }}
            >
              <RefreshCw size={12} className={isCheckingHealth ? 'spin' : ''} />
            </button>
          </div>
        </div>
      </div>
    </aside>
  );
};
