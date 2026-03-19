import {
  ColorType,
  CrosshairMode,
  type IChartApi,
  createChart,
} from 'lightweight-charts'
import { useEffect, useRef } from 'react'
import type { OHLCV } from '../../types'

interface IndicatorChartProps {
  ohlcv: OHLCV[]
  type: 'rsi' | 'macd'
  indicatorData: Array<{
    time: string
    value?: number
    signal?: number
    hist?: number
  }>
  isDark?: boolean
  height?: number
}

export function IndicatorChart({ ohlcv: _ohlcv, type, indicatorData, isDark = true, height = 150 }: IndicatorChartProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)

  useEffect(() => {
    if (!containerRef.current || !indicatorData.length) return

    const bgColor = isDark ? '#111827' : '#ffffff'
    const textColor = isDark ? '#9ca3af' : '#374151'
    const gridColor = isDark ? '#1f2937' : '#f3f4f6'
    const borderColor = isDark ? '#374151' : '#e5e7eb'

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height,
      layout: {
        background: { type: ColorType.Solid, color: bgColor },
        textColor,
      },
      grid: {
        vertLines: { color: gridColor },
        horzLines: { color: gridColor },
      },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor },
      timeScale: {
        borderColor,
        timeVisible: true,
        secondsVisible: false,
      },
    })

    chartRef.current = chart

    if (type === 'rsi') {
      const rsiSeries = chart.addLineSeries({
        color: '#a855f7',
        lineWidth: 2,
        lastValueVisible: true,
        priceLineVisible: false,
      })

      const rsiData = indicatorData
        .filter((d) => d.value !== undefined && d.value !== null)
        .map((d) => ({
          time: d.time.split('T')[0] as `${number}-${number}-${number}`,
          value: d.value!,
        }))
      rsiSeries.setData(rsiData)

      // Overbought/oversold reference lines
      const overboughtSeries = chart.addLineSeries({
        color: '#ef4444',
        lineWidth: 1,
        lineStyle: 2, // dashed
        lastValueVisible: false,
        priceLineVisible: false,
      })
      const oversoldSeries = chart.addLineSeries({
        color: '#22c55e',
        lineWidth: 1,
        lineStyle: 2,
        lastValueVisible: false,
        priceLineVisible: false,
      })

      if (rsiData.length > 0) {
        const first = rsiData[0].time
        const last = rsiData[rsiData.length - 1].time
        overboughtSeries.setData([
          { time: first, value: 70 },
          { time: last, value: 70 },
        ])
        oversoldSeries.setData([
          { time: first, value: 30 },
          { time: last, value: 30 },
        ])
      }
    } else if (type === 'macd') {
      const macdSeries = chart.addLineSeries({
        color: '#60a5fa',
        lineWidth: 2,
        lastValueVisible: true,
        priceLineVisible: false,
      })

      const signalSeries = chart.addLineSeries({
        color: '#f97316',
        lineWidth: 1,
        lastValueVisible: false,
        priceLineVisible: false,
      })

      const histSeries = chart.addHistogramSeries({
        color: '#22c55e',
        priceLineVisible: false,
      })

      const macdData = indicatorData
        .filter((d) => d.value !== undefined)
        .map((d) => ({
          time: d.time.split('T')[0] as `${number}-${number}-${number}`,
          value: d.value!,
        }))

      const signalData = indicatorData
        .filter((d) => d.signal !== undefined)
        .map((d) => ({
          time: d.time.split('T')[0] as `${number}-${number}-${number}`,
          value: d.signal!,
        }))

      const histData = indicatorData
        .filter((d) => d.hist !== undefined)
        .map((d) => ({
          time: d.time.split('T')[0] as `${number}-${number}-${number}`,
          value: d.hist!,
          color: (d.hist ?? 0) >= 0 ? '#22c55e80' : '#ef444480',
        }))

      macdSeries.setData(macdData)
      signalSeries.setData(signalData)
      histSeries.setData(histData)
    }

    chart.timeScale().fitContent()

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
  }, [type, indicatorData, isDark, height])

  // Update theme
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

  return (
    <div>
      <div className="flex items-center gap-2 mb-1">
        <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">
          {type.toUpperCase()}
        </span>
        {type === 'rsi' && (
          <div className="flex items-center gap-3 text-[10px]">
            <span className="text-red-500">— 70 Overbought</span>
            <span className="text-green-500">— 30 Oversold</span>
          </div>
        )}
        {type === 'macd' && (
          <div className="flex items-center gap-3 text-[10px]">
            <span style={{ color: '#60a5fa' }}>— MACD</span>
            <span style={{ color: '#f97316' }}>— Signal</span>
            <span className="text-gray-400">■ Histogram</span>
          </div>
        )}
      </div>
      <div ref={containerRef} className="w-full rounded-lg overflow-hidden" style={{ height }} />
    </div>
  )
}
