import React, { useState } from 'react';
import { formatCurrency } from '../../config/constants';

interface MonthlyDataPoint {
  month: string;
  revenue: number;
}

interface MonthlyTrendChartProps {
  data: MonthlyDataPoint[];
}

const MONTH_SHORT_NAMES: Record<string, string> = {
  '01': 'Jan',
  '02': 'Feb',
  '03': 'Mar',
  '04': 'Apr',
  '05': 'May',
  '06': 'Jun',
  '07': 'Jul',
  '08': 'Aug',
  '09': 'Sep',
  '10': 'Oct',
  '11': 'Nov',
  '12': 'Dec',
};

function formatMonthLabel(monthStr: string): string {
  const parts = monthStr.split('-');
  if (parts.length === 2 && MONTH_SHORT_NAMES[parts[1]]) {
    return MONTH_SHORT_NAMES[parts[1]];
  }
  return monthStr;
}

export const MonthlyTrendChart: React.FC<MonthlyTrendChartProps> = ({ data }) => {
  // Filter out non-month rows (e.g. "change" row in comparison)
  const validData = data.filter(
    (d) => d.month && d.month !== 'change' && typeof d.revenue === 'number'
  );

  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  if (validData.length === 0) return null;

  const maxRevenue = Math.max(...validData.map((d) => Math.max(0, d.revenue)), 1);
  const peakMonth = validData.reduce(
    (prev, curr) => (curr.revenue > prev.revenue ? curr : prev),
    validData[0]
  );

  // Extract year from dataset (e.g., "2026")
  const datasetYear = validData[0]?.month?.split('-')[0] || '';

  const height = 140;
  const paddingBottom = 24;
  const paddingTop = 16;
  const chartHeight = height - paddingBottom - paddingTop;

  return (
    <div className="visualization-container">
      <div className="viz-title">
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span>Monthly Revenue Distribution</span>
          {datasetYear && (
            <span style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
              ({datasetYear})
            </span>
          )}
        </div>
        <span style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
          Peak: {formatMonthLabel(peakMonth.month)} {datasetYear} ({formatCurrency(peakMonth.revenue)})
        </span>
      </div>

      <div style={{ position: 'relative', width: '100%', height }}>
        <svg
          viewBox={`0 0 ${validData.length * 100} ${height}`}
          style={{ width: '100%', height: '100%', overflow: 'visible' }}
          preserveAspectRatio="none"
        >
          {/* Subtle grid lines */}
          <line
            x1="0"
            y1={paddingTop + chartHeight * 0.5}
            x2={validData.length * 100}
            y2={paddingTop + chartHeight * 0.5}
            stroke="#1c1c21"
            strokeDasharray="4 4"
          />
          <line
            x1="0"
            y1={paddingTop + chartHeight}
            x2={validData.length * 100}
            y2={paddingTop + chartHeight}
            stroke="#27272a"
          />

          {validData.map((item, idx) => {
            const barWidth = 44;
            const x = idx * 100 + (100 - barWidth) / 2;
            const barHeight = (Math.max(0, item.revenue) / maxRevenue) * chartHeight;
            const y = paddingTop + chartHeight - barHeight;
            const isPeak = item.month === peakMonth.month;
            const isHovered = hoveredIdx === idx;
            const monthLabel = formatMonthLabel(item.month);

            return (
              <g
                key={item.month}
                onMouseEnter={() => setHoveredIdx(idx)}
                onMouseLeave={() => setHoveredIdx(null)}
                style={{ cursor: 'pointer' }}
              >
                {/* Bar */}
                <rect
                  x={x}
                  y={y}
                  width={barWidth}
                  height={Math.max(2, barHeight)}
                  rx={3}
                  fill={
                    isHovered
                      ? '#60a5fa'
                      : isPeak
                      ? '#3b82f6'
                      : '#27272a'
                  }
                  style={{ transition: 'fill 0.15s ease' }}
                />

                {/* Value on top if hovered or peak */}
                {(isHovered || isPeak) && (
                  <text
                    x={x + barWidth / 2}
                    y={Math.max(12, y - 6)}
                    textAnchor="middle"
                    fill={isPeak ? '#93c5fd' : '#a1a1aa'}
                    fontSize="11"
                    fontFamily="var(--font-mono)"
                    fontWeight="500"
                  >
                    {formatCurrency(item.revenue)}
                  </text>
                )}

                {/* X Axis label (short month name: Jan, Feb, Mar, etc.) */}
                <text
                  x={x + barWidth / 2}
                  y={height - 8}
                  textAnchor="middle"
                  fill={isHovered ? '#f4f4f5' : '#71717a'}
                  fontSize="11"
                  fontFamily="var(--font-mono)"
                >
                  {monthLabel}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
};
