import { Activity, AlertCircle, CheckCircle, Loader, Play } from 'lucide-react'
import { useEffect, useRef } from 'react'
import clsx from 'clsx'
import type { AgentEvent } from '../types'

const AGENT_COLORS: Record<string, string> = {
  orchestrator: 'bg-purple-500',
  market: 'bg-blue-500',
  historical: 'bg-cyan-500',
  news: 'bg-orange-500',
  debate_bull: 'bg-green-500',
  debate_bear: 'bg-red-500',
  debate_moderator: 'bg-yellow-500',
  recommender: 'bg-indigo-500',
}

const AGENT_TEXT_COLORS: Record<string, string> = {
  orchestrator: 'text-purple-400',
  market: 'text-blue-400',
  historical: 'text-cyan-400',
  news: 'text-orange-400',
  debate_bull: 'text-green-400',
  debate_bear: 'text-red-400',
  debate_moderator: 'text-yellow-400',
  recommender: 'text-indigo-400',
}

function EventTypeIcon({ type }: { type: string }) {
  switch (type) {
    case 'start':
      return <Play className="w-3.5 h-3.5 text-blue-400" />
    case 'progress':
      return <Activity className="w-3.5 h-3.5 text-yellow-400" />
    case 'complete':
      return <CheckCircle className="w-3.5 h-3.5 text-green-400" />
    case 'error':
      return <AlertCircle className="w-3.5 h-3.5 text-red-400" />
    default:
      return <Loader className="w-3.5 h-3.5 text-gray-400 animate-spin" />
  }
}

function formatTime(timestamp: string): string {
  try {
    const d = new Date(timestamp)
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  } catch {
    return ''
  }
}

interface AgentFeedProps {
  events: AgentEvent[]
  loading: boolean
}

export function AgentFeed({ events, loading }: AgentFeedProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [events.length])

  return (
    <div className="flex flex-col h-full bg-gray-50 dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
        <Activity className="w-4 h-4 text-blue-500" />
        <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100">Agent Activity</h2>
        {loading && (
          <span className="ml-auto flex items-center gap-1 text-xs text-blue-500">
            <span className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-pulse" />
            Live
          </span>
        )}
        {events.length > 0 && !loading && (
          <span className="ml-auto text-xs text-gray-400">{events.length} events</span>
        )}
      </div>

      {/* Events list */}
      <div className="flex-1 overflow-y-auto px-3 py-2 space-y-1.5">
        {events.length === 0 && !loading && (
          <div className="flex flex-col items-center justify-center h-full text-center py-12">
            <Activity className="w-8 h-8 text-gray-300 dark:text-gray-600 mb-3" />
            <p className="text-sm text-gray-400 dark:text-gray-500">Agent activity will appear here</p>
            <p className="text-xs text-gray-300 dark:text-gray-600 mt-1">Search for a ticker to begin</p>
          </div>
        )}

        {events.map((event) => {
          const agentColor = AGENT_COLORS[event.agent_name] || 'bg-gray-500'
          const agentTextColor = AGENT_TEXT_COLORS[event.agent_name] || 'text-gray-400'
          const isError = event.event_type === 'error'

          return (
            <div
              key={event.id}
              className={clsx(
                'rounded-lg px-3 py-2 text-xs',
                isError
                  ? 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800/40'
                  : 'bg-white dark:bg-gray-800/60',
              )}
            >
              <div className="flex items-center gap-2 mb-1">
                <span className={clsx('w-2 h-2 rounded-full flex-shrink-0', agentColor)} />
                <span className={clsx('font-semibold truncate', agentTextColor)}>
                  {event.agent_name.replace(/_/g, ' ')}
                </span>
                <EventTypeIcon type={event.event_type} />
                <span className="ml-auto text-gray-400 dark:text-gray-500 text-[10px] tabular-nums flex-shrink-0">
                  {formatTime(event.timestamp)}
                </span>
              </div>
              <p className={clsx('leading-snug', isError ? 'text-red-600 dark:text-red-400' : 'text-gray-600 dark:text-gray-300')}>
                {event.message}
              </p>
            </div>
          )
        })}

        {loading && events.length > 0 && (
          <div className="flex items-center gap-2 px-3 py-2 text-xs text-blue-500">
            <Loader className="w-3.5 h-3.5 animate-spin" />
            <span>Agents working...</span>
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  )
}
