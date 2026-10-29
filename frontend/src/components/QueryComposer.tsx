import React, { useRef, useEffect } from 'react';
import {
  ArrowUp,
  CornerDownLeft,
  Sparkles,
  Loader2,
  TrendingUp,
  Package,
  MapPin,
  CalendarRange,
} from 'lucide-react';

interface QueryComposerProps {
  question: string;
  onChangeQuestion: (val: string) => void;
  onSubmit: () => void;
  isLoading: boolean;
  onSelectSuggestion: (suggestion: string) => void;
}

interface ExamplePrompt {
  id: string;
  text: string;
  category: string;
  icon: React.ReactNode;
}

const EXAMPLE_SUGGESTIONS: ExamplePrompt[] = [
  {
    id: 'rev',
    text: 'What is our total revenue?',
    category: 'Total Revenue',
    icon: <TrendingUp size={13} />,
  },
  {
    id: 'prod',
    text: 'Which product earned the most revenue?',
    category: 'Product Ranking',
    icon: <Package size={13} />,
  },
  {
    id: 'trend',
    text: 'Show monthly revenue trends.',
    category: 'Monthly Trends',
    icon: <Sparkles size={13} />,
  },
  {
    id: 'reg',
    text: 'Which region had the highest sales?',
    category: 'Regional Sales',
    icon: <MapPin size={13} />,
  },
  {
    id: 'comp',
    text: 'Compare revenue between April and May 2026.',
    category: 'Period Comparison',
    icon: <CalendarRange size={13} />,
  },
];

export const QueryComposer: React.FC<QueryComposerProps> = ({
  question,
  onChangeQuestion,
  onSubmit,
  isLoading,
  onSelectSuggestion,
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea based on content
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(
        160,
        Math.max(52, textareaRef.current.scrollHeight)
      )}px`;
    }
  }, [question]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!isLoading && question.trim().length > 0) {
        onSubmit();
      }
    }
  };

  const handleCardClick = (suggestion: string) => {
    // Populate composer, do NOT submit automatically
    onSelectSuggestion(suggestion);
    if (textareaRef.current) {
      textareaRef.current.focus();
    }
  };

  const isSubmitDisabled = isLoading || question.trim().length === 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      {/* Composer Card */}
      <div className="composer-card">
        <textarea
          ref={textareaRef}
          className="composer-textarea"
          placeholder="Ask a question about sales revenue, top products, regions, or monthly trends..."
          value={question}
          onChange={(e) => onChangeQuestion(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isLoading}
          rows={2}
          aria-label="Ask a business analytics question"
        />

        <div className="composer-footer">
          <div className="composer-hints">
            <span>Press</span>
            <span className="keyboard-badge">
              <CornerDownLeft size={10} style={{ marginRight: 2 }} /> Enter
            </span>
            <span>to ask</span>
            <span style={{ color: 'var(--text-subtle)' }}>•</span>
            <span className="keyboard-badge">Shift + Enter</span>
            <span>new line</span>
          </div>

          <button
            type="button"
            className="composer-submit-btn"
            onClick={onSubmit}
            disabled={isSubmitDisabled}
            aria-label="Submit question"
          >
            {isLoading ? (
              <>
                <Loader2 size={13} className="spin" />
                <span>Classifying...</span>
              </>
            ) : (
              <>
                <span>Ask Analytics</span>
                <ArrowUp size={13} />
              </>
            )}
          </button>
        </div>
      </div>

      {/* Example Question Cards Grid */}
      <div className="example-cards-section">
        <div className="example-cards-header">
          <span>Supported Query Examples</span>
          <span style={{ color: 'var(--text-muted)' }}>Click to populate composer</span>
        </div>
        <div className="example-cards-grid">
          {EXAMPLE_SUGGESTIONS.map((item) => (
            <button
              key={item.id}
              type="button"
              className="example-query-card"
              onClick={() => handleCardClick(item.text)}
              title="Click to populate composer"
            >
              <div className="example-card-icon">{item.icon}</div>
              <div className="example-card-content">
                <span className="example-card-title">{item.text}</span>
                <span className="example-card-category">{item.category}</span>
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};
