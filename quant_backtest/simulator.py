"""组合模拟：含手续费、滑点，以及买入持有基准。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import BacktestConfig


def _buy_cost(notional: float, cfg: BacktestConfig) -> tuple[float, float]:
    """返回 (可买金额, 手续费)。"""
    fee = notional * cfg.commission_rate
    return notional - fee, fee


def _sell_proceeds(gross: float, cfg: BacktestConfig) -> tuple[float, float]:
    """返回 (到手金额, 手续费)。"""
    fee = gross * cfg.commission_rate
    return gross - fee, fee


def simulate_strategy_equity(df: pd.DataFrame, position: pd.Series, cfg: BacktestConfig) -> pd.Series:
    """策略净值：开仓按开盘价（含滑点），平仓按收盘价（含滑点），均扣手续费。"""
    open_p = df[cfg.open_col].fillna(df[cfg.price_col]).astype(float).values
    close_p = df[cfg.price_col].astype(float).values
    pos = position.fillna(0).astype(float).values
    n = len(df)

    cash = float(cfg.initial_capital)
    shares = 0.0
    equity = np.zeros(n)

    for i in range(n):
        prev = pos[i - 1] if i > 0 else 0.0
        tgt = pos[i]

        # 开仓：前一日信号确认后，当日开盘买入
        if prev == 0 and tgt > 0 and shares == 0 and cash > 0:
            buy_px = open_p[i] * (1.0 + cfg.slippage_rate)
            spend, fee = _buy_cost(cash, cfg)
            shares = spend / buy_px
            cash = 0.0

        # 平仓：当日收盘卖出
        if prev > 0 and tgt == 0 and shares > 0:
            sell_px = close_p[i] * (1.0 - cfg.slippage_rate)
            gross = shares * sell_px
            cash, fee = _sell_proceeds(gross, cfg)
            shares = 0.0

        equity[i] = cash + shares * close_p[i]

    return pd.Series(equity, index=df.index, name="equity")


def simulate_buy_hold_equity(df: pd.DataFrame, cfg: BacktestConfig) -> pd.Series:
    """买入持有基准：首日开盘全仓买入，末日收盘卖出，均扣手续费与滑点。"""
    open_p = df[cfg.open_col].fillna(df[cfg.price_col]).astype(float).values
    close_p = df[cfg.price_col].astype(float).values
    n = len(df)
    if n == 0:
        return pd.Series(dtype=float)

    buy_px = open_p[0] * (1.0 + cfg.slippage_rate)
    spend, _ = _buy_cost(float(cfg.initial_capital), cfg)
    shares = spend / buy_px

    equity = np.zeros(n)
    for i in range(n):
        if i == n - 1:
            sell_px = close_p[i] * (1.0 - cfg.slippage_rate)
            gross = shares * sell_px
            equity[i], _ = _sell_proceeds(gross, cfg)
        else:
            equity[i] = shares * close_p[i]

    return pd.Series(equity, index=df.index, name="bh_equity")


def apply_date_window(df: pd.DataFrame, cfg: BacktestConfig) -> pd.DataFrame:
    """按 start_date / end_date 截取回测区间。"""
    out = df.copy()
    col = cfg.date_col
    if col not in out.columns:
        return out
    out[col] = pd.to_datetime(out[col])
    if cfg.start_date:
        out = out[out[col] >= pd.Timestamp(cfg.start_date)]
    if cfg.end_date:
        out = out[out[col] <= pd.Timestamp(cfg.end_date)]
    return out.sort_values(col).reset_index(drop=True)


def attach_returns(df: pd.DataFrame, cfg: BacktestConfig) -> pd.DataFrame:
    """写入 strategy_ret / ret（用于夏普）及 close 日收益。"""
    out = df.copy()
    out["strategy_ret"] = out["equity"].pct_change().fillna(0)
    out["ret"] = out[cfg.price_col].pct_change().fillna(0)
    out["bh_ret"] = out["bh_equity"].pct_change().fillna(0)
    return out
