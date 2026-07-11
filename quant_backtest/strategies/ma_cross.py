"""双均线交叉策略（SMA）。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..strategy import Strategy


@dataclass
class DualMACrossStrategy(Strategy):
    short: int = 5
    long: int = 15
    price_col: str = "close"

    def __post_init__(self) -> None:
        if self.short >= self.long:
            raise ValueError(f"short({self.short}) 必须小于 long({self.long})")

    @property
    def name(self) -> str:
        return f"DualMA({self.short},{self.long})"

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        out["ma_short"] = out[self.price_col].rolling(self.short, min_periods=self.short).mean()
        out["ma_long"] = out[self.price_col].rolling(self.long, min_periods=self.long).mean()

        prev_short = out["ma_short"].shift(1)
        prev_long = out["ma_long"].shift(1)
        out["buy_signal"] = (out["ma_short"] > out["ma_long"]) & (prev_short <= prev_long)
        out["sell_signal"] = (out["ma_short"] < out["ma_long"]) & (prev_short >= prev_long)

        # 趋势跟踪：短均线在上则持多；延迟执行由引擎 position_lag 处理
        out["target_position"] = np.where(out["ma_short"] > out["ma_long"], 1.0, 0.0)
        return out
