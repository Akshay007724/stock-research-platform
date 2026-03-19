from __future__ import annotations

import asyncio
import json
import logging

from app.mcp.bus import MCPBus
from app.mcp.registry import registry
from app.schemas import AgentEvent, DebateArgument, DebateResult, MarketData, TechnicalIndicators
from app.services.llm import get_client, get_model, provider_label

logger = logging.getLogger(__name__)


def _build_market_summary(ticker: str, market_data: MarketData, indicators: TechnicalIndicators) -> str:
    lines = [
        f"Ticker: {ticker}",
        f"Company: {market_data.name or ticker}",
        f"Price: ${market_data.price:.2f} ({market_data.change_pct:+.2f}%)",
        f"Volume: {market_data.volume:,}",
        f"Market Cap: ${market_data.market_cap:,.0f}" if market_data.market_cap else "",
        f"P/E Ratio: {market_data.pe_ratio}" if market_data.pe_ratio else "",
        f"EPS: {market_data.eps}" if market_data.eps else "",
        f"Beta: {market_data.beta}" if market_data.beta else "",
        f"52W High: ${market_data.week_52_high}" if market_data.week_52_high else "",
        f"52W Low: ${market_data.week_52_low}" if market_data.week_52_low else "",
        f"Sector: {market_data.sector}" if market_data.sector else "",
        f"RSI-14: {indicators.rsi_14:.1f}" if indicators.rsi_14 else "",
        f"MACD: {indicators.macd:.3f}" if indicators.macd else "",
        f"ADX: {indicators.adx:.1f}" if indicators.adx else "",
        f"EMA-50: {indicators.ema_50:.2f}" if indicators.ema_50 else "",
        f"BB%: {indicators.bb_pct:.2f}" if indicators.bb_pct else "",
        f"ATR: {indicators.atr:.2f}" if indicators.atr else "",
        f"Support: ${indicators.support:.2f}" if indicators.support else "",
        f"Resistance: ${indicators.resistance:.2f}" if indicators.resistance else "",
        f"Trend: {'Uptrend' if indicators.trend_direction == 1 else 'Downtrend'}",
    ]
    return "\n".join(l for l in lines if l)


