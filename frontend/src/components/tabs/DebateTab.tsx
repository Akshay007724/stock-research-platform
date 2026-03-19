import { Scale, TrendingDown, TrendingUp } from 'lucide-react'
import clsx from 'clsx'
import type { DebateResult } from '../../types'

interface DebateTabProps {
  debate: DebateResult
}

function ScoreBar({ score }: { score: number }) {
  const pct = (score / 10) * 100
  const color = score >= 7 ? 'bg-green-500' : score >= 5 ? 'bg-yellow-500' : 'bg-red-500'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
        <div
          className={clsx('h-full rounded-full transition-all duration-700', color)}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-sm font-bold text-gray-700 dark:text-gray-300 tabular-nums w-10 text-right">
        {score.toFixed(1)}/10
      </span>
    </div>
  )
}

export function DebateTab({ debate }: DebateTabProps) {
  const { bull, bear, verdict, verdict_score, moderator_summary } = debate

  const verdictConfig =
    verdict === 'bull'
      ? { bg: 'bg-green-500', label: 'BULL WINS', icon: <TrendingUp className="w-4 h-4" /> }
      : verdict === 'bear'
      ? { bg: 'bg-red-500', label: 'BEAR WINS', icon: <TrendingDown className="w-4 h-4" /> }
      : { bg: 'bg-gray-500', label: 'NEUTRAL', icon: <Scale className="w-4 h-4" /> }

  return (
    <div className="space-y-4">
      {/* Debate columns */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Bull case */}
        <div className="bg-green-50 dark:bg-green-900/10 border border-green-200 dark:border-green-800/50 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-3">
            <TrendingUp className="w-5 h-5 text-green-600 dark:text-green-400" />
            <h3 className="font-bold text-green-700 dark:text-green-400 text-sm uppercase tracking-wider">
              Bull Case
            </h3>
            <span className="ml-auto px-2 py-0.5 bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-400 text-xs font-bold rounded-full border border-green-300 dark:border-green-700">
              BUY
            </span>
          </div>

          <div className="mb-3">
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Argument Strength</p>
            <ScoreBar score={bull.score} />
          </div>

          <ul className="space-y-2 mb-4">
            {bull.points.map((point, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-gray-700 dark:text-gray-300">
                <span className="text-green-500 font-bold flex-shrink-0 mt-0.5">✓</span>
                {point}
              </li>
            ))}
          </ul>

          {Object.keys(bull.key_metrics).length > 0 && (
            <div className="border-t border-green-200 dark:border-green-800/50 pt-3">
              <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-2">Key Metrics</p>
              <div className="space-y-1">
                {Object.entries(bull.key_metrics).map(([key, val]) => (
                  <div key={key} className="flex justify-between text-xs">
                    <span className="text-gray-500 capitalize">{key.replace(/_/g, ' ')}</span>
                    <span className="font-medium text-gray-700 dark:text-gray-300">{val}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Bear case */}
        <div className="bg-red-50 dark:bg-red-900/10 border border-red-200 dark:border-red-800/50 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-3">
            <TrendingDown className="w-5 h-5 text-red-600 dark:text-red-400" />
            <h3 className="font-bold text-red-700 dark:text-red-400 text-sm uppercase tracking-wider">
              Bear Case
            </h3>
            <span className="ml-auto px-2 py-0.5 bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-400 text-xs font-bold rounded-full border border-red-300 dark:border-red-700">
              SELL
            </span>
          </div>

          <div className="mb-3">
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Argument Strength</p>
            <ScoreBar score={bear.score} />
          </div>

          <ul className="space-y-2 mb-4">
            {bear.points.map((point, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-gray-700 dark:text-gray-300">
                <span className="text-red-500 font-bold flex-shrink-0 mt-0.5">✗</span>
                {point}
              </li>
            ))}
          </ul>

          {Object.keys(bear.key_metrics).length > 0 && (
            <div className="border-t border-red-200 dark:border-red-800/50 pt-3">
              <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-2">Key Metrics</p>
              <div className="space-y-1">
                {Object.entries(bear.key_metrics).map(([key, val]) => (
                  <div key={key} className="flex justify-between text-xs">
                    <span className="text-gray-500 capitalize">{key.replace(/_/g, ' ')}</span>
                    <span className="font-medium text-gray-700 dark:text-gray-300">{val}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* VS badge */}
      <div className="flex items-center gap-4">
        <div className="flex-1 h-px bg-gray-200 dark:bg-gray-700" />
        <span className="text-xs font-black text-gray-400 dark:text-gray-500 tracking-widest">VS</span>
        <div className="flex-1 h-px bg-gray-200 dark:bg-gray-700" />
      </div>

      {/* Moderator verdict */}
      <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-4">
        <div className="flex items-center gap-3 mb-3">
          <Scale className="w-5 h-5 text-yellow-500" />
          <h3 className="font-bold text-gray-800 dark:text-gray-200 text-sm">Moderator Verdict</h3>
          <span
            className={clsx(
              'ml-auto flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold text-white',
              verdictConfig.bg,
            )}
          >
            {verdictConfig.icon}
            {verdictConfig.label}
          </span>
        </div>

        <div className="mb-3">
          <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mb-1">
            <span>Bear</span>
            <span>Score: {verdict_score.toFixed(1)}/10</span>
            <span>Bull</span>
          </div>
          <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden flex">
            <div
              className="bg-red-500 h-full transition-all duration-700"
              style={{ width: `${((10 - verdict_score) / 10) * 100}%` }}
            />
            <div
              className="bg-green-500 h-full transition-all duration-700"
              style={{ width: `${(verdict_score / 10) * 100}%` }}
            />
          </div>
        </div>

        <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">{moderator_summary}</p>
      </div>
    </div>
  )
}
