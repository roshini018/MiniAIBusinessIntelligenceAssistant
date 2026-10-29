import React from 'react';
import { MessageSquare, Trash2, HelpCircle } from 'lucide-react';
import type { QueryHistoryItem } from '../types/bi';
import { ResultCard } from './ResultCard';

interface ConversationProps {
  history: QueryHistoryItem[];
  onClearHistory: () => void;
  onRetry: (question: string) => void;
  onNotify: (message: string) => void;
}

export const Conversation: React.FC<ConversationProps> = ({
  history,
  onClearHistory,
  onRetry,
  onNotify,
}) => {
  if (history.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-icon-box">
          <HelpCircle size={16} />
        </div>
        <div className="empty-title">Ready for your query</div>
        <p className="empty-desc">
          Enter any business intelligence question above or pick an example prompt to view instant verified results.
        </p>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div className="section-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <MessageSquare size={14} style={{ color: 'var(--text-muted)' }} />
          <h2 className="section-title">Session Query Stream ({history.length})</h2>
        </div>
        <button
          className="clear-btn"
          onClick={onClearHistory}
          title="Reset current conversation stream"
        >
          <Trash2 size={13} />
          <span>New Session</span>
        </button>
      </div>

      <div className="conversation-stream">
        {history.map((item) => (
          <ResultCard
            key={item.id}
            item={item}
            onRetry={onRetry}
            onNotify={onNotify}
          />
        ))}
      </div>
    </div>
  );
};
