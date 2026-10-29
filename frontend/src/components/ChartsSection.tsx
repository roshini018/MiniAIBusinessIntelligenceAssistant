import React, { useState, useEffect } from 'react';
import { fetchChartData } from '../api/client';
import { MonthlyTrendChart } from './Visualizations/MonthlyTrendChart';
import { RankingBarChart } from './Visualizations/RankingBarChart';
import type { ChartDataResponse } from '../types/bi';
import { BarChart3, RefreshCw, TrendingUp } from 'lucide-react';
import { formatCurrency } from '../config/constants';

export const ChartsSection: React.FC = () => {
  const [data, setData] = useState<ChartDataResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadCharts = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetchChartData();
      setData(res);
    } catch (err: any) {
      setError(err?.message || 'Failed to load chart data');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadCharts();
  }, []);

  if (isLoading) {
    return (
      <div className="charts-section">
        <div className="charts-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <BarChart3 size={16} style={{ color: 'var(--accent-blue)' }} />
            <span className="charts-title">Performance Breakdown</span>
          </div>
        </div>
        <div className="charts-grid">
          <div className="chart-card chart-card-wide">
            <div className="kpi-skeleton" style={{ width: '100%', height: 140, borderRadius: 8 }} />
          </div>
          <div className="chart-card">
            <div className="kpi-skeleton" style={{ width: '100%', height: 160, borderRadius: 8 }} />
          </div>
          <div className="chart-card">
            <div className="kpi-skeleton" style={{ width: '100%', height: 160, borderRadius: 8 }} />
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="charts-section">
        <div className="charts-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <BarChart3 size={16} style={{ color: 'var(--accent-blue)' }} />
            <span className="charts-title">Performance Breakdown</span>
          </div>
          <button
            type="button"
            onClick={loadCharts}
            className="chart-refresh-btn"
            aria-label="Retry loading chart data"
          >
            <RefreshCw size={12} />
            <span>Retry</span>
          </button>
        </div>
        <div
          style={{
            padding: '16px',
            backgroundColor: 'var(--accent-red-subtle)',
            border: '1px solid var(--accent-red-border)',
            borderRadius: 'var(--radius-sm)',
            fontSize: 13,
            color: 'var(--accent-red)',
          }}
        >
          {error}
        </div>
      </div>
    );
  }

  if (!data) return null;

  const hasMonthly = data.monthly_trend && data.monthly_trend.length > 0;
  const hasProducts = data.products && data.products.length > 0;
  const hasRegions = data.regions && data.regions.length > 0;

  if (!hasMonthly && !hasProducts && !hasRegions) return null;

  const peakMonth = hasMonthly
    ? data.monthly_trend.reduce(
        (prev, curr) => (curr.revenue > prev.revenue ? curr : prev),
        data.monthly_trend[0]
      )
    : null;

  const topProduct = hasProducts ? data.products[0] : null;

  return (
    <div className="charts-section">
      <div className="charts-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <BarChart3 size={16} style={{ color: 'var(--accent-blue)' }} />
          <span className="charts-title">Performance Breakdown</span>
        </div>
        <button
          type="button"
          onClick={loadCharts}
          className="chart-refresh-btn"
          title="Refresh chart data"
          aria-label="Refresh chart data"
        >
          <RefreshCw size={12} className={isLoading ? 'spin' : ''} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Monthly Revenue Trend - prominent & full width */}
      {hasMonthly && (
        <div className="chart-card chart-card-wide">
          <MonthlyTrendChart data={data.monthly_trend} />
        </div>
      )}

      {/* Product & Region breakdowns side by side */}
      <div className="charts-grid">
        {hasProducts && (
          <div className="chart-card">
            <RankingBarChart
              data={data.products}
              labelKey="product"
              valueKey="revenue"
              title="Revenue by Product"
            />
          </div>
        )}
        {hasRegions && (
          <div className="chart-card">
            <RankingBarChart
              data={data.regions}
              labelKey="region"
              valueKey="revenue"
              title="Revenue by Region"
            />
          </div>
        )}
      </div>

      {/* Data-driven insight callout */}
      {peakMonth && (
        <div className="charts-insight-banner">
          <TrendingUp size={14} style={{ color: 'var(--accent-blue)', flexShrink: 0 }} />
          <span>
            <strong>Performance Insight:</strong> Peak monthly revenue reached{' '}
            <strong>{formatCurrency(peakMonth.revenue)}</strong> in{' '}
            <strong>{peakMonth.month}</strong>
            {topProduct ? (
              <>
                , driven predominantly by <strong>{topProduct.product}</strong> ({formatCurrency(topProduct.revenue)}).
              </>
            ) : (
              '.'
            )}
          </span>
        </div>
      )}
    </div>
  );
};
