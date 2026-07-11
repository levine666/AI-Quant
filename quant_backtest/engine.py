"""回测核心引擎。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from .config import BacktestConfig
from .metrics import compute_metrics
from .simulator import apply_date_window, attach_returns, simulate_buy_hold_equity, simulate_strategy_equity
from .strategy import Strategy


@dataclass
class BacktestResult:
    """单次回测输出。"""

    strategy_name: str
    config: BacktestConfig
    metrics: dict[str, Any]
    dataframe: pd.DataFrame
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self, *, include_dataframe: bool = False) -> dict[str, Any]:
        cfg = self.config
        out = {
            "strategy": self.strategy_name,
            "metrics": self.metrics,
            "meta": self.meta,
            "config": {
                "initial_capital": cfg.initial_capital,
                "trading_days": cfg.trading_days,
                "commission_rate": cfg.commission_rate,
                "slippage_rate": cfg.slippage_rate,
                "position_lag": cfg.position_lag,
                "start_date": cfg.start_date,
                "end_date": cfg.end_date,
            },
        }
        if include_dataframe:
            out["dataframe"] = self.dataframe
        return out


class BacktestEngine:
    """通用日频回测引擎。

    流程：截取日期窗口 → 策略信号 → 延迟持仓 → 开平仓模拟（手续费+滑点）
         → 买入持有基准 → 绩效指标。
    """

    def __init__(self, config: BacktestConfig | None = None):
        self.config = config or BacktestConfig()

    def run(
        self,
        df: pd.DataFrame,
        strategy: Strategy,
        *,
        meta: dict[str, Any] | None = None,
    ) -> BacktestResult:
        cfg = self.config
        data = self._prepare_data(df)
        if len(data) < 2:
            raise ValueError("回测区间至少需要 2 个交易日")

        signed = strategy.generate_signals(data)
        if "target_position" not in signed.columns:
            raise ValueError(f"策略 {strategy.name} 必须输出 target_position 列")

        signed["position"] = signed["target_position"].shift(cfg.position_lag).fillna(0)
        signed["equity"] = simulate_strategy_equity(signed, signed["position"], cfg)
        signed["bh_equity"] = simulate_buy_hold_equity(signed, cfg)
        signed = attach_returns(signed, cfg)

        run_meta = dict(meta or {})
        run_meta.setdefault(
            "date_window",
            {
                "start": str(pd.Timestamp(signed[cfg.date_col].iloc[0]).date()),
                "end": str(pd.Timestamp(signed[cfg.date_col].iloc[-1]).date()),
                "rows": len(signed),
            },
        )

        metrics = compute_metrics(
            signed,
            initial_capital=cfg.initial_capital,
            trading_days=cfg.trading_days,
            date_col=cfg.date_col,
        )

        return BacktestResult(
            strategy_name=strategy.name,
            config=cfg,
            metrics=metrics,
            dataframe=signed,
            meta=run_meta,
        )

    def run_batch(
        self,
        df: pd.DataFrame,
        strategies: list[Strategy],
        *,
        meta: dict[str, Any] | None = None,
    ) -> list[BacktestResult]:
        return [self.run(df, s, meta=meta) for s in strategies]

    def _prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        cfg = self.config
        out = df.copy()
        if cfg.date_col in out.columns:
            out[cfg.date_col] = pd.to_datetime(out[cfg.date_col])
            out = out.sort_values(cfg.date_col).reset_index(drop=True)
        if cfg.price_col not in out.columns:
            raise ValueError(f"数据缺少价格列: {cfg.price_col}")
        out = apply_date_window(out, cfg)
        if cfg.open_col not in out.columns:
            out[cfg.open_col] = out[cfg.price_col]
        return out.reset_index(drop=True)
