from __future__ import annotations

import io
import logging
from datetime import datetime, timedelta

import httpx
import pandas as pd

from app.config import settings
from app.schemas import MarketData, OHLCV

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
}


async def get_ohlcv(ticker: str, days: int = 365) -> list[OHLCV]:
    """Fetch OHLCV data from Stooq — no API key required."""
    sym = ticker.upper().replace(".", "-") + ".US"
    url = f"https://stooq.com/q/d/l/?s={sym}&i=d"

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        resp = await client.get(url, headers=_HEADERS)
        resp.raise_for_status()

    content = resp.text.strip()
    if not content or "No data" in content or len(content) < 50:
        sym_plain = ticker.upper().replace(".", "-")
        url2 = f"https://stooq.com/q/d/l/?s={sym_plain}&i=d"
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(url2, headers=_HEADERS)
            resp.raise_for_status()
        content = resp.text.strip()

    df = pd.read_csv(io.StringIO(content), parse_dates=["Date"])
    df = df.sort_values("Date", ascending=True)

    cutoff = datetime.utcnow() - timedelta(days=days)
    df = df[df["Date"] >= cutoff]

    result: list[OHLCV] = []
    for _, row in df.iterrows():
        try:
            result.append(
                OHLCV(
                    ticker=ticker.upper(),
                    timestamp=row["Date"].to_pydatetime(),
                    open=float(row["Open"]),
                    high=float(row["High"]),
                    low=float(row["Low"]),
                    close=float(row["Close"]),
                    volume=int(row.get("Volume", 0) or 0),
                    adjusted_close=float(row.get("Close", row["Close"])),
                )
            )
        except Exception as e:
            logger.debug("Skipping bad row: %s", e)

    return result


async def _get_finnhub_quote(ticker: str) -> dict:
    """Fetch real-time quote from Finnhub."""
    if not settings.finnhub_api_key:
        return {}
    url = f"https://finnhub.io/api/v1/quote"
    params = {"symbol": ticker.upper(), "token": settings.finnhub_api_key}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
        data = resp.json()
        # c=current, d=change, dp=change_pct, h=high, l=low, o=open, pc=prev_close, v=volume (not in Finnhub quote)
        return data
    except Exception as exc:
        logger.warning("Finnhub quote failed for %s: %s", ticker, exc)
        return {}


async def _get_finnhub_profile(ticker: str) -> dict:
    """Fetch company profile from Finnhub (sector, industry, name, market cap)."""
    if not settings.finnhub_api_key:
        return {}
    url = "https://finnhub.io/api/v1/stock/profile2"
    params = {"symbol": ticker.upper(), "token": settings.finnhub_api_key}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.warning("Finnhub profile failed for %s: %s", ticker, exc)
        return {}


async def _get_fmp_fundamentals(ticker: str) -> dict:
    """Fetch P/E, EPS, beta, 52w high/low from FMP."""
    if not settings.fmp_api_key:
        return {}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            # Key stats endpoint
            url = f"https://financialmodelingprep.com/api/v3/key-metrics-ttm/{ticker.upper()}"
            resp = await client.get(url, params={"apikey": settings.fmp_api_key})
            resp.raise_for_status()
            metrics_list = resp.json()
            metrics = metrics_list[0] if metrics_list else {}

            # Quote endpoint for beta + 52w high/low
            url2 = f"https://financialmodelingprep.com/api/v3/quote/{ticker.upper()}"
            resp2 = await client.get(url2, params={"apikey": settings.fmp_api_key})
            resp2.raise_for_status()
            quote_list = resp2.json()
            quote = quote_list[0] if quote_list else {}

        return {"metrics": metrics, "quote": quote}
    except Exception as exc:
        logger.warning("FMP fundamentals failed for %s: %s", ticker, exc)
        return {}


async def get_market_data(ticker: str, ohlcv: list[OHLCV] | None = None) -> MarketData:
    """
    Fetch market data:
    - Real-time price/change: Finnhub /quote
    - Company name, sector, industry, market_cap: Finnhub /stock/profile2
    - PE ratio, EPS, beta, 52w high/low: FMP key-metrics-ttm + quote
    """
    import asyncio
    quote_data, profile_data, fmp_data = await asyncio.gather(
        _get_finnhub_quote(ticker),
        _get_finnhub_profile(ticker),
        _get_fmp_fundamentals(ticker),
    )

    # Finnhub quote fields: c, d, dp, h, l, o, pc
    price = quote_data.get("c") or None
    change = quote_data.get("d") or None
    change_pct = quote_data.get("dp") or None

    # Fallback to OHLCV if Finnhub unavailable
    if (price is None or price == 0) and ohlcv:
        last = ohlcv[-1]
        price = last.close
        if len(ohlcv) >= 2:
            prev = ohlcv[-2].close
            change = price - prev
            change_pct = (change / prev) * 100 if prev else 0.0
        else:
            change = 0.0
            change_pct = 0.0

    # Volume from FMP quote (Finnhub /quote doesn't include volume)
    fmp_quote = fmp_data.get("quote", {})
    fmp_metrics = fmp_data.get("metrics", {})
    volume = int(fmp_quote.get("volume") or (ohlcv[-1].volume if ohlcv else 0))

    # Market cap from Finnhub profile (in millions) or FMP
    market_cap_fh = profile_data.get("marketCapitalization")
    market_cap = float(market_cap_fh) * 1_000_000 if market_cap_fh else fmp_quote.get("marketCap")

    # PE, EPS from FMP
    pe_ratio = fmp_metrics.get("peRatioTTM") or fmp_quote.get("pe")
    eps = fmp_metrics.get("epsTTM") or fmp_quote.get("eps")

    # Beta, 52w from FMP quote
    beta = fmp_quote.get("beta")
    week_52_high = fmp_quote.get("yearHigh")
    week_52_low = fmp_quote.get("yearLow")

    # Company info from Finnhub profile
    name = profile_data.get("name") or fmp_quote.get("name")
    sector = profile_data.get("finnhubIndustry") or fmp_quote.get("sector")
    industry = profile_data.get("finnhubIndustry")

    def _safe_float(v) -> float | None:
        try:
            return float(v) if v is not None else None
        except (TypeError, ValueError):
            return None

    return MarketData(
        ticker=ticker.upper(),
        price=float(price or 0.0),
        change=float(change or 0.0),
        change_pct=float(change_pct or 0.0),
        volume=volume,
        market_cap=_safe_float(market_cap),
        pe_ratio=_safe_float(pe_ratio),
        eps=_safe_float(eps),
        beta=_safe_float(beta),
        week_52_high=_safe_float(week_52_high),
        week_52_low=_safe_float(week_52_low),
        sector=sector,
        industry=industry,
        name=name,
    )
