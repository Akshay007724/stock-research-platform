from __future__ import annotations

import json
import logging

from app.mcp.bus import MCPBus
from app.services.llm import get_client, get_model, provider_label
from app.mcp.registry import registry
from app.schemas import AgentEvent, DebateResult, MarketData, Recommendation, SentimentScore, TechnicalIndicators

logger = logging.getLogger(__name__)


def _compute_technical_score(indicators: TechnicalIndicators) -> tuple[float, list[str]]:
    score = 50.0
    signals: list[str] = []

    # RSI zone
    rsi = indicators.rsi_14
    if rsi is not None:
        if rsi < 30:
            score += 15
            signals.append(f"RSI oversold at {rsi:.1f} — potential reversal signal")
        elif rsi < 45:
            score += 7
            signals.append(f"RSI at {rsi:.1f} — mildly oversold territory")
        elif rsi > 70:
            score -= 15
            signals.append(f"RSI overbought at {rsi:.1f} — caution advised")
        elif rsi > 55:
            score += 5
            signals.append(f"RSI at {rsi:.1f} — moderate bullish momentum")

    # MACD direction
    macd = indicators.macd
    macd_signal = indicators.macd_signal
    if macd is not None and macd_signal is not None:
        if macd > macd_signal:
            score += 10
            signals.append("MACD above signal line — bullish crossover")
        else:
            score -= 10
            signals.append("MACD below signal line — bearish crossover")

    # EMA alignment (bullish if 9 > 21 > 50 > 200)
    ema9 = indicators.ema_9
    ema21 = indicators.ema_21
    ema50 = indicators.ema_50
    ema200 = indicators.ema_200
    close = None
    if ema50 is not None:
        if indicators.trend_direction == 1:
            score += 8
            signals.append("Price above EMA-50 — uptrend confirmed")
        else:
            score -= 8
            signals.append("Price below EMA-50 — downtrend warning")

    if ema9 is not None and ema21 is not None and ema50 is not None:
        if ema9 > ema21 > ema50:
            score += 7
            signals.append("EMA 9 > 21 > 50 — short-term momentum bullish")
        elif ema9 < ema21 < ema50:
            score -= 7
            signals.append("EMA 9 < 21 < 50 — short-term momentum bearish")

    # ADX strength
    adx = indicators.adx
    if adx is not None:
        if adx > 25:
            score += 5
            signals.append(f"ADX at {adx:.1f} — strong trend detected")
        elif adx < 15:
            score -= 3
            signals.append(f"ADX at {adx:.1f} — weak trend, sideways market")

    # Bollinger Band %
    bb_pct = indicators.bb_pct
    if bb_pct is not None:
        if bb_pct < 0.2:
            score += 5
            signals.append(f"Price near lower Bollinger Band ({bb_pct:.2f}) — oversold")
        elif bb_pct > 0.8:
            score -= 5
            signals.append(f"Price near upper Bollinger Band ({bb_pct:.2f}) — overbought")

    return max(0.0, min(100.0, score)), signals


