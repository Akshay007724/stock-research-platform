import { ArrowDown, ArrowUp, Minus, Printer, Target, TrendingDown, TrendingUp } from 'lucide-react'
import { useState } from 'react'
import clsx from 'clsx'
import type { Recommendation } from '../types'

function GaugeMini({ value, label }: { value: number; label: string }) {
  const clamped = Math.max(0, Math.min(100, value))
  const color = clamped >= 65 ? 'bg-green-500' : clamped >= 50 ? 'bg-yellow-500' : 'bg-red-500'

  return (
    <div className="flex flex-col gap-1 flex-1 min-w-[80px]">
      <div className="flex justify-between items-center">
        <span className="text-xs text-gray-500 dark:text-gray-400">{label}</span>
        <span className="text-xs font-semibold text-gray-700 dark:text-gray-300">{clamped.toFixed(0)}</span>
      </div>
      <div className="w-full h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
        <div
          className={clsx('h-full rounded-full transition-all duration-500', color)}
          style={{ width: `${clamped}%` }}
        />
      </div>
    </div>
  )
}

function CircularGauge({ value }: { value: number }) {
  const clamped = Math.max(0, Math.min(100, value))
  const radius = 36
  const circumference = 2 * Math.PI * radius
  const strokeDashoffset = circumference - (clamped / 100) * circumference
  const color = clamped >= 65 ? '#22c55e' : clamped >= 50 ? '#eab308' : '#ef4444'

  return (
    <div className="relative w-24 h-24">
      <svg className="w-24 h-24 -rotate-90" viewBox="0 0 88 88">
        <circle cx="44" cy="44" r={radius} fill="none" stroke="currentColor" strokeWidth="8" className="text-gray-200 dark:text-gray-700" />
        <circle
          cx="44"
          cy="44"
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="8"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          className="transition-all duration-700"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-xl font-bold text-gray-900 dark:text-gray-100">{clamped.toFixed(0)}</span>
        <span className="text-[10px] text-gray-400">/ 100</span>
      </div>
    </div>
  )
}

interface RecommendationCardProps {
  recommendation: Recommendation
}

