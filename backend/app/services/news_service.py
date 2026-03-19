from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone

import feedparser
import httpx
from app.config import settings
from app.schemas import NewsArticle, SentimentScore
from app.services.llm import get_client, get_model

logger = logging.getLogger(__name__)

_RSS_FEEDS = [
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US",
    "https://www.marketwatch.com/rss/topstories",
]

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}


async def _fetch_finnhub_news(ticker: str) -> list[dict]:
    """Fetch company news from Finnhub (primary source)."""
    if not settings.finnhub_api_key:
        return []
    try:
        to_date = datetime.now(timezone.utc)
        from_date = to_date - timedelta(days=7)
        url = "https://finnhub.io/api/v1/company-news"
        params = {
            "symbol": ticker.upper(),
            "from": from_date.strftime("%Y-%m-%d"),
            "to": to_date.strftime("%Y-%m-%d"),
            "token": settings.finnhub_api_key,
        }
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
        articles = []
        for item in resp.json()[:30]:
            ts = item.get("datetime", 0)
            try:
                published = datetime.fromtimestamp(ts, tz=timezone.utc) if ts else datetime.now(timezone.utc)
            except Exception:
                published = datetime.now(timezone.utc)
            articles.append({
                "title": item.get("headline", ""),
                "url": item.get("url", ""),
                "source": item.get("source", "Finnhub"),
                "published_at": published,
                "summary": item.get("summary", "")[:500],
            })
        return articles
    except Exception as exc:
        logger.warning("Finnhub news failed for %s: %s", ticker, exc)
        return []


def _time_decay_weight(published: datetime) -> float:
    now = datetime.now(timezone.utc)
    if published.tzinfo is None:
        published = published.replace(tzinfo=timezone.utc)
    age_hours = (now - published).total_seconds() / 3600
    if age_hours <= 24:
        return 1.0
    elif age_hours <= 48:
        return 0.7
    elif age_hours <= 72:
        return 0.4
    return 0.2


async def _fetch_rss(url: str, timeout: int = 10) -> list[dict]:
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(url, headers=_HEADERS)
            resp.raise_for_status()
        feed = feedparser.parse(resp.text)
        articles = []
        for entry in feed.entries[:30]:
            published = None
            for attr in ("published_parsed", "updated_parsed"):
                t = getattr(entry, attr, None)
                if t:
                    try:
                        published = datetime(*t[:6], tzinfo=timezone.utc)
                        break
                    except Exception:
                        pass
            if published is None:
                published = datetime.now(timezone.utc)

            articles.append(
                {
                    "title": entry.get("title", ""),
                    "url": entry.get("link", ""),
                    "source": feed.feed.get("title", "RSS"),
                    "published_at": published,
                    "summary": entry.get("summary", "")[:500],
                }
            )
        return articles
    except Exception as exc:
        logger.debug("RSS fetch failed for %s: %s", url, exc)
        return []


async def _fetch_newsapi(ticker: str) -> list[dict]:
    if not settings.news_api_key:
        return []
    try:
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": ticker,
            "apiKey": settings.news_api_key,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": 20,
        }
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
        data = resp.json()
        articles = []
        for a in data.get("articles", []):
            published_str = a.get("publishedAt", "")
            try:
                published = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
            except Exception:
                published = datetime.now(timezone.utc)
            articles.append(
                {
                    "title": a.get("title", ""),
                    "url": a.get("url", ""),
                    "source": a.get("source", {}).get("name", "NewsAPI"),
                    "published_at": published,
                    "summary": a.get("description", "")[:500],
                }
            )
        return articles
    except Exception as exc:
        logger.warning("NewsAPI fetch failed: %s", exc)
        return []


