import {
  ColorType,
  CrosshairMode,
  LineStyle,
  type IChartApi,
  type ISeriesApi,
  createChart,
} from 'lightweight-charts'
import { useEffect, useRef, useState } from 'react'
import clsx from 'clsx'
import type { OHLCV } from '../../types'

type Period = '1M' | '3M' | '6M' | '1Y'

const PERIOD_DAYS: Record<Period, number> = {
  '1M': 30,
  '3M': 90,
  '6M': 180,
  '1Y': 365,
}

const EMA_COLORS = {
  ema_9: '#60a5fa',   // blue-400
  ema_21: '#f97316',  // orange-500
  ema_50: '#a855f7',  // purple-500
  ema_200: '#22c55e', // green-500
}

interface EMAData {
  ema_9?: Array<{ time: string; value: number }>
  ema_21?: Array<{ time: string; value: number }>
  ema_50?: Array<{ time: string; value: number }>
  ema_200?: Array<{ time: string; value: number }>
}

interface CandlestickChartProps {
  ohlcv: OHLCV[]
  emaData?: EMAData
  isDark?: boolean
  height?: number
}

export function CandlestickChart({ ohlcv, emaData, isDark = true, height = 400 }: CandlestickChartProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null)
  const [period, setPeriod] = useState<Period>('1Y')

  // Filter data by period
  const filteredOHLCV = ohlcv.slice(-PERIOD_DAYS[period])

  useEffect(() => {
    if (!containerRef.current) return

    const bgColor = isDark ? '#111827' : '#ffffff'
    const textColor = isDark ? '#9ca3af' : '#374151'
    const gridColor = isDark ? '#1f2937' : '#f3f4f6'
    const borderColor = isDark ? '#374151' : '#e5e7eb'

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: height - 50, // leave room for volume
      layout: {
        background: { type: ColorType.Solid, color: bgColor },
        textColor,
      },
      grid: {
        vertLines: { color: gridColor },
        horzLines: { color: gridColor },
      },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: borderColor },
      timeScale: {
        borderColor: borderColor,
        timeVisible: true,
        secondsVisible: false,
      },
    })

    chartRef.current = chart

    // Candlestick series
    const candleSeries = chart.addCandlestickSeries({
      upColor: '#22c55e',
      downColor: '#ef4444',
      borderUpColor: '#22c55e',
      borderDownColor: '#ef4444',
      wickUpColor: '#22c55e',
      wickDownColor: '#ef4444',
    })
    candleSeriesRef.current = candleSeries

    // Volume histogram (in a separate pane conceptually, using price scale)
    const volumeSeries = chart.addHistogramSeries({
      color: '#3b82f6',
      priceFormat: { type: 'volume' },
      priceScaleId: 'volume',
    })
    chart.priceScale('volume').applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 },
    })
    volumeSeriesRef.current = volumeSeries

    // EMA line series
    if (emaData) {
      for (const [key, data] of Object.entries(emaData)) {
        if (!data || data.length === 0) continue
        const color = EMA_COLORS[key as keyof typeof EMA_COLORS] || '#ffffff'
        const emaSeries = chart.addLineSeries({
          color,
          lineWidth: 1,
          lineStyle: LineStyle.Solid,
          lastValueVisible: false,
          priceLineVisible: false,
        })
        emaSeries.setData(data)
      }
    }

    // Resize observer
    const resizeObserver = new ResizeObserver((entries) => {
      const entry = entries[0]
      if (entry && chart) {
        chart.applyOptions({ width: entry.contentRect.width })
      }
    })
    resizeObserver.observe(containerRef.current)

    return () => {
      resizeObserver.disconnect()
      chart.remove()
      chartRef.current = null
    }
  }, [isDark, height])

  // Update theme when isDark changes
  useEffect(() => {
    if (!chartRef.current) return
    const bgColor = isDark ? '#111827' : '#ffffff'
    const textColor = isDark ? '#9ca3af' : '#374151'
    const gridColor = isDark ? '#1f2937' : '#f3f4f6'
    const borderColor = isDark ? '#374151' : '#e5e7eb'

    chartRef.current.applyOptions({
      layout: { background: { type: ColorType.Solid, color: bgColor }, textColor },
      grid: { vertLines: { color: gridColor }, horzLines: { color: gridColor } },
      rightPriceScale: { borderColor },
      timeScale: { borderColor },
    })
  }, [isDark])

  // Update data when period or ohlcv changes
  useEffect(() => {
    if (!candleSeriesRef.current || !volumeSeriesRef.current) return

    const sliced = ohlcv.slice(-PERIOD_DAYS[period])

    const candleData = sliced.map((bar) => ({
      time: bar.timestamp.split('T')[0] as `${number}-${number}-${number}`,
      open: bar.open,
      high: bar.high,
      low: bar.low,
      close: bar.close,
    }))

    const volumeData = sliced.map((bar) => ({
      time: bar.timestamp.split('T')[0] as `${number}-${number}-${number}`,
      value: bar.volume,
      color: bar.close >= bar.open ? '#22c55e40' : '#ef444440',
    }))

    candleSeriesRef.current.setData(candleData)
    volumeSeriesRef.current.setData(volumeData)
    chartRef.current?.timeScale().fitContent()
  }, [ohlcv, period])

  return (
    <div className="flex flex-col gap-2">
      {/* Period selector */}
      <div className="flex gap-1 justify-end">
        {(Object.keys(PERIOD_DAYS) as Period[]).map((p) => (
          <button
            key={p}
            onClick={() => setPeriod(p)}
            className={clsx(
              'px-3 py-1 text-xs font-semibold rounded-lg transition-colors',
              period === p
                ? 'bg-blue-600 text-white'
                : 'text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800',
            )}
          >
            {p}
          </button>
        ))}
        {/* EMA legend */}
        <div className="ml-4 flex items-center gap-3">
          {Object.entries(EMA_COLORS).map(([key, color]) => (
            <div key={key} className="flex items-center gap-1">
              <span className="w-3 h-0.5 rounded-full inline-block" style={{ backgroundColor: color }} />
              <span className="text-[10px] text-gray-400">{key.replace('ema_', 'EMA ')}</span>
            </div>
          ))}
        </div>
      </div>

      <div ref={containerRef} className="w-full rounded-lg overflow-hidden" style={{ height: height - 50 }} />
    </div>
  )
}
