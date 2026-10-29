import React, { useState } from 'react';
import {
  Sparkles,
  Cpu,
  ChevronDown,
  ChevronUp,
  Copy,
  Check,
  RotateCcw,
  Code2,
  Table as TableIcon,
} from 'lucide-react';
import type { QueryHistoryItem } from '../types/bi';
import { DataTable } from './Visualizations/DataTable';
import { MonthlyTrendChart } from './Visualizations/MonthlyTrendChart';
import { RankingBarChart } from './Visualizations/RankingBarChart';

interface ResultCardProps {
  item: QueryHistoryItem;
  onRetry?: (question: string) => void;
  onNotify?: (message: string) => void;
}

export const ResultCard: React.FC<ResultCardProps> = ({
  item,
  onRetry,
  onNotify,
}) => {
  const [showSql, setShowSql] = useState(false);
  const [showData, setShowData] = useState(false);
  const [copiedAnswer, setCopiedAnswer] = useState(false);
  const [copiedSql, setCopiedSql] = useState(false);

  const { response, error, isLoading, question } = item;

  const handleCopyAnswer = () => {
    if (!response?.answer) return;
    navigator.clipboard.writeText(response.answer);
    setCopiedAnswer(true);
    onNotify?.('Copied answer to clipboard');
    setTimeout(() => setCopiedAnswer(false), 2000);
  };

  const handleCopySql = () => {
    if (!response?.sql_used) return;
    navigator.clipboard.writeText(response.sql_used);
    setCopiedSql(true);
    onNotify?.('Copied SQL to clipboard');
    setTimeout(() => setCopiedSql(false), 2000);
  };

  const renderVisualization = () => {
    if (!response?.supporting_data || response.supporting_data.length === 0) {
      return null;
    }

    const intent = response.intent;
    const data = response.supporting_data;

    // Monthly trend or comparison chart
    if (intent === 'monthly_trend' || intent === 'month_comparison') {
      const hasMonth = data.some((d) => d.month && typeof d.revenue === 'number');
      if (hasMonth) {
        return <MonthlyTrendChart data={data as any} />;
      }
    }

    // Top product rankings
    if (intent === 'top_product') {
      const hasProduct = data.some((d) => d.product && typeof d.revenue === 'number');
      if (hasProduct) {
        return (
          <RankingBarChart
            data={data}
            labelKey="product"
            valueKey="revenue"
            title="Product Revenue Ranking"
          />
        );
      }
    }

    // Top region rankings
    if (intent === 'top_region') {
      const hasRegion = data.some((d) => d.region && typeof d.revenue === 'number');
      if (hasRegion) {
        return (
          <RankingBarChart
            data={data}
            labelKey="region"
            valueKey="revenue"
            title="Regional Revenue Ranking"
          />
        );
      }
    }

    return null;
  };

  return (
    <article className="result-card">
      {/* Header: User Question + Meta Badges */}
      <div className="result-header">
        <h3 className="question-text">
          <span style={{ color: 'var(--text-muted)', fontSize: 13, fontWeight: 500 }}>Q:</span>
          {question}
        </h3>

        <div className="meta-badges">
          {isLoading && (
            <span className="badge badge-intent">
              <span className="status-dot connected" style={{ width: 6, height: 6 }} />
              Processing...
            </span>
          )}

          {error && (
            <span
              className="badge"
              style={{
                backgroundColor: (error.includes("can't answer") || error.includes('supported'))
                  ? 'var(--accent-amber-subtle)'
                  : 'var(--accent-red-subtle)',
                borderColor: (error.includes("can't answer") || error.includes('supported'))
                  ? 'var(--accent-amber-border)'
                  : 'var(--accent-red-border)',
                color: (error.includes("can't answer") || error.includes('supported'))
                  ? 'var(--accent-amber)'
                  : 'var(--accent-red)',
              }}
            >
              {(error.includes("can't answer") || error.includes('supported'))
                ? 'Unsupported Question'
                : 'Request Failed'}
            </span>
          )}

          {response && (
            <>
              {/* Intent pill */}
              <span className="badge badge-intent" title="Classified Intent">
                {response.intent.replace(/_/g, ' ')}
              </span>

              {/* Classifier Source: ONLY show Gemini if classified_by === 'gemini' */}
              {response.classified_by === 'gemini' ? (
                <span className="badge badge-gemini" title="Classified by Gemini">
                  <Sparkles size={11} />
                  Gemini
                </span>
              ) : response.classified_by === 'keywords' ? (
                <span className="badge badge-keywords" title="Keyword Rules Fallback">
                  <Cpu size={11} />
                  Keyword Fallback
                </span>
              ) : null}
            </>
          )}
        </div>
      </div>

      {/* Loading state skeleton */}
      {isLoading && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, padding: '8px 0' }}>
          <div className="kpi-skeleton" style={{ width: '80%', height: 18 }} />
          <div className="kpi-skeleton" style={{ width: '50%', height: 14 }} />
        </div>
      )}

      {/* Error / Unsupported state */}
      {error && (
        (error.includes("can't answer") || error.includes('supported')) ? (
          <div
            style={{
              padding: '14px 16px',
              backgroundColor: '#0d0d10',
              borderLeft: '3px solid var(--accent-amber)',
              borderRadius: '0 var(--radius-sm) var(--radius-sm) 0',
              display: 'flex',
              flexDirection: 'column',
              gap: 8,
            }}
          >
            <div
              style={{
                fontSize: 11,
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                color: 'var(--accent-amber)',
              }}
            >
              Supported Capabilities Notice
            </div>
            <div
              style={{
                fontSize: 13,
                color: 'var(--text-secondary)',
                lineHeight: 1.6,
                whiteSpace: 'pre-line',
              }}
            >
              {error}
            </div>
          </div>
        ) : (
          <div
            style={{
              padding: '12px 14px',
              backgroundColor: 'var(--accent-red-subtle)',
              border: '1px solid var(--accent-red-border)',
              borderRadius: 'var(--radius-sm)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: 12,
            }}
          >
            <div style={{ fontSize: 13, color: 'var(--accent-red)' }}>{error}</div>
            {onRetry && (
              <button
                onClick={() => onRetry(question)}
                className="chip-btn"
                style={{
                  color: 'var(--accent-red)',
                  borderColor: 'var(--accent-red-border)',
                  backgroundColor: 'transparent',
                }}
              >
                <RotateCcw size={12} />
                Retry
              </button>
            )}
          </div>
        )
      )}

      {/* Response Answer */}
      {response && (
        <>
          <div className="answer-box">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span className="answer-label">Assistant Answer</span>
              <button
                onClick={handleCopyAnswer}
                style={{
                  fontSize: 11,
                  color: 'var(--text-muted)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 4,
                  padding: '2px 6px',
                  borderRadius: 'var(--radius-xs)',
                }}
                title="Copy answer"
              >
                {copiedAnswer ? <Check size={12} color="var(--accent-green)" /> : <Copy size={12} />}
                <span>{copiedAnswer ? 'Copied' : 'Copy'}</span>
              </button>
            </div>
            <div className="answer-text">{response.answer}</div>
          </div>

          {/* Visualization (Charts) if appropriate */}
          {renderVisualization()}

          {/* Action buttons / Disclosures */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap', paddingTop: 4 }}>
            {/* SQL Disclosure */}
            {response.sql_used && (
              <button
                className="collapse-trigger"
                onClick={() => setShowSql(!showSql)}
                aria-expanded={showSql}
              >
                <Code2 size={13} />
                <span>{showSql ? 'Hide SQL Query' : 'View SQL Query'}</span>
                {showSql ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
              </button>
            )}

            {/* Supporting Data Disclosure */}
            {response.supporting_data && response.supporting_data.length > 0 && (
              <button
                className="collapse-trigger"
                onClick={() => setShowData(!showData)}
                aria-expanded={showData}
              >
                <TableIcon size={13} />
                <span>
                  {showData
                    ? 'Hide Raw Records'
                    : `View Supporting Records (${response.supporting_data.length})`}
                </span>
                {showData ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
              </button>
            )}
          </div>

          {/* Expanded SQL Code Box */}
          {showSql && response.sql_used && (
            <div className="code-box">
              <button
                onClick={handleCopySql}
                className="copy-btn"
                title="Copy SQL"
              >
                {copiedSql ? <Check size={12} color="var(--accent-green)" /> : <Copy size={12} />}
                <span>{copiedSql ? 'Copied' : 'Copy SQL'}</span>
              </button>
              <pre className="code-pre">{response.sql_used}</pre>
            </div>
          )}

          {/* Expanded Raw Records Table */}
          {showData && response.supporting_data && (
            <div style={{ paddingTop: 4 }}>
              <DataTable data={response.supporting_data} title="Underlying Result Dataset" />
            </div>
          )}
        </>
      )}
    </article>
  );
};