async def _score_sentiment_batch(ticker: str, headlines: list[str]) -> list[dict]:
    client = get_client()
    if not client or not headlines:
        return [{"score": 0.0, "label": "neutral"} for _ in headlines]

    numbered = "\n".join(f"{i+1}. {h}" for i, h in enumerate(headlines))
    prompt = (
        f"You are scoring news headlines for their likely impact on {ticker} stock price.\n\n"
        f"Headlines:\n{numbered}\n\n"
        f"For each headline, assign:\n"
        f"  score: float from -1.0 (very negative) to +1.0 (very positive) for {ticker}'s stock\n"
        f"  label: 'positive', 'negative', or 'neutral'\n\n"
        "Consider: earnings surprises, product launches, regulatory news, analyst upgrades/downgrades, macro events.\n"
        "Return ONLY a JSON array with exactly {len(headlines)} objects: "
        '[{"score": 0.0, "label": "neutral"}, ...]'
    )

    try:
        resp = await client.chat.completions.create(
            model=get_model(),
            messages=[
                {"role": "system", "content": "You are a professional financial sentiment analyst specializing in equity market impact. Return only valid JSON arrays — no markdown, no explanation."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=1200,
        )
        content = resp.choices[0].message.content or "[]"
        # Extract JSON array
        start = content.find("[")
        end = content.rfind("]") + 1
        if start >= 0 and end > start:
            results = json.loads(content[start:end])
            if len(results) == len(headlines):
                return results
    except Exception as exc:
        logger.warning("Sentiment scoring failed: %s", exc)

    return [{"score": 0.0, "label": "neutral"} for _ in headlines]


async def fetch_news(ticker: str) -> tuple[list[NewsArticle], SentimentScore]:
    """Fetch news from Finnhub (primary) + RSS fallback, score sentiment."""
    import asyncio

    raw_articles: list[dict] = []

    # Primary: Finnhub company news
    finnhub_articles = await _fetch_finnhub_news(ticker)
    raw_articles.extend(finnhub_articles)

    # Fallback to RSS if Finnhub returned nothing
    if not finnhub_articles:
        rss_url = _RSS_FEEDS[0].format(ticker=ticker.upper())
        rss_articles = await _fetch_rss(rss_url)
        raw_articles.extend(rss_articles)

        # Also try general market RSS filtered by ticker
        general_articles = await _fetch_rss(_RSS_FEEDS[1])
        ticker_upper = ticker.upper()
        for a in general_articles:
            if ticker_upper in a.get("title", "").upper() or ticker_upper in a.get("summary", "").upper():
                raw_articles.append(a)

    # NewsAPI supplement (if key set)
    newsapi_articles = await _fetch_newsapi(ticker)
    raw_articles.extend(newsapi_articles)

    # Deduplicate by URL
    seen_urls: set[str] = set()
    unique_articles: list[dict] = []
    for a in raw_articles:
        url = a.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_articles.append(a)

    if not unique_articles:
        # Return empty sentiment if no news
        return [], SentimentScore(
            score=0.0,
            signals=["No news articles found"],
            overall_sentiment="neutral",
            news_volume=0,
            key_themes=[],
        )

    # Apply time-decay weighting for relevance sorting
    for a in unique_articles:
        a["time_weight"] = _time_decay_weight(a["published_at"])

    unique_articles.sort(key=lambda x: x["time_weight"], reverse=True)
    top_articles = unique_articles[:20]

    # Score sentiment in batches of 10
    headlines = [a["title"] for a in top_articles]
    sentiments: list[dict] = []
    for i in range(0, len(headlines), 10):
        batch = headlines[i : i + 10]
        batch_sentiments = await _score_sentiment_batch(ticker, batch)
        sentiments.extend(batch_sentiments)

    # Build NewsArticle objects
    news_articles: list[NewsArticle] = []
    weighted_score = 0.0
    total_weight = 0.0

    for i, raw in enumerate(top_articles):
        sent = sentiments[i] if i < len(sentiments) else {"score": 0.0, "label": "neutral"}
        score = float(sent.get("score", 0.0))
        label = sent.get("label", "neutral")
        if label not in ("positive", "negative", "neutral"):
            label = "neutral"
        time_w = raw["time_weight"]
        relevance = time_w * (0.5 + abs(score) * 0.5)

        news_articles.append(
            NewsArticle(
                title=raw["title"],
                url=raw["url"],
                source=raw["source"],
                published_at=raw["published_at"],
                sentiment_score=score,
                sentiment_label=label,
                relevance_score=relevance,
                summary=raw.get("summary", ""),
            )
        )

        weighted_score += score * time_w
        total_weight += time_w

    # Sort by relevance
    news_articles.sort(key=lambda x: x.relevance_score, reverse=True)

    composite_score = (weighted_score / total_weight) if total_weight > 0 else 0.0

    positive_count = sum(1 for a in news_articles if a.sentiment_label == "positive")
    negative_count = sum(1 for a in news_articles if a.sentiment_label == "negative")

    if composite_score > 0.2:
        overall = "positive"
    elif composite_score < -0.2:
        overall = "negative"
    else:
        overall = "neutral"

    signals: list[str] = []
    if positive_count > negative_count:
        signals.append(f"{positive_count} positive articles vs {negative_count} negative")
    elif negative_count > positive_count:
        signals.append(f"{negative_count} negative articles vs {positive_count} positive")
    else:
        signals.append(f"Mixed sentiment: {positive_count} positive, {negative_count} negative")

    # Extract key themes from top headlines
    key_themes: list[str] = []
    common_words = {"the", "a", "an", "in", "on", "at", "to", "for", "of", "and", "or", "is", "are", "was", "were", ticker.upper(), ticker.lower()}
    word_freq: dict[str, int] = {}
    for a in news_articles[:10]:
        for word in a.title.lower().split():
            clean = word.strip(".,!?;:'\"()[]")
            if len(clean) > 3 and clean not in common_words:
                word_freq[clean] = word_freq.get(clean, 0) + 1
    for word, count in sorted(word_freq.items(), key=lambda x: -x[1])[:5]:
        if count >= 2:
            key_themes.append(word)

    sentiment_obj = SentimentScore(
        score=composite_score,
        signals=signals,
        overall_sentiment=overall,
        news_volume=len(news_articles),
        key_themes=key_themes,
    )

    return news_articles, sentiment_obj
