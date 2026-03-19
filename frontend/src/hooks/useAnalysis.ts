import { useCallback, useRef, useState } from 'react'
import { analyzeStock, createSSEStream } from '../lib/api'
import type { AgentEvent, AnalysisResult } from '../types'

interface UseAnalysisReturn {
  result: AnalysisResult | null
  loading: boolean
  error: string | null
  events: AgentEvent[]
  activeTicker: string | null
  analyze: (ticker: string) => Promise<void>
  clearError: () => void
  reset: () => void
}

export function useAnalysis(): UseAnalysisReturn {
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [events, setEvents] = useState<AgentEvent[]>([])
  const [activeTicker, setActiveTicker] = useState<string | null>(null)
  const esRef = useRef<EventSource | null>(null)

  const analyze = useCallback(async (ticker: string) => {
    const upperTicker = ticker.toUpperCase().trim()
    if (!upperTicker) return

    // Close any existing SSE stream
    if (esRef.current) {
      esRef.current.close()
      esRef.current = null
    }

    setLoading(true)
    setError(null)
    setEvents([])
    setResult(null)
    setActiveTicker(upperTicker)

    // Start SSE stream BEFORE posting so we capture all events
    const es = createSSEStream(upperTicker, (e: AgentEvent) => {
      setEvents((prev) => {
        // Deduplicate by id
        if (prev.some((p) => p.id === e.id)) return prev
        return [...prev, e]
      })
    })
    esRef.current = es

    try {
      const analysisResult = await analyzeStock(upperTicker)
      setResult(analysisResult)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Analysis failed'
      setError(message)
    } finally {
      setLoading(false)
      // Close SSE after a short delay to capture final events
      setTimeout(() => {
        if (esRef.current) {
          esRef.current.close()
          esRef.current = null
        }
      }, 2000)
    }
  }, [])

  const clearError = useCallback(() => setError(null), [])

  const reset = useCallback(() => {
    if (esRef.current) {
      esRef.current.close()
      esRef.current = null
    }
    setResult(null)
    setLoading(false)
    setError(null)
    setEvents([])
    setActiveTicker(null)
  }, [])

  return { result, loading, error, events, activeTicker, analyze, clearError, reset }
}
