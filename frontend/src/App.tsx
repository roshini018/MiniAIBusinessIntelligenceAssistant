import { useState, useEffect, useCallback } from 'react';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { KPISection } from './components/KPISection';
import { QueryComposer } from './components/QueryComposer';
import { Conversation } from './components/Conversation';
import { Toast } from './components/Toast';
import { fetchHealth, fetchKpis, askQuestion } from './api/client';
import { ChartsSection } from './components/ChartsSection';
import type { KPIResponse, QueryHistoryItem } from './types/bi';

export function App() {
  const [activeTab, setActiveTab] = useState<'overview' | 'ask'>('overview');
  const [isBackendConnected, setIsBackendConnected] = useState<boolean>(false);
  const [isCheckingHealth, setIsCheckingHealth] = useState<boolean>(false);

  const [kpis, setKpis] = useState<KPIResponse | null>(null);
  const [isLoadingKpis, setIsLoadingKpis] = useState<boolean>(true);
  const [kpiError, setKpiError] = useState<string | null>(null);

  const [question, setQuestion] = useState<string>('');
  const [isAsking, setIsAsking] = useState<boolean>(false);
  const [history, setHistory] = useState<QueryHistoryItem[]>([]);

  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState<boolean>(false);

  const showToast = useCallback((msg: string) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage((current) => (current === msg ? null : current));
    }, 2500);
  }, []);

  // Health check
  const checkHealth = useCallback(async () => {
    setIsCheckingHealth(true);
    try {
      const res = await fetchHealth();
      setIsBackendConnected(Boolean(res && res.status === 'ok'));
    } catch {
      setIsBackendConnected(false);
    } finally {
      setIsCheckingHealth(false);
    }
  }, []);

  // Load KPIs
  const loadKpis = useCallback(async () => {
    setIsLoadingKpis(true);
    setKpiError(null);
    try {
      const data = await fetchKpis();
      setKpis(data);
      setIsBackendConnected(true);
    } catch (err: any) {
      setKpiError(err?.message || 'Failed to fetch KPIs');
    } finally {
      setIsLoadingKpis(false);
    }
  }, []);

  // Initial setup and periodic health monitoring
  useEffect(() => {
    checkHealth();
    loadKpis();

    const interval = setInterval(() => {
      checkHealth();
    }, 15000);

    return () => clearInterval(interval);
  }, [checkHealth, loadKpis]);

  // Handle Question Submission
  const handleAsk = async (queryText?: string) => {
    const textToAsk = (queryText ?? question).trim();
    if (!textToAsk || isAsking) return;

    const queryId = `query_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`;
    const newItem: QueryHistoryItem = {
      id: queryId,
      timestamp: new Date(),
      question: textToAsk,
      isLoading: true,
    };

    // Prepend or append to history - prepending shows newest results at top
    setHistory((prev) => [newItem, ...prev]);
    if (!queryText) {
      setQuestion('');
    }
    setIsAsking(true);

    try {
      const response = await askQuestion(textToAsk);
      setHistory((prev) =>
        prev.map((item) =>
          item.id === queryId
            ? { ...item, isLoading: false, response }
            : item
        )
      );
      setIsBackendConnected(true);
    } catch (err: any) {
      const errorMsg = err?.message || 'Error occurred while processing question.';
      setHistory((prev) =>
        prev.map((item) =>
          item.id === queryId
            ? { ...item, isLoading: false, error: errorMsg }
            : item
        )
      );
    } finally {
      setIsAsking(false);
    }
  };

  const handleRetry = (retryQuestion: string) => {
    handleAsk(retryQuestion);
  };

  const handleSelectSuggestion = (suggestion: string) => {
    // Only populates the composer, does not submit automatically
    setQuestion(suggestion);
    showToast('Example query inserted into composer');
  };

  const handleClearHistory = () => {
    setHistory([]);
    showToast('Started new conversation session');
  };

  // Close mobile drawer on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && mobileMenuOpen) {
        setMobileMenuOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [mobileMenuOpen]);

  // Prevent background scrolling while mobile drawer is open
  useEffect(() => {
    if (mobileMenuOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [mobileMenuOpen]);

  return (
    <div className="app-layout">
      {/* Mobile Drawer Backdrop */}
      <div
        className={`sidebar-backdrop ${mobileMenuOpen ? 'open' : ''}`}
        onClick={() => setMobileMenuOpen(false)}
        aria-hidden="true"
      />

      {/* Left Sidebar */}
      <Sidebar
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        isBackendConnected={isBackendConnected}
        onRefreshHealth={checkHealth}
        isCheckingHealth={isCheckingHealth}
        isOpenOnMobile={mobileMenuOpen}
        onCloseMobile={() => setMobileMenuOpen(false)}
        ordersCounted={kpis?.orders_counted}
        timeframeLabel={kpis?.timeframe?.label}
        isLoadingMetadata={isLoadingKpis}
      />

      {/* Main Content Workspace */}
      <div className="main-wrapper">
        <main className="content-container">
          {/* Header with page-specific titles */}
          {activeTab === 'overview' ? (
            <Header
              isBackendConnected={isBackendConnected}
              isMobileMenuOpen={mobileMenuOpen}
              onToggleMobileMenu={() => setMobileMenuOpen(!mobileMenuOpen)}
              title="Business Dashboard"
              description="Executive overview of enterprise sales performance, monthly revenue trends, and product & regional breakdowns."
              breadcrumb="Sales Workspace / Overview"
            />
          ) : (
            <Header
              isBackendConnected={isBackendConnected}
              isMobileMenuOpen={mobileMenuOpen}
              onToggleMobileMenu={() => setMobileMenuOpen(!mobileMenuOpen)}
              title="Ask Analytics"
              description="Ask questions in natural language about your sales data. Queries are classified with Gemini and executed deterministically against SQLite."
              breadcrumb="Sales Workspace / Ask Analytics"
            />
          )}

          {/* Tab 1: Overview — Business Performance Dashboard */}
          {activeTab === 'overview' && (
            <>
              {/* Four KPI cards in one row on desktop */}
              <section aria-label="Key Performance Indicators">
                <KPISection
                  kpis={kpis}
                  isLoading={isLoadingKpis}
                  error={kpiError}
                  onRetry={loadKpis}
                />
              </section>

              {/* Performance Breakdown: Monthly trend + Product & Region + Insights */}
              <section aria-label="Analytics Charts">
                <ChartsSection />
              </section>
            </>
          )}

          {/* Tab 2: Ask Analytics — Dedicated AI Query Workspace */}
          {activeTab === 'ask' && (
            <>
              {/* Prominent Question Composer & Example Chips */}
              <section aria-label="Analytics Query Composer">
                <QueryComposer
                  question={question}
                  onChangeQuestion={setQuestion}
                  onSubmit={() => handleAsk()}
                  isLoading={isAsking}
                  onSelectSuggestion={handleSelectSuggestion}
                />
              </section>

              {/* Query Results / Conversation Stream */}
              <section aria-label="Analytics Results Stream">
                <Conversation
                  history={history}
                  onClearHistory={handleClearHistory}
                  onRetry={handleRetry}
                  onNotify={showToast}
                />
              </section>
            </>
          )}
        </main>
      </div>

      {/* Subtle Toast Feedback */}
      <Toast message={toastMessage} />
    </div>
  );
}

export default App;