async def _run_bull_agent(ticker: str, summary: str, client) -> DebateArgument:
    prompt = (
        f"You are an experienced buy-side equity analyst building the strongest possible investment case for {ticker}.\n\n"
        f"Live market and technical data:\n{summary}\n\n"
        "Task: Construct 5 specific, data-driven BUY arguments. Each point must cite actual numbers from the data above. "
        "Avoid generic statements — every argument must be grounded in the provided metrics.\n\n"
        "Return ONLY valid JSON (no markdown, no preamble):\n"
        '{"points": ["<specific argument with numbers>", ...5 items...], '
        '"score": <float 0-10 reflecting conviction>, '
        '"key_metrics": {"<metric>": "<interpretation>"}}'
    )

    try:
        resp = await client.chat.completions.create(
            model=get_model(),
            messages=[
                {"role": "system", "content": "You are a senior buy-side equity analyst at a top hedge fund. You write precise, data-driven investment arguments. Always return valid JSON only — no markdown, no explanation outside the JSON."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.6,
            max_tokens=900,
        )
        content = resp.choices[0].message.content or "{}"
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(content[start:end])
            return DebateArgument(
                side="bull",
                points=data.get("points", ["Strong bullish case"]),
                score=float(data.get("score", 6.0)),
                key_metrics=data.get("key_metrics", {}),
            )
    except Exception as exc:
        logger.warning("Bull agent LLM call failed: %s", exc)

    return DebateArgument(
        side="bull",
        points=[
            "Price momentum indicates upward trend",
            "Technical indicators show buying pressure",
            "Market positioning looks favorable",
        ],
        score=6.0,
        key_metrics={},
    )


async def _run_bear_agent(ticker: str, summary: str, client) -> DebateArgument:
    prompt = (
        f"You are an experienced short-seller and risk analyst stress-testing the bear case for {ticker}.\n\n"
        f"Live market and technical data:\n{summary}\n\n"
        "Task: Construct 5 specific, data-driven SELL/AVOID arguments. Each point must cite actual numbers from the data above. "
        "Focus on valuation risk, technical breakdown signals, and downside scenarios. "
        "Avoid generic statements — every argument must be grounded in the provided metrics.\n\n"
        "Return ONLY valid JSON (no markdown, no preamble):\n"
        '{"points": ["<specific argument with numbers>", ...5 items...], '
        '"score": <float 0-10 reflecting conviction>, '
        '"key_metrics": {"<metric>": "<risk interpretation>"}}'
    )

    try:
        resp = await client.chat.completions.create(
            model=get_model(),
            messages=[
                {"role": "system", "content": "You are a senior short-seller and risk analyst at a top hedge fund. You write precise, data-driven risk arguments. Always return valid JSON only — no markdown, no explanation outside the JSON."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.6,
            max_tokens=900,
        )
        content = resp.choices[0].message.content or "{}"
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(content[start:end])
            return DebateArgument(
                side="bear",
                points=data.get("points", ["Significant downside risk"]),
                score=float(data.get("score", 5.0)),
                key_metrics=data.get("key_metrics", {}),
            )
    except Exception as exc:
        logger.warning("Bear agent LLM call failed: %s", exc)

    return DebateArgument(
        side="bear",
        points=[
            "Valuation appears stretched",
            "Momentum shows signs of weakening",
            "Risk/reward unfavorable at current levels",
        ],
        score=5.0,
        key_metrics={},
    )


async def _run_moderator(ticker: str, bull: DebateArgument, bear: DebateArgument, client) -> tuple[str, float, str]:
    bull_points = "\n".join(f"  {i+1}. {p}" for i, p in enumerate(bull.points))
    bear_points = "\n".join(f"  {i+1}. {p}" for i, p in enumerate(bear.points))

    prompt = (
        f"You are a CFA-certified portfolio manager moderating an investment debate on {ticker}.\n\n"
        f"BULL CASE (self-score: {bull.score:.1f}/10):\n{bull_points}\n\n"
        f"BEAR CASE (self-score: {bear.score:.1f}/10):\n{bear_points}\n\n"
        "Evaluate the quality of each argument's evidence and logic independently. "
        "Determine which case is better supported by the data. Your verdict_score should reflect the balance of evidence, "
        "not just which side has more points. Write a 2-3 sentence summary that a fund manager could read before making a decision.\n\n"
        "Return ONLY valid JSON:\n"
        '{"verdict": "bull" | "bear" | "neutral", '
        '"verdict_score": <float 0-10: 10=strong bull, 5=neutral, 0=strong bear>, '
        '"moderator_summary": "<concise, specific 2-3 sentence summary citing key evidence>"}'
    )

    try:
        resp = await client.chat.completions.create(
            model=get_model(),
            messages=[
                {"role": "system", "content": "You are a CFA-certified portfolio manager and objective investment debate moderator. Evaluate arguments on evidence quality, not quantity. Always return valid JSON only — no markdown, no text outside JSON."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=600,
        )
        content = resp.choices[0].message.content or "{}"
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(content[start:end])
            verdict = data.get("verdict", "neutral")
            if verdict not in ("bull", "bear", "neutral"):
                verdict = "neutral"
            return verdict, float(data.get("verdict_score", 5.0)), data.get("moderator_summary", "")
    except Exception as exc:
        logger.warning("Moderator LLM call failed: %s", exc)

    return "neutral", 5.0, f"Both bull and bear cases presented valid arguments for {ticker}."


async def run(ticker: str, market_data: MarketData, indicators: TechnicalIndicators, bus: MCPBus) -> DebateResult:
    """Debate Agent: runs bull vs bear debate with a moderator."""
    client = get_client()
    llm_label = provider_label()

    summary = _build_market_summary(ticker, market_data, indicators)

    await registry.set_status("debate_bull", "running", bus._redis, f"Preparing bull case for {ticker}")
    await registry.set_status("debate_bear", "running", bus._redis, f"Preparing bear case for {ticker}")

    await bus.publish(
        ticker,
        AgentEvent(
            agent_name="debate_bull",
            event_type="start",
            message=f"Bull agent building investment case for {ticker} via {llm_label}",
        ),
    )
    await bus.publish(
        ticker,
        AgentEvent(
            agent_name="debate_bear",
            event_type="start",
            message=f"Bear agent building risk case for {ticker} via {llm_label}",
        ),
    )

    # Run bull and bear in parallel
    if client:
        bull_task = _run_bull_agent(ticker, summary, client)
        bear_task = _run_bear_agent(ticker, summary, client)
        bull, bear = await asyncio.gather(bull_task, bear_task)
    else:
        # Fallback without OpenAI
        bull = DebateArgument(
            side="bull",
            points=[
                "Price is currently in an upward channel",
                "Volume is supporting the move higher",
                "Fundamental valuation is reasonable for sector",
                "Technical momentum indicators are positive",
                "Market conditions favor growth stocks",
            ],
            score=6.5,
            key_metrics={"trend": "bullish", "rsi": str(indicators.rsi_14)},
        )
        bear = DebateArgument(
            side="bear",
            points=[
                "Valuation premium may not be justified",
                "Market sentiment is volatile",
                "Resistance levels could cap upside",
                "Macro headwinds remain a concern",
                "Risk/reward not optimal at current price",
            ],
            score=5.5,
            key_metrics={"trend": "cautious", "pe": str(market_data.pe_ratio)},
        )

    await registry.set_status("debate_bull", "done", bus._redis, f"Bull score: {bull.score}/10")
    await registry.set_status("debate_bear", "done", bus._redis, f"Bear score: {bear.score}/10")

    await bus.publish(
        ticker,
        AgentEvent(
            agent_name="debate_bull",
            event_type="complete",
            message=f"Bull case complete: score {bull.score}/10",
            data={"score": bull.score, "points_count": len(bull.points)},
        ),
    )
    await bus.publish(
        ticker,
        AgentEvent(
            agent_name="debate_bear",
            event_type="complete",
            message=f"Bear case complete: score {bear.score}/10",
            data={"score": bear.score, "points_count": len(bear.points)},
        ),
    )

    # Moderator evaluation
    await registry.set_status("debate_moderator", "running", bus._redis, "Evaluating debate...")
    await bus.publish(
        ticker,
        AgentEvent(
            agent_name="debate_moderator",
            event_type="start",
            message=f"Moderator evaluating bull vs bear debate for {ticker}",
        ),
    )

    if client:
        verdict, verdict_score, summary_text = await _run_moderator(ticker, bull, bear, client)
    else:
        # Score-based fallback
        if bull.score > bear.score + 1:
            verdict = "bull"
            verdict_score = 6.5
            summary_text = f"The bull case presents stronger arguments for {ticker} based on technical and fundamental factors."
        elif bear.score > bull.score + 1:
            verdict = "bear"
            verdict_score = 3.5
            summary_text = f"The bear case highlights significant risks for {ticker} that investors should consider."
        else:
            verdict = "neutral"
            verdict_score = 5.0
            summary_text = f"Both bull and bear cases for {ticker} are balanced, suggesting a cautious approach."

    await registry.set_status("debate_moderator", "done", bus._redis, f"Verdict: {verdict}")
    await bus.publish(
        ticker,
        AgentEvent(
            agent_name="debate_moderator",
            event_type="complete",
            message=f"Debate verdict: {verdict.upper()} (score: {verdict_score:.1f}/10)",
            data={"verdict": verdict, "score": verdict_score},
        ),
    )

    return DebateResult(
        ticker=ticker.upper(),
        bull=bull,
        bear=bear,
        verdict=verdict,
        verdict_score=verdict_score,
        moderator_summary=summary_text,
    )
