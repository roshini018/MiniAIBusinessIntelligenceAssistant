import React from 'react';
import { formatCurrency, formatNumber } from '../../config/constants';

interface DataTableProps {
  data: Record<string, any>[];
  title?: string;
}

export const DataTable: React.FC<DataTableProps> = ({ data, title }) => {
  if (!data || data.length === 0) {
    return null;
  }

  const columns = Object.keys(data[0]);

  const formatCellValue = (key: string, value: any) => {
    if (value === null || value === undefined) return '—';

    const lowerKey = key.toLowerCase();
    if (typeof value === 'number') {
      if (lowerKey.includes('revenue') || lowerKey.includes('price') || lowerKey.includes('sales')) {
        return formatCurrency(value);
      }
      if (lowerKey.includes('percent')) {
        return `${value > 0 ? '+' : ''}${value.toFixed(1)}%`;
      }
      if (lowerKey.includes('count') || lowerKey.includes('orders') || lowerKey.includes('quantity')) {
        return formatNumber(value);
      }
      return value.toLocaleString();
    }

    return String(value);
  };

  const formatHeader = (key: string) => {
    return key.replace(/_/g, ' ');
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      {title && (
        <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          {title}
        </div>
      )}
      <div className="data-table-container">
        <table className="data-table">
          <thead>
            <tr>
              {columns.map((col) => (
                <th key={col}>{formatHeader(col)}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((row, idx) => (
              <tr key={idx}>
                {columns.map((col) => {
                  const val = row[col];
                  const isNumeric = typeof val === 'number';
                  return (
                    <td
                      key={col}
                      className={isNumeric ? 'font-mono' : ''}
                      style={{
                        textAlign: isNumeric ? 'right' : 'left',
                      }}
                    >
                      {formatCellValue(col, val)}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
