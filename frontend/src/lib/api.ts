import type { AgentEvent, AgentGraphData, AnalysisResult } from '../types'

const BASE = (import.meta.env.VITE_API_URL as string | undefined) || ''

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, options)
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || `HTTP ${res.status}`)
  }
  return res.json() as Promise<T>
}

export async function analyzeStock(ticker: string): Promise<AnalysisResult> {
  return fetchJSON<AnalysisResult>(`/api/analyze/${ticker.toUpperCase()}`, {
    method: 'POST',
  })
}

export function createSSEStream(
  ticker: string,
  onEvent: (e: AgentEvent) => void,
  onError?: (e: Event) => void,
): EventSource {
  const es = new EventSource(`${BASE}/api/stream/${ticker.toUpperCase()}`)
  es.onmessage = (e: MessageEvent<string>) => {
    try {
      const event = JSON.parse(e.data) as AgentEvent
      onEvent(event)
    } catch {
      // ignore malformed events
    }
  }
  if (onError) {
    es.onerror = onError
  }
  return es
}

export async function getAgentsStatus(): Promise<AgentGraphData> {
  return fetchJSON<AgentGraphData>('/api/agents/status')
}

export async function getTickerHistory(ticker: string, limit = 10) {
  return fetchJSON<{ ticker: string; history: AnalysisResult[] }>(
    `/api/analysis/${ticker.toUpperCase()}/history?limit=${limit}`,
  )
}

export async function clearTickerCache(ticker: string) {
  return fetchJSON<{ message: string }>(
    `/api/analysis/${ticker.toUpperCase()}/cache`,
    { method: 'DELETE' },
  )
}

export interface TickerInfo {
  ticker: string
  name: string
  sector: string
}

export async function getTickers(q = ''): Promise<TickerInfo[]> {
  const url = q ? `/api/tickers?q=${encodeURIComponent(q)}` : '/api/tickers'
  const data = await fetchJSON<{ tickers: TickerInfo[] }>(url)
  return data.tickers
}

export interface ScreenPick {
  ticker: string
  price: number
  change_pct: number
  week_52_high: number
  week_52_low: number
  range_position_pct: number
  rsi_14: number
  composite_score: number
}

export async function getScreenResults(topN = 5): Promise<{ top_picks: ScreenPick[]; screened: number; universe_size: number; methodology: string }> {
  return fetchJSON(`/api/screen?top_n=${topN}`)
}
