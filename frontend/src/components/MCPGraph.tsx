import {
  Background,
  BackgroundVariant,
  Controls,
  Handle,
  type Node,
  type NodeProps,
  Position,
  ReactFlow,
  type Edge,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import clsx from 'clsx'
import { Network } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { getAgentsStatus } from '../lib/api'
import type { AgentNodeData, FlowEdge, FlowNode } from '../types'

const STATUS_COLORS: Record<string, string> = {
  idle: 'border-gray-400 dark:border-gray-600',
  running: 'border-blue-500',
  done: 'border-green-500',
  error: 'border-red-500',
}

const STATUS_INDICATOR: Record<string, string> = {
  idle: 'bg-gray-400 dark:bg-gray-600',
  running: 'bg-blue-500 animate-pulse',
  done: 'bg-green-500',
  error: 'bg-red-500',
}

const AGENT_LABEL_COLORS: Record<string, string> = {
  orchestrator: 'text-purple-600 dark:text-purple-400',
  market: 'text-blue-600 dark:text-blue-400',
  historical: 'text-cyan-600 dark:text-cyan-400',
  news: 'text-orange-600 dark:text-orange-400',
  debate_bull: 'text-green-600 dark:text-green-400',
  debate_bear: 'text-red-600 dark:text-red-400',
  debate_moderator: 'text-yellow-600 dark:text-yellow-400',
  recommender: 'text-indigo-600 dark:text-indigo-400',
  monitor: 'text-pink-600 dark:text-pink-400',
}

function AgentNode({ data }: NodeProps) {
  const nodeData = data as AgentNodeData
  const statusBorder = STATUS_COLORS[nodeData.status] || STATUS_COLORS.idle
  const statusDot = STATUS_INDICATOR[nodeData.status] || STATUS_INDICATOR.idle
  const labelColor = AGENT_LABEL_COLORS[nodeData.agent_id] || 'text-gray-600 dark:text-gray-400'

  return (
    <div
      className={clsx(
        'rounded-xl border-2 bg-white dark:bg-gray-800 shadow-sm px-3 py-2 min-w-[130px] max-w-[160px]',
        statusBorder,
        nodeData.status === 'running' && 'shadow-blue-500/20 shadow-md',
      )}
    >
      <Handle type="target" position={Position.Top} className="!bg-gray-400 dark:!bg-gray-600 !w-2 !h-2" />
      <div className="flex items-center gap-1.5 mb-1">
        <span className={clsx('w-2 h-2 rounded-full flex-shrink-0', statusDot)} />
        <span className={clsx('text-xs font-semibold truncate', labelColor)}>{nodeData.label}</span>
      </div>
      {nodeData.last_event && (
        <p className="text-[10px] text-gray-400 dark:text-gray-500 leading-tight truncate">
          {nodeData.last_event.substring(0, 50)}
        </p>
      )}
      {!nodeData.last_event && (
        <p className="text-[10px] text-gray-300 dark:text-gray-600">idle</p>
      )}
      <Handle type="source" position={Position.Bottom} className="!bg-gray-400 dark:!bg-gray-600 !w-2 !h-2" />
    </div>
  )
}

const nodeTypes = { agentNode: AgentNode }

interface MCPGraphProps {
  loading: boolean
  activeTicker: string | null
}

function buildDefaultNodes(): Node[] {
  return [
    { id: 'orchestrator', type: 'agentNode', position: { x: 190, y: 0 }, data: { label: 'Orchestrator', status: 'idle', last_event: null, agent_id: 'orchestrator' } },
    { id: 'market', type: 'agentNode', position: { x: 0, y: 120 }, data: { label: 'Market Research', status: 'idle', last_event: null, agent_id: 'market' } },
    { id: 'historical', type: 'agentNode', position: { x: 190, y: 120 }, data: { label: 'Historical Analysis', status: 'idle', last_event: null, agent_id: 'historical' } },
    { id: 'news', type: 'agentNode', position: { x: 380, y: 120 }, data: { label: 'News Sentiment', status: 'idle', last_event: null, agent_id: 'news' } },
    { id: 'debate_bull', type: 'agentNode', position: { x: 60, y: 260 }, data: { label: 'Bull Agent', status: 'idle', last_event: null, agent_id: 'debate_bull' } },
    { id: 'debate_bear', type: 'agentNode', position: { x: 250, y: 260 }, data: { label: 'Bear Agent', status: 'idle', last_event: null, agent_id: 'debate_bear' } },
    { id: 'debate_moderator', type: 'agentNode', position: { x: 155, y: 380 }, data: { label: 'Debate Moderator', status: 'idle', last_event: null, agent_id: 'debate_moderator' } },
    { id: 'recommender', type: 'agentNode', position: { x: 155, y: 500 }, data: { label: 'Recommender', status: 'idle', last_event: null, agent_id: 'recommender' } },
    { id: 'monitor', type: 'agentNode', position: { x: 380, y: 500 }, data: { label: 'Perf Monitor', status: 'idle', last_event: null, agent_id: 'monitor' } },
  ]
}

function buildDefaultEdges(): Edge[] {
  return [
    { id: 'o-m', source: 'orchestrator', target: 'market', type: 'smoothstep', animated: false },
    { id: 'o-h', source: 'orchestrator', target: 'historical', type: 'smoothstep', animated: false },
    { id: 'o-n', source: 'orchestrator', target: 'news', type: 'smoothstep', animated: false },
    { id: 'm-db', source: 'market', target: 'debate_bull', type: 'smoothstep', animated: false },
    { id: 'm-dbe', source: 'market', target: 'debate_bear', type: 'smoothstep', animated: false },
    { id: 'db-dm', source: 'debate_bull', target: 'debate_moderator', type: 'smoothstep', animated: false },
    { id: 'dbe-dm', source: 'debate_bear', target: 'debate_moderator', type: 'smoothstep', animated: false },
    { id: 'dm-r', source: 'debate_moderator', target: 'recommender', type: 'smoothstep', animated: false },
    { id: 'h-r', source: 'historical', target: 'recommender', type: 'smoothstep', animated: false },
    { id: 'n-r', source: 'news', target: 'recommender', type: 'smoothstep', animated: false },
    { id: 'r-mon', source: 'recommender', target: 'monitor', type: 'smoothstep', animated: false },
    { id: 'o-mon', source: 'orchestrator', target: 'monitor', type: 'smoothstep', animated: false },
  ]
}

export function MCPGraph({ loading, activeTicker }: MCPGraphProps) {
  const [nodes, setNodes] = useState<Node[]>(buildDefaultNodes)
  const [edges, setEdges] = useState<Edge[]>(buildDefaultEdges)

  const fetchStatus = useCallback(async () => {
    try {
      const data = await getAgentsStatus()
      if (data.nodes.length > 0) {
        setNodes(
          data.nodes.map((n: FlowNode) => ({
            id: n.id,
            type: n.type,
            position: n.position,
            data: n.data,
          })),
        )
        setEdges(
          data.edges.map((e: FlowEdge) => ({
            id: e.id,
            source: e.source,
            target: e.target,
            animated: e.animated,
            type: e.type,
          })),
        )
      }
    } catch {
      // silently fail
    }
  }, [])

  useEffect(() => {
    if (!activeTicker) return

    fetchStatus()
    const interval = setInterval(fetchStatus, 2000)
    return () => clearInterval(interval)
  }, [activeTicker, loading, fetchStatus])

  return (
    <div className="flex flex-col h-full bg-gray-50 dark:bg-gray-900 border-l border-gray-200 dark:border-gray-800">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
        <Network className="w-4 h-4 text-purple-500" />
        <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100">Agent Graph</h2>
        {activeTicker && (
          <span className="ml-auto text-xs text-gray-400 dark:text-gray-500">{activeTicker}</span>
        )}
      </div>

      {/* React Flow */}
      <div className="flex-1">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          proOptions={{ hideAttribution: true }}
          panOnDrag={false}
          zoomOnScroll={false}
          zoomOnPinch={false}
          nodesDraggable={false}
          nodesConnectable={false}
          elementsSelectable={false}
        >
          <Background
            variant={BackgroundVariant.Dots}
            gap={16}
            size={1}
            className="!text-gray-200 dark:[&>*]:fill-gray-700"
          />
          <Controls
            showInteractive={false}
            className="!bg-white dark:!bg-gray-800 !border-gray-200 dark:!border-gray-700 !shadow-sm [&>button]:!text-gray-600 dark:[&>button]:!text-gray-300"
          />
        </ReactFlow>
      </div>
    </div>
  )
}
