import { useCallback, useEffect, useRef } from 'react'
import { createSSEStream } from '../lib/api'
import type { AgentEvent } from '../types'

interface UseSSEOptions {
  ticker: string | null
  onEvent: (event: AgentEvent) => void
  enabled?: boolean
}

export function useSSE({ ticker, onEvent, enabled = true }: UseSSEOptions): void {
  const esRef = useRef<EventSource | null>(null)
  const onEventRef = useRef(onEvent)

  // Keep callback ref current without re-subscribing
  useEffect(() => {
    onEventRef.current = onEvent
  }, [onEvent])

  const connect = useCallback((t: string) => {
    if (esRef.current) {
      esRef.current.close()
      esRef.current = null
    }
    const es = createSSEStream(
      t,
      (e) => onEventRef.current(e),
      () => {
        // On error, attempt reconnect after 2 seconds
        setTimeout(() => {
          if (esRef.current && esRef.current.readyState !== EventSource.CLOSED) return
          const fresh = createSSEStream(t, (e) => onEventRef.current(e))
          esRef.current = fresh
        }, 2000)
      },
    )
    esRef.current = es
    return es
  }, [])

  useEffect(() => {
    if (!ticker || !enabled) {
      if (esRef.current) {
        esRef.current.close()
        esRef.current = null
      }
      return
    }

    connect(ticker)

    return () => {
      if (esRef.current) {
        esRef.current.close()
        esRef.current = null
      }
    }
  }, [ticker, enabled, connect])
}
