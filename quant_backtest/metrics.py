"""回测绩效指标。"""

from __future__ import annotations

import numpy as np
import pandas as pd


def compute_metrics(
    df: pd.DataFrame,
    *,
    initial_capital: float,
    trading_days: int = 252,
    equity_col: str = "equity",
    strategy_ret_col: str = "strategy_ret",
    bh_equity_col: str = "bh_equity",
    date_col: str = "date",
) -> dict:
    equity = df[equity_col]
    strat_ret = df[strategy_ret_col].dropna()
    roll_max = equity.cummax()
    drawdown = (equity - roll_max) / roll_max

    cum_ret = equity.iloc[-1] / initial_capital - 1
    bh_cum_ret = df[bh_equity_col].iloc[-1] / initial_capital - 1
    mdd = float(drawdown.min())
    vol = float(strat_ret.std())
    sharpe = float(strat_ret.mean() / vol * np.sqrt(trading_days)) if vol > 0 else 0.0

    metrics = {
        "cumulative_return_pct": round(cum_ret * 100, 2),
        "buy_hold_return_pct": round(bh_cum_ret * 100, 2),
        "max_drawdown_pct": round(mdd * 100, 2),
        "sharpe_ratio": round(sharpe, 3),
        "final_equity": round(float(equity.iloc[-1]), 2),
        "final_bh_equity": round(float(df[bh_equity_col].iloc[-1]), 2),
        "start_date": str(pd.Timestamp(df[date_col].iloc[0]).date()),
        "end_date": str(pd.Timestamp(df[date_col].iloc[-1]).date()),
        "rows": len(df),
    }

    if "buy_signal" in df.columns:
        metrics["buy_count"] = int(df["buy_signal"].sum())
        metrics["sell_count"] = int(df["sell_signal"].sum())
        metrics["trade_count"] = metrics["buy_count"] + metrics["sell_count"]

    return metrics