def _compute_fundamental_score(market_data: MarketData) -> tuple[float, list[str], str, str, str]:
    score = 50.0
    signals: list[str] = []

    pe = market_data.pe_ratio
    pe_analysis = "P/E data not available"
    if pe is not None:
        if pe <= 0:
            score -= 10
            pe_analysis = f"Negative P/E ({pe:.1f}) — company not currently profitable"
            signals.append("Negative earnings — fundamental red flag")
        elif pe < 15:
            score += 15
            pe_analysis = f"Low P/E of {pe:.1f} — potentially undervalued"
            signals.append(f"Low P/E ratio ({pe:.1f}) suggests undervaluation")
        elif pe < 25:
            score += 5
            pe_analysis = f"Moderate P/E of {pe:.1f} — fairly valued"
            signals.append(f"P/E ratio of {pe:.1f} is within reasonable range")
        elif pe < 40:
            score -= 5
            pe_analysis = f"Elevated P/E of {pe:.1f} — growth premium priced in"
            signals.append(f"High P/E of {pe:.1f} — significant growth expectations baked in")
        else:
            score -= 15
            pe_analysis = f"Very high P/E of {pe:.1f} — significant overvaluation risk"
            signals.append(f"Extreme P/E of {pe:.1f} — bubble territory risk")

    beta = market_data.beta
    risk_assessment = "Beta data not available"
    if beta is not None:
        if beta < 0.5:
            score += 5
            risk_assessment = f"Low beta ({beta:.2f}) — defensive, low volatility stock"
        elif beta <= 1.2:
            risk_assessment = f"Market-neutral beta ({beta:.2f}) — moves with market"
        elif beta <= 2.0:
            score -= 5
            risk_assessment = f"High beta ({beta:.2f}) — amplified market movements"
            signals.append(f"Elevated beta of {beta:.2f} increases volatility risk")
        else:
            score -= 10
            risk_assessment = f"Very high beta ({beta:.2f}) — highly speculative"
            signals.append(f"Very high beta ({beta:.2f}) — significant volatility risk")

    # 52-week position
    w52_high = market_data.week_52_high
    w52_low = market_data.week_52_low
    price = market_data.price
    growth_analysis = "52-week range data not available"
    if w52_high and w52_low and price:
        range_pct = (price - w52_low) / (w52_high - w52_low) * 100 if (w52_high - w52_low) > 0 else 50
        growth_analysis = f"Currently at {range_pct:.0f}% of 52-week range (${w52_low:.2f} - ${w52_high:.2f})"
        if range_pct < 30:
            score += 10
            signals.append(f"Near 52-week low — potential value opportunity")
        elif range_pct > 80:
            score -= 5
            signals.append(f"Near 52-week high — limited upside in near term")

    return max(0.0, min(100.0, score)), signals, pe_analysis, growth_analysis, risk_assessment


