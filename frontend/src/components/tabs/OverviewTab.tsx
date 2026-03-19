import { Activity, BarChart2, DollarSign, TrendingDown, TrendingUp } from 'lucide-react'
import clsx from 'clsx'
import { CandlestickChart } from '../charts/CandlestickChart'
import type { AnalysisResult } from '../../types'

function formatMarketCap(val: number | null): string {
  if (!val) return 'N/A'
  if (val >= 1e12) return `$${(val / 1e12).toFixed(2)}T`
  if (val >= 1e9) return `$${(val / 1e9).toFixed(2)}B`
  if (val >= 1e6) return `$${(val / 1e6).toFixed(2)}M`
  return `$${val.toFixed(0)}`
}

function formatVolume(val: number): string {
  if (val >= 1e9) return `${(val / 1e9).toFixed(2)}B`
  if (val >= 1e6) return `${(val / 1e6).toFixed(2)}M`
  if (val >= 1e3) return `${(val / 1e3).toFixed(1)}K`
  return `${val}`
}

interface MetricCardProps {
  label: string
  value: string
  subValue?: string
  positive?: boolean
  negative?: boolean
  icon?: React.ReactNode
}

function MetricCard({ label, value, subValue, positive, negative, icon }: MetricCardProps) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 px-4 py-3">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-medium text-gray-500 dark:text-gray-400">{label}</span>
        {icon && <span className="text-gray-400">{icon}</span>}
      </div>
      <div className="text-lg font-bold text-gray-900 dark:text-gray-100">{value}</div>
      {subValue && (
        <div
          className={clsx(
            'text-xs font-semibold mt-0.5',
            positive && 'text-green-600 dark:text-green-400',
            negative && 'text-red-600 dark:text-red-400',
            !positive && !negative && 'text-gray-400',
          )}
        >
          {subValue}
        </div>
      )}
    </div>
  )
}

interface OverviewTabProps {
  result: AnalysisResult
  isDark: boolean
}

export function OverviewTab({ result, isDark }: OverviewTabProps) {
  const { market_data: md, ohlcv, indicators } = result

  const isPositive = md.change_pct >= 0
  const priceSubValue = `${isPositive ? '+' : ''}${md.change_pct.toFixed(2)}% ${isPositive ? '▲' : '▼'} today`

  // Build EMA data for chart overlays
  const emaData = {
    ema_9: ohlcv
      .filter((_, i) => i >= 8)
      .map((bar, i) => ({
        time: bar.timestamp,
        value: indicators.ema_9 || 0, // simplified - in production compute per bar
      })),
  }
  // Actually pass only the final indicator values since we don't have per-bar EMA from backend
  const simplifiedEmaData = undefined

  return (
    <div className="space-y-4">
      {/* Metric cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-6 gap-3">
        <MetricCard
          label="Price"
          value={`$${md.price.toFixed(2)}`}
          subValue={priceSubValue}
          positive={isPositive}
          negative={!isPositive}
          icon={<DollarSign className="w-3.5 h-3.5" />}
        />
        <MetricCard
          label="Change"
          value={`${md.change >= 0 ? '+' : ''}$${md.change.toFixed(2)}`}
          subValue={`${md.change_pct >= 0 ? '+' : ''}${md.change_pct.toFixed(2)}%`}
          positive={md.change >= 0}
          negative={md.change < 0}
          icon={md.change >= 0 ? <TrendingUp className="w-3.5 h-3.5" /> : <TrendingDown className="w-3.5 h-3.5" />}
        />
        <MetricCard
          label="Volume"
          value={formatVolume(md.volume)}
          icon={<BarChart2 className="w-3.5 h-3.5" />}
        />
        <MetricCard
          label="Market Cap"
          value={formatMarketCap(md.market_cap)}
          icon={<Activity className="w-3.5 h-3.5" />}
        />
        <MetricCard
          label="P/E Ratio"
          value={md.pe_ratio ? md.pe_ratio.toFixed(1) : 'N/A'}
          subValue={md.eps ? `EPS: $${md.eps.toFixed(2)}` : undefined}
        />
        <MetricCard
          label="Beta"
          value={md.beta ? md.beta.toFixed(2) : 'N/A'}
          subValue={
            md.beta
              ? md.beta > 1.5
                ? 'High volatility'
                : md.beta < 0.8
                ? 'Low volatility'
                : 'Market neutral'
              : undefined
          }
        />
      </div>

      {/* 52-week range */}
      {md.week_52_high && md.week_52_low && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 px-4 py-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">52-Week Range</span>
            <div className="flex gap-3 text-xs">
              <span className="text-gray-500">Low: <span className="font-semibold text-gray-700 dark:text-gray-300">${md.week_52_low.toFixed(2)}</span></span>
              <span className="text-gray-500">High: <span className="font-semibold text-gray-700 dark:text-gray-300">${md.week_52_high.toFixed(2)}</span></span>
            </div>
          </div>
          <div className="relative h-2 bg-gray-200 dark:bg-gray-700 rounded-full">
            {(() => {
              const range = md.week_52_high - md.week_52_low
              const position = range > 0 ? ((md.price - md.week_52_low) / range) * 100 : 50
              const clamped = Math.max(0, Math.min(100, position))
              return (
                <>
                  <div
                    className="absolute top-0 left-0 h-full bg-gradient-to-r from-red-400 via-yellow-400 to-green-400 rounded-full"
                    style={{ width: `${clamped}%` }}
                  />
                  <div
                    className="absolute top-1/2 -translate-y-1/2 w-3 h-3 bg-white dark:bg-gray-100 border-2 border-blue-500 rounded-full shadow-sm"
                    style={{ left: `calc(${clamped}% - 6px)` }}
                  />
                </>
              )
            })()}
          </div>
        </div>
      )}

      {/* Sector/Industry badges */}
      {(md.sector || md.industry) && (
        <div className="flex flex-wrap gap-2">
          {md.sector && (
            <span className="px-3 py-1 text-xs font-semibold bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800 rounded-full">
              {md.sector}
            </span>
          )}
          {md.industry && (
            <span className="px-3 py-1 text-xs font-semibold bg-purple-50 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800 rounded-full">
              {md.industry}
            </span>
          )}
        </div>
      )}

      {/* Candlestick chart */}
      {ohlcv.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">{md.ticker} Price Chart</h3>
          <CandlestickChart ohlcv={ohlcv} emaData={simplifiedEmaData} isDark={isDark} height={360} />
        </div>
      )}
    </div>
  )
}
