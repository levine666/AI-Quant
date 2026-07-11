"""海龟交易法则策略（Donchian 突破 + ATR 止损，仅做多）。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..strategy import Strategy


def _compute_tr(df: pd.DataFrame) -> pd.Series:
    prev_close = df["close"].shift(1)
    parts = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    )
    return parts.max(axis=1)


def _wilder_atr(df: pd.DataFrame, period: int) -> pd.Series:
    tr = _compute_tr(df)
    return tr.ewm(alpha=1 / period, adjust=False).mean()


@dataclass
class TurtleStrategy(Strategy):
    entry_period: int = 20
    exit_period: int = 10
    atr_period: int = 20
    stop_n_multiplier: float = 2.0

    def __post_init__(self) -> None:
        if self.entry_period <= self.exit_period:
            raise ValueError(
                f"entry_period({self.entry_period}) 必须大于 exit_period({self.exit_period})"
            )
        if self.atr_period < 5:
            raise ValueError(f"atr_period({self.atr_period}) 至少为 5")
        if self.stop_n_multiplier <= 0:
            raise ValueError("stop_n_multiplier 必须为正")

    @property
    def name(self) -> str:
        return (
            f"Turtle({self.entry_period}/{self.exit_period},"
            f"N={self.atr_period},{self.stop_n_multiplier}x)"
        )

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        ep, xp, ap = self.entry_period, self.exit_period, self.atr_period

        out["donchian_entry_high"] = (
            out["high"].rolling(ep, min_periods=ep).max().shift(1)
        )
        out["donchian_exit_low"] = (
            out["low"].rolling(xp, min_periods=xp).min().shift(1)
        )
        out["atr_n"] = _wilder_atr(out, ap)

        closes = out["close"].values
        entry_high = out["donchian_entry_high"].values
        exit_low = out["donchian_exit_low"].values
        atr_n = out["atr_n"].values
        n = len(out)

        target = np.zeros(n, dtype=float)
        buy = np.zeros(n, dtype=bool)
        sell = np.zeros(n, dtype=bool)
        stop_price = np.full(n, np.nan)

        in_position = False
        active_stop = np.nan

        for i in range(n):
            if not in_position:
                eh = entry_high[i]
                if not np.isnan(eh) and closes[i] > eh:
                    buy[i] = True
                    in_position = True
                    atr_val = atr_n[i] if not np.isnan(atr_n[i]) else atr_n[i - 1]
                    active_stop = closes[i] - self.stop_n_multiplier * atr_val
            else:
                stop_price[i] = active_stop
                exit_now = False
                el = exit_low[i]
                if not np.isnan(el) and closes[i] < el:
                    exit_now = True
                if not np.isnan(active_stop) and closes[i] < active_stop:
                    exit_now = True
                if exit_now:
                    sell[i] = True
                    in_position = False
                    active_stop = np.nan

            target[i] = 1.0 if in_position else 0.0

        out["target_position"] = target
        out["buy_signal"] = buy
        out["sell_signal"] = sell
        out["stop_price"] = stop_price
        return out
