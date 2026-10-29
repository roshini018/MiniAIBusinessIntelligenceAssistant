import React from 'react';
import { DollarSign, ShoppingCart, Award, MapPin } from 'lucide-react';
import type { KPIResponse } from '../types/bi';
import { formatCurrency, formatNumber } from '../config/constants';

interface KPISectionProps {
  kpis: KPIResponse | null;
  isLoading: boolean;
  error?: string | null;
  onRetry?: () => void;
}

export const KPISection: React.FC<KPISectionProps> = ({
  kpis,
  isLoading,
  error,
  onRetry,
}) => {
  if (error) {
    return (
      <div
        style={{
          padding: '12px 16px',
          background: 'var(--accent-red-subtle)',
          border: '1px solid var(--accent-red-border)',
          borderRadius: 'var(--radius-sm)',
          fontSize: 12,
          color: 'var(--accent-red)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <span>Failed to load KPI metrics: {error}</span>
        {onRetry && (
          <button
            onClick={onRetry}
            style={{
              fontSize: 11,
              fontWeight: 500,
              textDecoration: 'underline',
              color: 'var(--accent-red)',
            }}
          >
            Retry
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="kpi-grid">
      {/* 1. Total Revenue */}
      <div className="kpi-card">
        <div className="kpi-label-row">
          <span className="kpi-label">Total Revenue</span>
          <DollarSign size={14} className="kpi-icon" />
        </div>
        {isLoading || !kpis ? (
          <div className="kpi-skeleton" />
        ) : (
          <>
            <div className="kpi-value">{formatCurrency(kpis.total_revenue)}</div>
            <div className="kpi-subtext">Cumulative settled sales</div>
          </>
        )}
      </div>

      {/* 2. Orders Counted */}
      <div className="kpi-card">
        <div className="kpi-label-row">
          <span className="kpi-label">Orders Counted</span>
          <ShoppingCart size={14} className="kpi-icon" />
        </div>
        {isLoading || !kpis ? (
          <div className="kpi-skeleton" />
        ) : (
          <>
            <div className="kpi-value">{formatNumber(kpis.orders_counted)}</div>
            <div className="kpi-subtext">Completed transactions</div>
          </>
        )}
      </div>

      {/* 3. Top Product */}
      <div className="kpi-card">
        <div className="kpi-label-row">
          <span className="kpi-label">Top Product</span>
          <Award size={14} className="kpi-icon" />
        </div>
        {isLoading || !kpis ? (
          <div className="kpi-skeleton" />
        ) : (
          <>
            <div className="kpi-value">{kpis.top_product.name || '—'}</div>
            <div className="kpi-subtext">
              Revenue:{' '}
              <span className="kpi-subtext-highlight">
                {formatCurrency(kpis.top_product.revenue)}
              </span>
            </div>
          </>
        )}
      </div>

      {/* 4. Top Region */}
      <div className="kpi-card">
        <div className="kpi-label-row">
          <span className="kpi-label">Top Region</span>
          <MapPin size={14} className="kpi-icon" />
        </div>
        {isLoading || !kpis ? (
          <div className="kpi-skeleton" />
        ) : (
          <>
            <div className="kpi-value">{kpis.top_region.name || '—'}</div>
            <div className="kpi-subtext">
              Revenue:{' '}
              <span className="kpi-subtext-highlight">
                {formatCurrency(kpis.top_region.revenue)}
              </span>
            </div>
          </>
        )}
      </div>
    </div>
  );
};
