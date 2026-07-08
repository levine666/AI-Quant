"""技术指标计算函数（Wilder 平滑 RSI/ATR，标准 MACD/BOLL）。"""

from __future__ import annotations

import numpy as np
import pandas as pd


def compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - 100 / (1 + rs)
    return rsi.astype(float)


def compute_macd(
    close: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> pd.DataFrame:
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=signal, adjust=False).mean()
    hist = dif - dea
    return pd.DataFrame({"macd_dif": dif, "macd_dea": dea, "macd_hist": hist})


def compute_bollinger(
    close: pd.Series,
    period: int = 20,
    std_multiplier: float = 2.0,
) -> pd.DataFrame:
    mid = close.rolling(window=period).mean()
    std = close.rolling(window=period).std()
    upper = mid + std_multiplier * std
    lower = mid - std_multiplier * std
    width = (upper - lower) / mid
    return pd.DataFrame(
        {
            "boll_mid": mid,
            "boll_upper": upper,
            "boll_lower": lower,
            "boll_width": width,
        }
    )


def compute_atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14,
) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1 / period, adjust=False).mean().astype(float).rename("atr_14")


def add_all_indicators(df: pd.DataFrame, params: dict | None = None) -> pd.DataFrame:
    """在 OHLCV DataFrame 上追加全部指标列。"""
    p = params or {}
    rsi_p = p.get("rsi_period", 14)

    macd_p = p.get("macd", {})
    macd_fast = macd_p.get("fast", macd_p.get("fast_period", 12))
    macd_slow = macd_p.get("slow", macd_p.get("slow_period", 26))
    macd_signal = macd_p.get("signal", macd_p.get("signal_period", 9))

    boll_p = p.get("boll", {})
    boll_period = boll_p.get("period", 20)
    boll_std = boll_p.get("std_multiplier", 2.0)

    atr_p = p.get("atr_period", 14)

    out = df.copy()
    out["rsi_14"] = compute_rsi(out["close"], rsi_p)
    out = out.join(
        compute_macd(out["close"], macd_fast, macd_slow, macd_signal)
    )
    out = out.join(compute_bollinger(out["close"], boll_period, boll_std))
    out["atr_14"] = compute_atr(out["high"], out["low"], out["close"], atr_p)
    return out
