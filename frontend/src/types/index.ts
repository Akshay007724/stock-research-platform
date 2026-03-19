export interface AgentEvent {
  id: string
  agent_name: string
  event_type: 'start' | 'progress' | 'complete' | 'error'
  message: string
  data: Record<string, unknown>
  timestamp: string
}

export interface MarketData {
  ticker: string
  price: number
  change: number
  change_pct: number
  volume: number
  market_cap: number | null
  pe_ratio: number | null
  eps: number | null
  beta: number | null
  week_52_high: number | null
  week_52_low: number | null
  sector: string | null
  industry: string | null
  name: string | null
}

export interface OHLCV {
  ticker: string
  timestamp: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  adjusted_close: number | null
}

export interface TechnicalIndicators {
  ticker: string
  timestamp: string
  ema_9: number | null
  ema_21: number | null
  ema_50: number | null
  ema_200: number | null
  rsi_14: number | null
  macd: number | null
  macd_signal: number | null
  macd_hist: number | null
  atr: number | null
  bb_upper: number | null
  bb_middle: number | null
  bb_lower: number | null
  bb_pct: number | null
  adx: number | null
  obv: number | null
  vwap: number | null
  volume_zscore: number | null
  support: number | null
  resistance: number | null
  trend_direction: number
}

export interface NewsArticle {
  title: string
  url: string
  source: string
  published_at: string
  sentiment_score: number
  sentiment_label: 'positive' | 'negative' | 'neutral'
  relevance_score: number
  summary: string
}

export interface SentimentScore {
  score: number
  signals: string[]
  overall_sentiment: string
  news_volume: number
  key_themes: string[]
}

export interface DebateArgument {
  side: 'bull' | 'bear'
  points: string[]
  score: number
  key_metrics: Record<string, string>
}

export interface DebateResult {
  ticker: string
  bull: DebateArgument
  bear: DebateArgument
  verdict: string
  verdict_score: number
  moderator_summary: string
}

export interface Recommendation {
  ticker: string
  action: 'BUY' | 'SELL' | 'HOLD'
  confidence: number
  technical_score: number
  sentiment_score: number
  fundamental_score: number
  debate_score: number
  composite_score: number
  reasoning: string[]
  allocation_pct: number
  risk_level: string
  target_price: number | null
  stop_loss: number | null
  timestamp: string
}

export interface AnalysisResult {
  ticker: string
  market_data: MarketData
  ohlcv: OHLCV[]
  indicators: TechnicalIndicators
  news: NewsArticle[]
  debate: DebateResult
  recommendation: Recommendation
  agent_log: AgentEvent[]
}

export interface AgentNodeData extends Record<string, unknown> {
  label: string
  status: 'idle' | 'running' | 'done' | 'error'
  last_event: string | null
  agent_id: string
}

export interface FlowNode {
  id: string
  type: string
  position: { x: number; y: number }
  data: AgentNodeData
}

export interface FlowEdge {
  id: string
  source: string
  target: string
  animated: boolean
  type: string
}

export interface AgentGraphData {
  nodes: FlowNode[]
  edges: FlowEdge[]
}
