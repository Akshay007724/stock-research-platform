import { useState, useEffect, useCallback } from 'react'
import clsx from 'clsx'
import { BarChart2, TrendingUp, Zap } from 'lucide-react'
import { SearchBar } from './components/SearchBar'
import { ThemeToggle } from './components/ThemeToggle'
import { AgentFeed } from './components/AgentFeed'
import { MCPGraph } from './components/MCPGraph'
import { RecommendationCard } from './components/RecommendationCard'
import { OverviewTab } from './components/tabs/OverviewTab'
import { DebateTab } from './components/tabs/DebateTab'
import { TechnicalTab } from './components/tabs/TechnicalTab'
import { NewsTab } from './components/tabs/NewsTab'
import { useAnalysis } from './hooks/useAnalysis'
import type { SentimentScore } from './types'

type Tab = 'overview' | 'debate' | 'technical' | 'news'

const TABS: { id: Tab; label: string }[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'debate', label: 'Bull vs Bear' },
  { id: 'technical', label: 'Technical' },
  { id: 'news', label: 'News' },
]

function useIsDark(): boolean {
  const [isDark, setIsDark] = useState(() => {
    if (typeof window === 'undefined') return true
    const stored = localStorage.getItem('theme')
    if (stored) return stored === 'dark'
    return window.matchMedia('(prefers-color-scheme: dark)').matches
  })

  useEffect(() => {
    const observer = new MutationObserver(() => {
      setIsDark(document.documentElement.classList.contains('dark'))
    })
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['class'],
    })
    return () => observer.disconnect()
  }, [])

  return isDark
}