export function RecommendationCard({ recommendation: rec }: RecommendationCardProps) {
  const [portfolioSize, setPortfolioSize] = useState('')

  const allocationAmount = portfolioSize
    ? ((parseFloat(portfolioSize) || 0) * rec.allocation_pct) / 100
    : null

  function handlePrint() {
    window.print()
  }

  const actionConfig = {
    BUY: {
      bg: 'bg-green-500',
      text: 'text-white',
      border: 'border-green-500',
      icon: <TrendingUp className="w-6 h-6" />,
      light: 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800',
    },
    SELL: {
      bg: 'bg-red-500',
      text: 'text-white',
      border: 'border-red-500',
      icon: <TrendingDown className="w-6 h-6" />,
      light: 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800',
    },
    HOLD: {
      bg: 'bg-yellow-500',
      text: 'text-white',
      border: 'border-yellow-500',
      icon: <Minus className="w-6 h-6" />,
      light: 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800',
    },
  }

  const config = actionConfig[rec.action]

  return (
    <div className="bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-800 px-6 py-4 print:break-before-page">
      <div className="flex flex-wrap gap-6 items-start">
        {/* Action + Gauge */}
        <div className="flex items-center gap-4">
          <div
            className={clsx(
              'flex items-center gap-3 px-6 py-3 rounded-2xl font-bold text-2xl',
              config.bg,
              config.text,
            )}
          >
            {config.icon}
            {rec.action}
          </div>
          <CircularGauge value={rec.composite_score} />
          <div className="flex flex-col gap-0.5">
            <span className="text-xs text-gray-400">Confidence</span>
            <span className="text-2xl font-bold text-gray-900 dark:text-gray-100">{rec.composite_score.toFixed(1)}%</span>
            <span
              className={clsx(
                'text-xs font-semibold px-2 py-0.5 rounded-full border w-fit',
                rec.risk_level === 'HIGH'
                  ? 'bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 border-red-200 dark:border-red-800'
                  : rec.risk_level === 'LOW'
                  ? 'bg-green-50 dark:bg-green-900/20 text-green-600 dark:text-green-400 border-green-200 dark:border-green-800'
                  : 'bg-yellow-50 dark:bg-yellow-900/20 text-yellow-600 dark:text-yellow-400 border-yellow-200 dark:border-yellow-800',
              )}
            >
              {rec.risk_level} RISK
            </span>
          </div>
        </div>

        {/* Score breakdown */}
        <div className="flex-1 min-w-[300px]">
          <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">Score Breakdown</p>
          <div className="flex flex-wrap gap-x-4 gap-y-3">
            <GaugeMini value={rec.technical_score} label="Technical" />
            <GaugeMini value={rec.sentiment_score} label="Sentiment" />
            <GaugeMini value={rec.fundamental_score} label="Fundamental" />
            <GaugeMini value={rec.debate_score} label="Debate" />
          </div>
        </div>

        {/* Targets */}
        <div className="flex flex-col gap-2 min-w-[140px]">
          <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Price Targets</p>
          {rec.target_price && (
            <div className="flex items-center gap-2">
              <ArrowUp className="w-3.5 h-3.5 text-green-500" />
              <span className="text-xs text-gray-500">Target</span>
              <span className="text-sm font-bold text-green-600 dark:text-green-400">${rec.target_price.toFixed(2)}</span>
            </div>
          )}
          {rec.stop_loss && (
            <div className="flex items-center gap-2">
              <ArrowDown className="w-3.5 h-3.5 text-red-500" />
              <span className="text-xs text-gray-500">Stop Loss</span>
              <span className="text-sm font-bold text-red-600 dark:text-red-400">${rec.stop_loss.toFixed(2)}</span>
            </div>
          )}
          <div className="flex items-center gap-2">
            <Target className="w-3.5 h-3.5 text-blue-500" />
            <span className="text-xs text-gray-500">Allocation</span>
            <span className="text-sm font-bold text-blue-600 dark:text-blue-400">{rec.allocation_pct}%</span>
          </div>
        </div>

        {/* Reasoning */}
        <div className="flex-1 min-w-[240px]">
          <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">Investment Rationale</p>
          <ul className="space-y-1">
            {rec.reasoning.map((r, i) => (
              <li key={i} className="flex items-start gap-2 text-xs text-gray-700 dark:text-gray-300">
                <span className="text-blue-500 font-bold flex-shrink-0 mt-0.5">→</span>
                {r}
              </li>
            ))}
          </ul>
        </div>

        {/* Portfolio calculator */}
        <div className="flex flex-col gap-2 min-w-[180px]">
          <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Portfolio Calculator</p>
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm">$</span>
            <input
              type="number"
              value={portfolioSize}
              onChange={(e) => setPortfolioSize(e.target.value)}
              placeholder="Portfolio size"
              className="w-full pl-7 pr-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          {allocationAmount !== null && allocationAmount > 0 && (
            <div className="text-xs text-gray-600 dark:text-gray-400">
              Suggested allocation:{' '}
              <span className="font-bold text-blue-600 dark:text-blue-400">
                ${allocationAmount.toLocaleString('en-US', { maximumFractionDigits: 0 })}
              </span>{' '}
              ({rec.allocation_pct}%)
            </div>
          )}
          {allocationAmount !== null && allocationAmount === 0 && (
            <div className="text-xs text-gray-500">No allocation recommended</div>
          )}
        </div>

        {/* Export */}
        <button
          onClick={handlePrint}
          className="flex items-center gap-2 px-3 py-2 text-xs font-semibold rounded-lg border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
        >
          <Printer className="w-3.5 h-3.5" />
          Export
        </button>
      </div>
    </div>
  )
}
