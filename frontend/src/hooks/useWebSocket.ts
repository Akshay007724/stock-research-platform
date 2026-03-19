import { useCallback, useEffect, useRef, useState } from 'react'

interface PriceUpdate {
  type: 'price_update'
  ticker: string
  price: number | null
  change: number | null
  change_pct: number | null
  volume: number | null
  timestamp: string
}

interface WsMessage {
  type: string
  [key: string]: unknown
}

interface UseWebSocketReturn {
  priceUpdate: PriceUpdate | null
  connected: boolean
}

const WS_BASE = (import.meta.env.VITE_WS_URL as string | undefined) ||
  (typeof window !== 'undefined'
    ? `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}`
    : 'ws://localhost:8000')

export function useWebSocket(ticker: string | null): UseWebSocketReturn {
  const [priceUpdate, setPriceUpdate] = useState<PriceUpdate | null>(null)
  const [connected, setConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const connect = useCallback((t: string) => {
    if (wsRef.current) {
      wsRef.current.close()
    }

    const ws = new WebSocket(`${WS_BASE}/ws/${t.toUpperCase()}`)

    ws.onopen = () => {
      setConnected(true)
    }

    ws.onmessage = (e: MessageEvent<string>) => {
      try {
        const msg = JSON.parse(e.data) as WsMessage
        if (msg.type === 'price_update') {
          setPriceUpdate(msg as unknown as PriceUpdate)
        }
      } catch {
        // ignore
      }
    }

    ws.onclose = () => {
      setConnected(false)
      // Reconnect after 5 seconds
      reconnectTimer.current = setTimeout(() => {
        if (ticker) connect(ticker)
      }, 5000)
    }

    ws.onerror = () => {
      ws.close()
    }

    wsRef.current = ws
  }, [ticker])

  useEffect(() => {
    if (!ticker) {
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
      setConnected(false)
      return
    }

    connect(ticker)

    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [ticker, connect])

  return { priceUpdate, connected }
}
