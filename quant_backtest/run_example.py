#!/usr/bin/env python3
"""回测引擎使用示例。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from quant_backtest import BacktestConfig, BacktestEngine
from quant_backtest.data import load_csv
from quant_backtest.strategies import DualMACrossStrategy

DATA = ROOT / "TASK2/task02_indicator_lab/data/raw/smic_hk_00981_daily.csv"


def main() -> None:
    df = load_csv(DATA)
    engine = BacktestEngine(BacktestConfig(initial_capital=100_000, position_lag=1))

    result = engine.run(
        df,
        DualMACrossStrategy(short=5, long=15),
        meta={"symbol": "00981.HK"},
    )

    m = result.metrics
    print(f"策略: {result.strategy_name}")
    print(f"累计回报: {m['cumulative_return_pct']}%")
    print(f"最大回撤: {m['max_drawdown_pct']}%")
    print(f"夏普比率: {m['sharpe_ratio']}")
    print(f"买卖次数: {m.get('buy_count', 0)} / {m.get('sell_count', 0)}")


if __name__ == "__main__":
    main()
