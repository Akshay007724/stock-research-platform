import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { NewsArticle } from '../../types'

interface SentimentTimelineProps {
  articles: NewsArticle[]
}

function formatDate(dateStr: string): string {
  try {
    const d = new Date(dateStr)
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  } catch {
    return dateStr
  }
}

interface TooltipProps {
  active?: boolean
  payload?: Array<{ value: number; name: string }>
  label?: string
}

function CustomTooltip({ active, payload, label }: TooltipProps) {
  if (!active || !payload?.length) return null
  const value = payload[0].value
  const color = value > 0 ? '#22c55e' : value < 0 ? '#ef4444' : '#6b7280'
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-xs shadow-xl">
      <p className="text-gray-400 mb-1">{label}</p>
      <p className="font-semibold" style={{ color }}>
        Sentiment: {value > 0 ? '+' : ''}{value.toFixed(3)}
      </p>
    </div>
  )
}

export function SentimentTimeline({ articles }: SentimentTimelineProps) {
  // Group articles by date and average sentiment
  const byDate: Record<string, number[]> = {}
  for (const article of articles) {
    const date = article.published_at.split('T')[0]
    if (!byDate[date]) byDate[date] = []
    byDate[date].push(article.sentiment_score)
  }

  const data = Object.entries(byDate)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, scores]) => ({
      date: formatDate(date),
      sentiment: parseFloat((scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(3)),
    }))

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-24 text-sm text-gray-400">
        No sentiment timeline data available
      </div>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={120}>
      <AreaChart data={data} margin={{ top: 5, right: 10, bottom: 0, left: -20 }}>
        <defs>
          <linearGradient id="sentimentGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
        <XAxis
          dataKey="date"
          tick={{ fill: '#6b7280', fontSize: 10 }}
          tickLine={false}
          axisLine={false}
        />
        <YAxis
          domain={[-1, 1]}
          tick={{ fill: '#6b7280', fontSize: 10 }}
          tickLine={false}
          axisLine={false}
        />
        <Tooltip content={<CustomTooltip />} />
        <ReferenceLine y={0} stroke="#374151" strokeDasharray="3 3" />
        <Area
          type="monotone"
          dataKey="sentiment"
          stroke="#3b82f6"
          strokeWidth={2}
          fill="url(#sentimentGradient)"
          dot={false}
          activeDot={{ r: 4, fill: '#3b82f6' }}
        />
      </AreaChart>
    </ResponsiveContainer>
  )
}
