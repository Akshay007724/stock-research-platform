import { ExternalLink, Newspaper } from 'lucide-react'
import clsx from 'clsx'
import { SentimentTimeline } from '../charts/SentimentTimeline'
import type { NewsArticle, SentimentScore } from '../../types'

function timeAgo(dateStr: string): string {
  try {
    const now = Date.now()
    const then = new Date(dateStr).getTime()
    const diffMs = now - then
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
    const diffDays = Math.floor(diffHours / 24)
    if (diffHours < 1) return 'just now'
    if (diffHours < 24) return `${diffHours}h ago`
    if (diffDays < 7) return `${diffDays}d ago`
    return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  } catch {
    return ''
  }
}

function SentimentBadge({ label, score }: { label: string; score: number }) {
  const config = {
    positive: 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 border-green-200 dark:border-green-800',
    negative: 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 border-red-200 dark:border-red-800',
    neutral: 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 border-gray-200 dark:border-gray-700',
  }
  const style = config[label as keyof typeof config] || config.neutral
  return (
    <span className={clsx('inline-flex items-center gap-1 px-2 py-0.5 text-[10px] font-semibold rounded-full border', style)}>
      {label} {score > 0 ? '+' : ''}{score.toFixed(2)}
    </span>
  )
}

interface NewsTabProps {
  articles: NewsArticle[]
  sentiment: SentimentScore
}

export function NewsTab({ articles, sentiment }: NewsTabProps) {
  const positiveCount = articles.filter((a) => a.sentiment_label === 'positive').length
  const negativeCount = articles.filter((a) => a.sentiment_label === 'negative').length
  const neutralCount = articles.filter((a) => a.sentiment_label === 'neutral').length
  const total = articles.length || 1

  return (
    <div className="space-y-4">
      {/* Sentiment overview */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
        <div className="flex flex-wrap items-center gap-4 mb-3">
          <div className="flex-1">
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1">Sentiment Overview</h3>
            <div className="flex items-center gap-2 text-xs text-gray-500">
              <span>{articles.length} articles analyzed</span>
              {sentiment.key_themes.length > 0 && (
                <>
                  <span>·</span>
                  <span>Themes: {sentiment.key_themes.join(', ')}</span>
                </>
              )}
            </div>
          </div>
          <div
            className={clsx(
              'px-4 py-2 rounded-xl text-sm font-bold border',
              sentiment.overall_sentiment === 'positive'
                ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400 border-green-200 dark:border-green-800'
                : sentiment.overall_sentiment === 'negative'
                ? 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 border-red-200 dark:border-red-800'
                : 'bg-gray-50 dark:bg-gray-800 text-gray-600 dark:text-gray-400 border-gray-200 dark:border-gray-700',
            )}
          >
            {sentiment.overall_sentiment.toUpperCase()} ({sentiment.score > 0 ? '+' : ''}{sentiment.score.toFixed(3)})
          </div>
        </div>

        {/* Distribution bar */}
        <div className="flex h-3 rounded-full overflow-hidden gap-0.5 mb-2">
          {positiveCount > 0 && (
            <div
              className="bg-green-500 h-full transition-all duration-700"
              style={{ width: `${(positiveCount / total) * 100}%` }}
            />
          )}
          {neutralCount > 0 && (
            <div
              className="bg-gray-400 dark:bg-gray-600 h-full transition-all duration-700"
              style={{ width: `${(neutralCount / total) * 100}%` }}
            />
          )}
          {negativeCount > 0 && (
            <div
              className="bg-red-500 h-full transition-all duration-700"
              style={{ width: `${(negativeCount / total) * 100}%` }}
            />
          )}
        </div>

        <div className="flex gap-4 text-xs text-gray-500">
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-green-500 inline-block" />{positiveCount} positive</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-gray-400 dark:bg-gray-600 inline-block" />{neutralCount} neutral</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-500 inline-block" />{negativeCount} negative</span>
        </div>
      </div>

      {/* Sentiment timeline */}
      {articles.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">
            Sentiment Timeline
          </h3>
          <SentimentTimeline articles={articles} />
        </div>
      )}

      {/* Article list */}
      <div className="space-y-2">
        {articles.length === 0 && (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <Newspaper className="w-10 h-10 text-gray-300 dark:text-gray-600 mb-3" />
            <p className="text-sm text-gray-400">No news articles found</p>
          </div>
        )}

        {articles.map((article, i) => (
          <article
            key={i}
            className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-4 hover:border-blue-300 dark:hover:border-blue-700 transition-colors"
          >
            <div className="flex flex-wrap items-start gap-2 mb-2">
              <div className="flex-1 min-w-0">
                <a
                  href={article.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm font-semibold text-gray-900 dark:text-gray-100 hover:text-blue-600 dark:hover:text-blue-400 transition-colors line-clamp-2 flex items-start gap-1.5"
                >
                  {article.title}
                  <ExternalLink className="w-3 h-3 flex-shrink-0 mt-0.5 text-gray-400" />
                </a>
              </div>
              <SentimentBadge label={article.sentiment_label} score={article.sentiment_score} />
            </div>

            {article.summary && (
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-2 line-clamp-2 leading-relaxed">
                {article.summary}
              </p>
            )}

            <div className="flex items-center gap-3 text-xs text-gray-400">
              <span className="font-medium text-gray-500 dark:text-gray-400">{article.source}</span>
              <span>·</span>
              <span>{timeAgo(article.published_at)}</span>
              <span className="ml-auto text-[10px]">
                Relevance: {(article.relevance_score * 100).toFixed(0)}%
              </span>
            </div>
          </article>
        ))}
      </div>
    </div>
  )
}