async def run(
    ticker: str,
    market_data: MarketData,
    indicators: TechnicalIndicators,
    sentiment: SentimentScore,
    debate: DebateResult,
    bus: MCPBus,
) -> Recommendation:
    """Recommendation Engine: synthesizes all agent outputs into a final recommendation."""
    agent = "recommender"

    await registry.set_status(agent, "running", bus._redis, f"Computing recommendation for {ticker}")
    await bus.publish(
        ticker,
        AgentEvent(
            agent_name=agent,
            event_type="start",
            message=f"Computing final recommendation for {ticker}",
        ),
    )

    try:
        # Technical score
        await bus.publish(ticker, AgentEvent(agent_name=agent, event_type="progress", message="Scoring technical indicators..."))
        technical_score, tech_signals = _compute_technical_score(indicators)

        # Sentiment score (map -1..1 to 0..100)
        sentiment_score_normalized = (sentiment.score + 1.0) / 2.0 * 100.0
        sentiment_score_normalized = max(0.0, min(100.0, sentiment_score_normalized))

        # Fundamental score
        await bus.publish(ticker, AgentEvent(agent_name=agent, event_type="progress", message="Scoring fundamental metrics..."))
        fundamental_score, fund_signals, pe_analysis, growth_analysis, risk_assessment = _compute_fundamental_score(market_data)

        # Debate score (0-10 verdict_score → 0-100)
        debate_score = debate.verdict_score * 10.0

        # Composite weighted score
        composite = (
            0.30 * technical_score
            + 0.25 * sentiment_score_normalized
            + 0.25 * fundamental_score
            + 0.20 * debate_score
        )
        composite = max(0.0, min(100.0, composite))

        # Action determination
        if composite >= 65:
            action = "BUY"
        elif composite <= 35:
            action = "SELL"
        else:
            action = "HOLD"

        # Allocation
        if composite >= 80:
            allocation_pct = 5.0
        elif composite >= 65:
            allocation_pct = 3.0
        elif composite >= 50:
            allocation_pct = 1.0
        else:
            allocation_pct = 0.0

        # Risk level
        beta = market_data.beta
        if beta is not None:
            if beta > 1.5:
                risk_level = "HIGH"
            elif beta > 0.8:
                risk_level = "MEDIUM"
            else:
                risk_level = "LOW"
        else:
            risk_level = "MEDIUM"

        # Target price and stop loss from technical levels
        price = market_data.price
        target_price: float | None = None
        stop_loss: float | None = None

        if indicators.resistance and price and indicators.resistance > price:
            target_price = round(indicators.resistance, 2)
        elif price and indicators.ema_50:
            target_price = round(price * 1.10, 2)

        if indicators.support and price and indicators.support < price:
            stop_loss = round(indicators.support, 2)
        elif price and indicators.atr:
            stop_loss = round(price - 2 * indicators.atr, 2)

        await bus.publish(
            ticker,
            AgentEvent(
                agent_name=agent,
                event_type="progress",
                message=f"Scores: Technical={technical_score:.1f}, Sentiment={sentiment_score_normalized:.1f}, Fundamental={fundamental_score:.1f}, Debate={debate_score:.1f}",
                data={
                    "technical_score": technical_score,
                    "sentiment_score": sentiment_score_normalized,
                    "fundamental_score": fundamental_score,
                    "debate_score": debate_score,
                    "composite": composite,
                },
            ),
        )

        # Generate reasoning bullets via LLM
        reasoning: list[str] = []
        all_signals = tech_signals[:2] + fund_signals[:2] + sentiment.signals[:1] + [debate.moderator_summary[:150]]
        client = get_client()

        if client:
            try:
                llm_label = provider_label()
                await bus.publish(ticker, AgentEvent(agent_name=agent, event_type="progress", message=f"Generating investment rationale via {llm_label}..."))
                signals_text = "\n".join(f"- {s}" for s in all_signals if s)
                resp = await client.chat.completions.create(
                    model=get_model(),
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are a portfolio manager writing the investment rationale section of a research note. "
                                "Be specific, cite numbers, and explain the 'why' behind each point. "
                                "Return valid JSON only — a JSON array of strings, nothing else."
                            ),
                        },
                        {
                            "role": "user",
                            "content": (
                                f"Write 4 concise but specific investment rationale bullets for a {action} recommendation on {ticker}.\n"
                                f"Composite score: {composite:.1f}/100 | Technical: {technical_score:.0f} | Sentiment: {sentiment_score_normalized:.0f} | Fundamental: {fundamental_score:.0f} | Debate: {debate_score:.0f}\n\n"
                                f"Key signals:\n{signals_text}\n\n"
                                "Each bullet should be one clear sentence that a fund manager can act on. "
                                "Return ONLY a JSON array: [\"bullet1\", \"bullet2\", \"bullet3\", \"bullet4\"]"
                            ),
                        },
                    ],
                    temperature=0.3,
                    max_tokens=500,
                )
                content = resp.choices[0].message.content or "[]"
                start = content.find("[")
                end = content.rfind("]") + 1
                if start >= 0 and end > start:
                    reasoning = json.loads(content[start:end])
            except Exception as exc:
                logger.warning("Reasoning generation failed: %s", exc)

        if not reasoning:
            reasoning = [s for s in all_signals if s][:5]
            if not reasoning:
                reasoning = [f"Composite score of {composite:.1f} supports {action} recommendation"]

        await registry.set_status(agent, "done", bus._redis, f"Recommendation: {action} ({composite:.1f}/100)")
        await bus.publish(
            ticker,
            AgentEvent(
                agent_name=agent,
                event_type="complete",
                message=f"Final recommendation: {action} | Confidence: {composite:.1f}/100 | Allocation: {allocation_pct}%",
                data={"action": action, "composite": composite, "allocation_pct": allocation_pct},
            ),
        )

        return Recommendation(
            ticker=ticker.upper(),
            action=action,
            confidence=composite,
            technical_score=technical_score,
            sentiment_score=sentiment_score_normalized,
            fundamental_score=fundamental_score,
            debate_score=debate_score,
            composite_score=composite,
            reasoning=reasoning,
            allocation_pct=allocation_pct,
            risk_level=risk_level,
            target_price=target_price,
            stop_loss=stop_loss,
        )

    except Exception as exc:
        logger.exception("Recommender agent failed for %s: %s", ticker, exc)
        await registry.set_status(agent, "error", bus._redis, str(exc))
        await bus.publish(
            ticker,
            AgentEvent(
                agent_name=agent,
                event_type="error",
                message=f"Recommendation failed: {exc}",
            ),
        )
        raise
