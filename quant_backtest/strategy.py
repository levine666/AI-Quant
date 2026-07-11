"""策略基类：子类只需实现 generate_signals。"""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


class Strategy(ABC):
    """策略接口。

    子类在 generate_signals 中返回至少包含 target_position 列的 DataFrame：
    - target_position: 当日收盘后决定的理想仓位（0=空仓，1=全多；可扩展为 -1~1）
    - buy_signal / sell_signal: 可选，用于可视化与统计
    """

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        ...