function LoadingOverlay({ ticker }: { ticker: string | null }) {
  return (
    <div className="flex flex-col items-center justify-center gap-6 py-20 px-8 text-center">
      <div className="relative">
        <div className="w-16 h-16 rounded-full border-4 border-blue-500/20 border-t-blue-500 animate-spin" />
        <div className="absolute inset-0 flex items-center justify-center">
          <Zap className="w-6 h-6 text-blue-500" />
        </div>
      </div>
      <div>
        <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100 mb-1">
          Analyzing {ticker}
        </h2>
        <p className="text-sm text-gray-500 dark:text-gray-400 max-w-xs">
          Running multi-agent analysis pipeline. Watch the agent feed for live updates.
        </p>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 w-full max-w-lg">
        {['Market Research', 'Historical Analysis', 'News Sentiment', 'Bull vs Bear Debate'].map((label) => (
          <div
            key={label}
            className="flex flex-col items-center gap-2 bg-gray-50 dark:bg-gray-800/60 border border-gray-200 dark:border-gray-700 rounded-xl p-3"
          >
            <div className="w-6 h-6 rounded-full bg-blue-500/10 border-2 border-blue-500/30 border-t-blue-500 animate-spin" />
            <span className="text-[10px] font-medium text-gray-500 dark:text-gray-400 text-center leading-snug">
              {label}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

function EmptyState({ onSearch }: { onSearch: (ticker: string) => void }) {
  const exampleTickers = ['AAPL', 'NVDA', 'TSLA', 'MSFT']

  return (
    <div className="flex flex-col items-center justify-center gap-8 py-20 px-8 text-center">
      <div className="flex flex-col items-center gap-4">
        <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shadow-xl shadow-blue-500/20">
          <BarChart2 className="w-10 h-10 text-white" />
        </div>
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
            AI-Powered Stock Research
          </h2>
          <p className="text-gray-500 dark:text-gray-400 max-w-md leading-relaxed">
            Enter any stock ticker to trigger a multi-agent analysis pipeline. Our AI agents will
            research fundamentals, analyze technicals, debate bull vs bear cases, and deliver a
            weighted recommendation.
          </p>
        </div>
      </div>

      <div className="flex flex-col items-center gap-3">
        <p className="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider">
          Quick start with
        </p>
        <div className="flex gap-2 flex-wrap justify-center">
          {exampleTickers.map((t) => (
            <button
              key={t}
              onClick={() => onSearch(t)}
              className="px-4 py-2 rounded-xl text-sm font-semibold bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:bg-blue-50 dark:hover:bg-blue-900/20 hover:border-blue-300 dark:hover:border-blue-700 hover:text-blue-700 dark:hover:text-blue-300 transition-all duration-150 shadow-sm"
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 w-full max-w-2xl mt-2">
        {[
          {
            title: '8 Specialized Agents',
            desc: 'Market, Historical, News, Bull, Bear, Moderator, Recommender, Orchestrator',
            color: 'text-blue-500',
          },
          {
            title: 'Real-time Events',
            desc: 'Watch agents collaborate via Redis pub/sub with live SSE streaming',
            color: 'text-purple-500',
          },
          {
            title: 'Weighted Recommendation',
            desc: 'BUY/SELL/HOLD with composite score from technical, sentiment, fundamental & debate',
            color: 'text-green-500',
          },
        ].map((item) => (
          <div
            key={item.title}
            className="bg-white dark:bg-gray-800/60 border border-gray-200 dark:border-gray-700 rounded-xl p-4 text-left"
          >
            <h3 className={clsx('text-sm font-bold mb-1', item.color)}>{item.title}</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed">{item.desc}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

function ErrorBanner({ message, onDismiss }: { message: string; onDismiss: () => void }) {
  return (
    <div className="mx-4 my-3 flex items-start gap-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800/40 rounded-xl px-4 py-3">
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-red-700 dark:text-red-400">Analysis Failed</p>
        <p className="text-xs text-red-600 dark:text-red-500 mt-0.5 break-words">{message}</p>
      </div>
      <button
        onClick={onDismiss}
        className="flex-shrink-0 text-red-400 hover:text-red-600 dark:hover:text-red-300 transition-colors text-lg leading-none"
        aria-label="Dismiss error"
      >
        ×
      </button>
    </div>
  )
}

export default function App() {
  const isDark = useIsDark()
  const [activeTab, setActiveTab] = useState<Tab>('overview')
  const { result, loading, error, events, activeTicker, analyze, clearError, reset } = useAnalysis()

  const handleSearch = useCallback(
    (ticker: string) => {
      setActiveTab('overview')
      analyze(ticker)
    },
    [analyze],
  )

  // Switch to news tab automatically when news data arrives if nothing else selected
  useEffect(() => {
    if (result && activeTab === 'overview') {
      setActiveTab('overview')
    }
  }, [result])

  // Build a SentimentScore from news articles if we have a result
  const sentimentScore: SentimentScore | null = result
    ? (() => {
        const articles = result.news
        const total = articles.length || 1
        const positive = articles.filter((a) => a.sentiment_label === 'positive').length
        const negative = articles.filter((a) => a.sentiment_label === 'negative').length

        const raw = articles.reduce((sum, a) => sum + a.sentiment_score, 0) / total
        const overall = raw > 0.2 ? 'positive' : raw < -0.2 ? 'negative' : 'neutral'

        return {
          score: raw,
          signals: [
            positive > negative
              ? `${positive} positive vs ${negative} negative articles`
              : `${negative} negative vs ${positive} positive articles`,
          ],
          overall_sentiment: overall,
          news_volume: articles.length,
          key_themes: [],
        }
      })()
    : null

  return (
    <div className="flex flex-col h-screen bg-white dark:bg-gray-950 overflow-hidden">
      {/* ── Header ─────────────────────────────────────────────────────── */}
      <header className="flex-shrink-0 flex items-center gap-4 px-4 py-3 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 shadow-sm z-10">
        {/* Logo */}
        <div className="flex items-center gap-2 flex-shrink-0">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
            <TrendingUp className="w-4.5 h-4.5 text-white" style={{ width: 18, height: 18 }} />
          </div>
          <span className="font-bold text-sm text-gray-900 dark:text-gray-100 hidden sm:block whitespace-nowrap">
            Stock<span className="text-blue-500">AI</span>
          </span>
        </div>

        {/* Search bar (centered) */}
        <div className="flex-1 flex justify-center">
          <SearchBar onSearch={handleSearch} loading={loading} />
        </div>

        {/* Theme toggle + ticker badge */}
        <div className="flex items-center gap-2 flex-shrink-0">
          {activeTicker && result && (
            <span className="hidden sm:flex items-center gap-1.5 px-3 py-1 bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 text-xs font-bold rounded-full border border-blue-200 dark:border-blue-800">
              <span
                className={clsx(
                  'w-1.5 h-1.5 rounded-full',
                  loading ? 'bg-blue-500 animate-pulse' : 'bg-green-500',
                )}
              />
              {activeTicker}
            </span>
          )}
          <ThemeToggle />
        </div>
      </header>

      {/* ── Error Banner ──────────────────────────────────────────────── */}
      {error && <ErrorBanner message={error} onDismiss={clearError} />}

      {/* ── Main Content Area ─────────────────────────────────────────── */}
      <div className="flex flex-1 min-h-0 overflow-hidden">
        {/* Left: Agent Feed (280px fixed) */}
        <div className="flex-shrink-0 w-[280px] min-h-0 overflow-hidden">
          <AgentFeed events={events} loading={loading} />
        </div>

        {/* Center: Main Analysis Panel */}
        <div className="flex-1 min-w-0 min-h-0 flex flex-col overflow-hidden">
          {/* Tabs */}
          {result && (
            <div className="flex-shrink-0 flex items-center gap-0.5 px-4 py-2 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800">
              {TABS.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={clsx(
                    'px-4 py-2 rounded-lg text-sm font-medium transition-all duration-150',
                    activeTab === tab.id
                      ? 'bg-blue-600 text-white shadow-sm'
                      : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-gray-200',
                  )}
                >
                  {tab.label}
                </button>
              ))}

              {/* Ticker info inline */}
              {result && (
                <div className="ml-auto flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
                  <span className="font-semibold text-gray-700 dark:text-gray-300">
                    {result.market_data.name || result.ticker}
                  </span>
                  <span
                    className={clsx(
                      'font-bold',
                      result.market_data.change_pct >= 0
                        ? 'text-green-600 dark:text-green-400'
                        : 'text-red-600 dark:text-red-400',
                    )}
                  >
                    ${result.market_data.price.toFixed(2)}{' '}
                    {result.market_data.change_pct >= 0 ? '+' : ''}
                    {result.market_data.change_pct.toFixed(2)}%
                  </span>
                  <button
                    onClick={reset}
                    className="px-2 py-1 rounded-lg border border-gray-200 dark:border-gray-700 text-xs hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                  >
                    Clear
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Tab content / loading / empty */}
          <div className="flex-1 min-h-0 overflow-y-auto p-4">
            {loading && !result && <LoadingOverlay ticker={activeTicker} />}

            {!loading && !result && !error && <EmptyState onSearch={handleSearch} />}

            {result && (
              <>
                {activeTab === 'overview' && <OverviewTab result={result} isDark={isDark} />}
                {activeTab === 'debate' && <DebateTab debate={result.debate} />}
                {activeTab === 'technical' && <TechnicalTab result={result} isDark={isDark} />}
                {activeTab === 'news' && sentimentScore && (
                  <NewsTab articles={result.news} sentiment={sentimentScore} />
                )}
              </>
            )}
          </div>
        </div>

        {/* Right: MCP Graph (320px fixed) */}
        <div className="flex-shrink-0 w-[320px] min-h-0 overflow-hidden">
          <MCPGraph loading={loading} activeTicker={activeTicker} />
        </div>
      </div>

      {/* ── Recommendation Card (full-width bottom strip) ────────────── */}
      {result && <RecommendationCard recommendation={result.recommendation} />}
    </div>
  )
}
