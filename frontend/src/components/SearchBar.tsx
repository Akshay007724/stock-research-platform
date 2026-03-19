import clsx from 'clsx'
import { ChevronDown, Search, TrendingUp, X } from 'lucide-react'
import { type FormEvent, useEffect, useRef, useState } from 'react'
import { getTickers, type TickerInfo } from '../lib/api'

const POPULAR_TICKERS = ['AAPL', 'TSLA', 'NVDA', 'MSFT', 'GOOGL', 'AMZN', 'META', 'SPY']

interface SearchBarProps {
  onSearch: (ticker: string) => void
  loading: boolean
}

export function SearchBar({ onSearch, loading }: SearchBarProps) {
  const [value, setValue] = useState('')
  const [query, setQuery] = useState('')
  const [allTickers, setAllTickers] = useState<TickerInfo[]>([])
  const [filtered, setFiltered] = useState<TickerInfo[]>([])
  const [showDropdown, setShowDropdown] = useState(false)
  const [highlighted, setHighlighted] = useState(0)
  const containerRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Load all tickers once on mount
  useEffect(() => {
    getTickers().then(setAllTickers).catch(() => {})
  }, [])

  // Filter locally on every keystroke for speed
  useEffect(() => {
    const q = query.trim().toLowerCase()
    if (!q) {
      setFiltered([])
      setShowDropdown(false)
      return
    }
    const results = allTickers.filter(
      (t) =>
        t.ticker.toLowerCase().startsWith(q) ||
        t.name.toLowerCase().includes(q) ||
        t.sector.toLowerCase().includes(q),
    )
    setFiltered(results.slice(0, 12))
    setShowDropdown(results.length > 0)
    setHighlighted(0)
  }, [query, allTickers])

  // Close dropdown on outside click
  useEffect(() => {
    function handler(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setShowDropdown(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  function selectTicker(ticker: string) {
    setValue(ticker)
    setQuery('')
    setShowDropdown(false)
    onSearch(ticker)
  }

  function handleInput(e: React.ChangeEvent<HTMLInputElement>) {
    const raw = e.target.value.toUpperCase()
    setValue(raw)
    setQuery(raw)
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    const ticker = value.trim().toUpperCase()
    if (ticker) {
      setShowDropdown(false)
      onSearch(ticker)
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (!showDropdown) return
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setHighlighted((h) => Math.min(h + 1, filtered.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setHighlighted((h) => Math.max(h - 1, 0))
    } else if (e.key === 'Enter') {
      e.preventDefault()
      if (filtered[highlighted]) {
        selectTicker(filtered[highlighted].ticker)
      }
    } else if (e.key === 'Escape') {
      setShowDropdown(false)
    }
  }

  function handleQuickSelect(ticker: string) {
    setValue(ticker)
    setQuery('')
    setShowDropdown(false)
    onSearch(ticker)
  }

  const sectorColors: Record<string, string> = {
    Technology: 'text-blue-500',
    Financials: 'text-green-500',
    Healthcare: 'text-red-400',
    Energy: 'text-orange-400',
    'Consumer Discretionary': 'text-yellow-500',
    'Consumer Staples': 'text-lime-500',
    'Communication Services': 'text-purple-400',
    Industrials: 'text-gray-400',
    Utilities: 'text-teal-400',
    'Real Estate': 'text-pink-400',
    Materials: 'text-amber-400',
    ETF: 'text-indigo-400',
  }

  return (
    <div className="flex flex-col items-center gap-3 w-full max-w-2xl">
      <form onSubmit={handleSubmit} className="flex w-full gap-2">
        <div className="relative flex-1" ref={containerRef}>
          <TrendingUp className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 z-10" />
          <input
            ref={inputRef}
            type="text"
            value={value}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            onFocus={() => { if (filtered.length > 0) setShowDropdown(true) }}
            placeholder="Search ticker or company name…"
            disabled={loading}
            autoComplete="off"
            className={clsx(
              'w-full pl-10 pr-8 py-2.5 rounded-xl border text-sm font-medium',
              'bg-white dark:bg-gray-800',
              'border-gray-200 dark:border-gray-700',
              'text-gray-900 dark:text-gray-100',
              'placeholder-gray-400 dark:placeholder-gray-500',
              'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
              'disabled:opacity-50 disabled:cursor-not-allowed',
              'transition-all duration-150',
            )}
            maxLength={20}
          />
          {value && !loading && (
            <button
              type="button"
              onClick={() => { setValue(''); setQuery(''); setShowDropdown(false); inputRef.current?.focus() }}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
          {!value && (
            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400 pointer-events-none" />
          )}

          {/* Dropdown */}
          {showDropdown && (
            <div className="absolute top-full left-0 right-0 mt-1 z-50 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-xl max-h-72 overflow-y-auto">
              {filtered.map((t, i) => (
                <button
                  key={t.ticker}
                  type="button"
                  onMouseDown={() => selectTicker(t.ticker)}
                  className={clsx(
                    'w-full flex items-center gap-3 px-3 py-2 text-left text-sm transition-colors',
                    i === highlighted
                      ? 'bg-blue-50 dark:bg-blue-900/30'
                      : 'hover:bg-gray-50 dark:hover:bg-gray-700/50',
                  )}
                >
                  <span className="font-bold text-gray-900 dark:text-gray-100 w-16 shrink-0">
                    {t.ticker}
                  </span>
                  <span className="flex-1 text-gray-600 dark:text-gray-400 truncate">{t.name}</span>
                  <span className={clsx('text-xs font-medium shrink-0', sectorColors[t.sector] || 'text-gray-400')}>
                    {t.sector}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>

        <button
          type="submit"
          disabled={loading || !value.trim()}
          className={clsx(
            'flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold',
            'bg-blue-600 hover:bg-blue-700 active:bg-blue-800',
            'text-white',
            'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2',
            'disabled:opacity-50 disabled:cursor-not-allowed',
            'transition-all duration-150',
            'min-w-[100px] justify-center',
          )}
        >
          {loading ? (
            <>
              <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              <span>Analyzing</span>
            </>
          ) : (
            <>
              <Search className="w-4 h-4" />
              <span>Analyze</span>
            </>
          )}
        </button>
      </form>

      {/* Quick select chips */}
      <div className="flex flex-wrap gap-1.5 justify-center">
        {POPULAR_TICKERS.map((ticker) => (
          <button
            key={ticker}
            onClick={() => handleQuickSelect(ticker)}
            disabled={loading}
            className={clsx(
              'px-3 py-1 rounded-full text-xs font-semibold',
              'bg-gray-100 dark:bg-gray-800',
              'text-gray-600 dark:text-gray-400',
              'hover:bg-blue-50 dark:hover:bg-blue-900/30 hover:text-blue-600 dark:hover:text-blue-400',
              'border border-gray-200 dark:border-gray-700',
              'disabled:opacity-50 disabled:cursor-not-allowed',
              'transition-all duration-100',
            )}
          >
            {ticker}
          </button>
        ))}
      </div>
    </div>
  )
}
