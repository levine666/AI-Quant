"""回测配置。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BacktestConfig:
    """回测全局配置。"""

    initial_capital: float = 100_000.0
    trading_days: int = 252
    commission_rate: float = 0.0003   # 单边手续费率，0.0003=万三
    slippage_rate: float = 0.0005     # 滑点率，买入加价/卖出减价
    position_lag: int = 1             # 信号延迟 bar 数，1=次日执行
    price_col: str = "close"
    open_col: str = "open"
    date_col: str = "date"
    start_date: str | None = None     # 回测起始日 YYYY-MM-DD（含）
    end_date: str | None = None       # 回测结束日 YYYY-MM-DD（含）
