import React from 'react';
import { formatCurrency } from '../../config/constants';

interface RankingItem {
  name: string;
  value: number;
}

interface RankingBarChartProps {
  data: Record<string, any>[];
  labelKey: string;
  valueKey: string;
  title?: string;
}

export const RankingBarChart: React.FC<RankingBarChartProps> = ({
  data,
  labelKey,
  valueKey,
  title,
}) => {
  if (!data || data.length === 0) return null;

  const items: RankingItem[] = data
    .filter((d) => d[labelKey] && typeof d[valueKey] === 'number')
    .map((d) => ({
      name: String(d[labelKey]),
      value: Number(d[valueKey]),
    }));

  if (items.length === 0) return null;

  const maxValue = Math.max(...items.map((i) => i.value), 1);

  return (
    <div className="visualization-container">
      {title && (
        <div className="viz-title">
          <span>{title}</span>
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
            Ranked by Revenue
          </span>
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
        {items.map((item, idx) => {
          const pct = Math.min(100, Math.max(4, (item.value / maxValue) * 100));
          const isTop = idx === 0;

          return (
            <div key={item.name} style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  fontSize: 12,
                  alignItems: 'center',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span
                    style={{
                      fontSize: 10,
                      fontWeight: 600,
                      color: isTop ? 'var(--accent-blue)' : 'var(--text-muted)',
                      fontFamily: 'var(--font-mono)',
                      width: 18,
                    }}
                  >
                    #{idx + 1}
                  </span>
                  <span style={{ fontWeight: isTop ? 600 : 400, color: 'var(--text-primary)' }}>
                    {item.name}
                  </span>
                </div>
                <span className="font-mono" style={{ color: isTop ? '#93c5fd' : 'var(--text-secondary)' }}>
                  {formatCurrency(item.value)}
                </span>
              </div>

              {/* Progress bar */}
              <div
                style={{
                  width: '100%',
                  height: 5,
                  backgroundColor: '#18181c',
                  borderRadius: 3,
                  overflow: 'hidden',
                }}
              >
                <div
                  style={{
                    width: `${pct}%`,
                    height: '100%',
                    backgroundColor: isTop ? '#3b82f6' : '#27272a',
                    borderRadius: 3,
                    transition: 'width 0.3s ease',
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
