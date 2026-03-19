import clsx from 'clsx'
import { CandlestickChart } from '../charts/CandlestickChart'
import { IndicatorChart } from '../charts/IndicatorChart'
import type { AnalysisResult } from '../../types'

interface IndicatorRowProps {
  label: string
  value: string | number | null | undefined
  signal?: string
  positive?: boolean
  negative?: boolean
  neutral?: boolean
}

function IndicatorRow({ label, value, signal, positive, negative, neutral }: IndicatorRowProps) {
  const displayValue = value === null || value === undefined ? 'N/A' : typeof value === 'number' ? value.toFixed(4) : value
  return (
    <div className="flex items-center justify-between py-2 border-b border-gray-100 dark:border-gray-800 last:border-0">
      <span className="text-xs text-gray-500 dark:text-gray-400">{label}</span>
      <div className="flex items-center gap-2">
        <span className="text-xs font-semibold text-gray-800 dark:text-gray-200 tabular-nums">{displayValue}</span>
        {signal && (
          <span
            className={clsx(
              'text-[10px] font-semibold px-2 py-0.5 rounded-full',
              positive && 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400',
              negative && 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400',
              neutral && 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400',
            )}
          >
            {signal}
          </span>
        )}
      </div>
    </div>
  )
}

interface TechnicalTabProps {
  result: AnalysisResult
  isDark: boolean
}

export function TechnicalTab({ result, isDark }: TechnicalTabProps) {
  const { ohlcv, indicators } = result

  // Build RSI data from OHLCV timestamps (simplified: we only have last bar indicator values)
  // In production the backend would return per-bar indicator arrays
  const rsiData = ohlcv.slice(-100).map((bar, i, arr) => ({
    time: bar.timestamp,
    value: i === arr.length - 1 ? (indicators.rsi_14 ?? undefined) : undefined,
  })).filter((d) => d.value !== undefined)

  const macdData = ohlcv.slice(-100).map((bar, i, arr) => ({
    time: bar.timestamp,
    value: i === arr.length - 1 ? (indicators.macd ?? undefined) : undefined,
    signal: i === arr.length - 1 ? (indicators.macd_signal ?? undefined) : undefined,
    hist: i === arr.length - 1 ? (indicators.macd_hist ?? undefined) : undefined,
  })).filter((d) => d.value !== undefined)

  const rsi = indicators.rsi_14
  const rsiSignal = rsi === null ? undefined : rsi > 70 ? 'Overbought' : rsi < 30 ? 'Oversold' : 'Neutral'
  const rsiPositive = rsi !== null && rsi < 30
  const rsiNegative = rsi !== null && rsi > 70

  const macdSignal = indicators.macd !== null && indicators.macd_signal !== null
    ? indicators.macd > indicators.macd_signal ? 'Bullish' : 'Bearish'
    : undefined

  const trend = indicators.trend_direction === 1 ? 'Uptrend' : 'Downtrend'
  const adxSignal = indicators.adx !== null
    ? indicators.adx > 25 ? 'Strong' : indicators.adx > 15 ? 'Moderate' : 'Weak'
    : undefined

  return (
    <div className="space-y-4">
      {/* Main candlestick chart */}
      {ohlcv.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
            {result.ticker} — Price & Technical Overlays
          </h3>
          <CandlestickChart ohlcv={ohlcv} isDark={isDark} height={380} />
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        {/* RSI chart */}
        <div className="xl:col-span-2 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4 space-y-4">
          {rsiData.length > 0 ? (
            <IndicatorChart ohlcv={ohlcv} type="rsi" indicatorData={rsiData} isDark={isDark} height={140} />
          ) : (
            <div className="text-center py-8 text-sm text-gray-400">RSI data computed for last bar only</div>
          )}

          {macdData.length > 0 ? (
            <IndicatorChart ohlcv={ohlcv} type="macd" indicatorData={macdData} isDark={isDark} height={140} />
          ) : (
            <div className="text-center py-8 text-sm text-gray-400">MACD data computed for last bar only</div>
          )}
        </div>

        {/* Indicator values panel */}
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">
            Indicator Values
          </h3>
          <IndicatorRow label="Trend Direction" value={trend} signal={trend} positive={trend === 'Uptrend'} negative={trend === 'Downtrend'} />
          <IndicatorRow label="RSI-14" value={indicators.rsi_14?.toFixed(2)} signal={rsiSignal} positive={rsiPositive} negative={rsiNegative} neutral={!rsiPositive && !rsiNegative} />
          <IndicatorRow label="MACD" value={indicators.macd?.toFixed(4)} signal={macdSignal} positive={macdSignal === 'Bullish'} negative={macdSignal === 'Bearish'} />
          <IndicatorRow label="MACD Signal" value={indicators.macd_signal?.toFixed(4)} />
          <IndicatorRow label="MACD Hist" value={indicators.macd_hist?.toFixed(4)} />
          <IndicatorRow label="ATR" value={indicators.atr?.toFixed(2)} />
          <IndicatorRow label="ADX" value={indicators.adx?.toFixed(2)} signal={adxSignal} positive={adxSignal === 'Strong'} neutral={adxSignal === 'Moderate'} negative={adxSignal === 'Weak'} />
          <IndicatorRow label="BB Upper" value={indicators.bb_upper?.toFixed(2)} />
          <IndicatorRow label="BB Middle" value={indicators.bb_middle?.toFixed(2)} />
          <IndicatorRow label="BB Lower" value={indicators.bb_lower?.toFixed(2)} />
          <IndicatorRow label="BB %" value={indicators.bb_pct?.toFixed(3)} />
          <IndicatorRow label="EMA 9" value={indicators.ema_9?.toFixed(2)} />
          <IndicatorRow label="EMA 21" value={indicators.ema_21?.toFixed(2)} />
          <IndicatorRow label="EMA 50" value={indicators.ema_50?.toFixed(2)} />
          <IndicatorRow label="EMA 200" value={indicators.ema_200?.toFixed(2)} />
          <IndicatorRow label="VWAP" value={indicators.vwap?.toFixed(2)} />
          <IndicatorRow
            label="Support"
            value={indicators.support ? `$${indicators.support.toFixed(2)}` : 'N/A'}
            signal="Support"
            positive
          />
          <IndicatorRow
            label="Resistance"
            value={indicators.resistance ? `$${indicators.resistance.toFixed(2)}` : 'N/A'}
            signal="Resistance"
            negative
          />
          <IndicatorRow label="Vol Z-Score" value={indicators.volume_zscore?.toFixed(2)} />
        </div>
      </div>
    </div>
  )
}
