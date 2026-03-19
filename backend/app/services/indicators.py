from __future__ import annotations

import logging
from datetime import datetime

import numpy as np
import pandas as pd
import ta.momentum as ta_momentum
import ta.trend as ta_trend
import ta.volatility as ta_vol
import ta.volume as ta_volume

from app.schemas import OHLCV, TechnicalIndicators

logger = logging.getLogger(__name__)


def compute_indicators(ohlcv_list: list[OHLCV]) -> tuple[TechnicalIndicators, pd.DataFrame]:
    """
    Compute technical indicators from OHLCV data.
    Returns (last bar TechnicalIndicators, full DataFrame with all indicator columns).
    """
    if len(ohlcv_list) < 30:
        raise ValueError(f"Need at least 30 bars to compute indicators, got {len(ohlcv_list)}")

    df = pd.DataFrame(
        [
            {
                "timestamp": bar.timestamp,
                "open": bar.open,
                "high": bar.high,
                "low": bar.low,
                "close": bar.close,
                "volume": float(bar.volume),
            }
            for bar in ohlcv_list
        ]
    ).sort_values("timestamp", ascending=True).reset_index(drop=True)

    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    # EMAs
    df["ema_9"] = ta_trend.EMAIndicator(close=close, window=9).ema_indicator()
    df["ema_21"] = ta_trend.EMAIndicator(close=close, window=21).ema_indicator()
    df["ema_50"] = ta_trend.EMAIndicator(close=close, window=50).ema_indicator()
    df["ema_200"] = ta_trend.EMAIndicator(close=close, window=200).ema_indicator()

    # RSI
    df["rsi_14"] = ta_momentum.RSIIndicator(close=close, window=14).rsi()

    # MACD
    macd_ind = ta_trend.MACD(close=close, window_slow=26, window_fast=12, window_sign=9)
    df["macd"] = macd_ind.macd()
    df["macd_signal"] = macd_ind.macd_signal()
    df["macd_hist"] = macd_ind.macd_diff()

    # ATR
    df["atr"] = ta_vol.AverageTrueRange(high=high, low=low, close=close, window=14).average_true_range()

    # Bollinger Bands
    bb = ta_vol.BollingerBands(close=close, window=20, window_dev=2)
    df["bb_upper"] = bb.bollinger_hband()
    df["bb_middle"] = bb.bollinger_mavg()
    df["bb_lower"] = bb.bollinger_lband()
    df["bb_pct"] = bb.bollinger_pband()

    # ADX
    df["adx"] = ta_trend.ADXIndicator(high=high, low=low, close=close, window=14).adx()

    # OBV
    df["obv"] = ta_volume.OnBalanceVolumeIndicator(close=close, volume=volume).on_balance_volume()

    # VWAP
    try:
        df["vwap"] = ta_volume.VolumeWeightedAveragePrice(
            high=high, low=low, close=close, volume=volume, window=14
        ).volume_weighted_average_price()
    except Exception:
        df["vwap"] = (high + low + close) / 3

    # Volume Z-score
    vol_mean = volume.rolling(20).mean()
    vol_std = volume.rolling(20).std()
    df["volume_zscore"] = (volume - vol_mean) / vol_std.replace(0, np.nan)

    # Support / Resistance
    df["support"] = low.rolling(20).min()
    df["resistance"] = high.rolling(20).max()

    # Trend direction
    df["trend_direction"] = np.where(close > df["ema_50"], 1, -1)

    # Extract last row
    last = df.iloc[-1]

    def _f(col: str) -> float | None:
        val = last.get(col)
        if val is None or (isinstance(val, float) and np.isnan(val)):
            return None
        return float(val)

    indicators = TechnicalIndicators(
        ticker=ohlcv_list[-1].ticker,
        timestamp=datetime.utcnow(),
        ema_9=_f("ema_9"),
        ema_21=_f("ema_21"),
        ema_50=_f("ema_50"),
        ema_200=_f("ema_200"),
        rsi_14=_f("rsi_14"),
        macd=_f("macd"),
        macd_signal=_f("macd_signal"),
        macd_hist=_f("macd_hist"),
        atr=_f("atr"),
        bb_upper=_f("bb_upper"),
        bb_middle=_f("bb_middle"),
        bb_lower=_f("bb_lower"),
        bb_pct=_f("bb_pct"),
        adx=_f("adx"),
        obv=_f("obv"),
        vwap=_f("vwap"),
        volume_zscore=_f("volume_zscore"),
        support=_f("support"),
        resistance=_f("resistance"),
        trend_direction=int(last.get("trend_direction", 0) or 0),
    )

    return indicators, df


async def get_ohlcv_with_indicators(ticker: str, days: int = 365) -> pd.DataFrame:
    """Convenience async wrapper: returns full DataFrame with indicators."""
    from app.services.market_data import get_ohlcv

    ohlcv = await get_ohlcv(ticker, days=days)
    _, df = compute_indicators(ohlcv)
    return df
