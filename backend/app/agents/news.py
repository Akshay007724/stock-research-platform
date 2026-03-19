from __future__ import annotations

import logging

from app.mcp.bus import MCPBus
from app.mcp.registry import registry
from app.schemas import AgentEvent, NewsArticle, SentimentScore
from app.services.news_service import fetch_news

logger = logging.getLogger(__name__)


async def run(ticker: str, bus: MCPBus) -> tuple[list[NewsArticle], SentimentScore]:
    """News Sentiment Agent: fetches news and scores sentiment."""
    agent = "news"

    await registry.set_status(agent, "running", bus._redis, f"Fetching news for {ticker}")
    await bus.publish(
        ticker,
        AgentEvent(
            agent_name=agent,
            event_type="start",
            message=f"Scanning news sources for {ticker}",
        ),
    )

    try:
        await bus.publish(
            ticker,
            AgentEvent(
                agent_name=agent,
                event_type="progress",
                message="Fetching Yahoo Finance RSS feed...",
            ),
        )

        await bus.publish(
            ticker,
            AgentEvent(
                agent_name=agent,
                event_type="progress",
                message="Fetching MarketWatch headlines...",
            ),
        )

        await bus.publish(
            ticker,
            AgentEvent(
                agent_name=agent,
                event_type="progress",
                message="Checking Seeking Alpha and NewsAPI sources...",
            ),
        )

        articles, sentiment = await fetch_news(ticker)

        await bus.publish(
            ticker,
            AgentEvent(
                agent_name=agent,
                event_type="progress",
                message=f"Found {len(articles)} articles, scoring sentiment with AI...",
                data={"article_count": len(articles)},
            ),
        )

        sentiment_label = sentiment.overall_sentiment
        score_pct = f"{sentiment.score:+.2f}"

        await bus.publish(
            ticker,
            AgentEvent(
                agent_name=agent,
                event_type="progress",
                message=f"Sentiment analysis complete: {sentiment_label} ({score_pct})",
                data={
                    "sentiment": sentiment_label,
                    "score": sentiment.score,
                    "news_volume": sentiment.news_volume,
                },
            ),
        )

        if sentiment.key_themes:
            await bus.publish(
                ticker,
                AgentEvent(
                    agent_name=agent,
                    event_type="progress",
                    message=f"Key themes: {', '.join(sentiment.key_themes[:5])}",
                ),
            )

        await registry.set_status(agent, "done", bus._redis, f"News analysis complete for {ticker}")
        await bus.publish(
            ticker,
            AgentEvent(
                agent_name=agent,
                event_type="complete",
                message=f"News sentiment analysis complete: {len(articles)} articles processed",
            ),
        )

        return articles, sentiment

    except Exception as exc:
        logger.exception("News agent failed for %s: %s", ticker, exc)
        await registry.set_status(agent, "error", bus._redis, str(exc))
        await bus.publish(
            ticker,
            AgentEvent(
                agent_name=agent,
                event_type="error",
                message=f"News fetch failed: {exc}",
            ),
        )
        # Return empty results so orchestration continues
        return [], SentimentScore(
            score=0.0,
            signals=[f"News fetch failed: {exc}"],
            overall_sentiment="neutral",
            news_volume=0,
            key_themes=[],
        )
