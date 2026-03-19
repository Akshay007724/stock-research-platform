from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.utcnow()


class AgentEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_name: str
    event_type: str  # start | progress | complete | error
    message: str
    data: dict = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=_now)


class MarketData(BaseModel):
    ticker: str
    price: float
    change: float
    change_pct: float
    volume: int
    market_cap: float | None = None
    pe_ratio: float | None = None
    eps: float | None = None
    beta: float | None = None
    week_52_high: float | None = None
    week_52_low: float | None = None
    sector: str | None = None
    industry: str | None = None
    name: str | None = None


class OHLCV(BaseModel):
    ticker: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    adjusted_close: float | None = None


class TechnicalIndicators(BaseModel):
    ticker: str
    timestamp: datetime
    ema_9: float | None = None
    ema_21: float | None = None
    ema_50: float | None = None
    ema_200: float | None = None
    rsi_14: float | None = None
    macd: float | None = None
    macd_signal: float | None = None
    macd_hist: float | None = None
    atr: float | None = None
    bb_upper: float | None = None
    bb_middle: float | None = None
    bb_lower: float | None = None
    bb_pct: float | None = None
    adx: float | None = None
    obv: float | None = None
    vwap: float | None = None
    volume_zscore: float | None = None
    support: float | None = None
    resistance: float | None = None
    trend_direction: int = 0  # +1 or -1


class NewsArticle(BaseModel):
    title: str
    url: str
    source: str
    published_at: datetime
    sentiment_score: float = 0.0
    sentiment_label: Literal["positive", "negative", "neutral"] = "neutral"
    relevance_score: float = 0.0
    summary: str = ""


class DebateArgument(BaseModel):
    side: Literal["bull", "bear"]
    points: list[str]
    score: float
    key_metrics: dict = Field(default_factory=dict)


class DebateResult(BaseModel):
    ticker: str
    bull: DebateArgument
    bear: DebateArgument
    verdict: str
    verdict_score: float
    moderator_summary: str


class FundamentalScore(BaseModel):
    score: float
    signals: list[str]
    pe_analysis: str
    growth_analysis: str
    risk_assessment: str


class TechnicalScore(BaseModel):
    score: float
    signals: list[str]
    trend: str
    momentum: str
    support_resistance: str


class SentimentScore(BaseModel):
    score: float
    signals: list[str]
    overall_sentiment: str
    news_volume: int
    key_themes: list[str]


class Recommendation(BaseModel):
    ticker: str
    action: Literal["BUY", "SELL", "HOLD"]
    confidence: float
    technical_score: float
    sentiment_score: float
    fundamental_score: float
    debate_score: float
    composite_score: float
    reasoning: list[str]
    allocation_pct: float
    risk_level: str
    target_price: float | None = None
    stop_loss: float | None = None
    timestamp: datetime = Field(default_factory=_now)


class AnalysisResult(BaseModel):
    ticker: str
    market_data: MarketData
    ohlcv: list[OHLCV]
    indicators: TechnicalIndicators
    news: list[NewsArticle]
    debate: DebateResult
    recommendation: Recommendation
    agent_log: list[AgentEvent]


class AgentStatus(BaseModel):
    id: str
    name: str
    status: str
    connections: list[str]
    last_event: str | None = None
