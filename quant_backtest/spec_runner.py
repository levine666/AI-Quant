"""从 spec 构建策略、加载数据、执行单次回测（供 runner / scanner 共用）。"""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

import pandas as pd

from . import BacktestConfig, BacktestEngine
from .data import load_csv

STRATEGY_ALIASES = {
    "dual_ma": "quant_backtest.strategies.DualMACrossStrategy",
}


def stock_index(spec: dict) -> dict[str, dict]:
    return {s["stock_id"]: s for s in spec["stocks"]}


def resolve_data_path(base_dir: Path, rel: str) -> Path:
    p = base_dir / rel
    if not p.exists():
        raise FileNotFoundError(f"数据文件不存在: {p}")
    return p


def validate_df(df: pd.DataFrame, rules: dict) -> list[str]:
    errors: list[str] = []
    if len(df) < rules.get("min_rows", 1):
        errors.append(f"行数不足: {len(df)} < {rules['min_rows']}")
    for col in rules.get("required_columns", []):
        if col not in df.columns:
            errors.append(f"缺少字段: {col}")
    if "close" in df.columns and (df["close"] <= 0).any():
        errors.append("存在 close <= 0")
    if "open" in df.columns and (df["open"] <= 0).any():
        errors.append("存在 open <= 0")
    return errors


def check_constraints(params: dict, constraints: list[dict]) -> bool:
    for c in constraints:
        rule = c.get("rule", "")
        if rule == "short < long":
            if params.get("short", 0) >= params.get("long", 0):
                return False
    return True


def build_strategy(strategy_type: str, params: dict, spec: dict) -> Any:
    registry = spec.get("strategies", {})
    if strategy_type not in registry:
        raise ValueError(f"未知策略类型: {strategy_type}")

    entry = registry[strategy_type]
    if entry.get("enabled") is False:
        raise ValueError(f"策略 {strategy_type} 未启用")

    if not check_constraints(params, entry.get("constraints", [])):
        raise ValueError(entry.get("constraints", [{}])[0].get("message", "参数约束不满足"))

    class_path = entry.get("class") or STRATEGY_ALIASES.get(strategy_type)
    if not class_path:
        raise ValueError(f"策略 {strategy_type} 未配置 class")

    module_path, class_name = class_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)(**params)


def build_engine(spec: dict, *, date_window: dict | None = None) -> BacktestEngine:
    cfg = spec["defaults"]["engine"]
    dw = date_window or spec["defaults"].get("date_window", {})
    return BacktestEngine(
        BacktestConfig(
            initial_capital=float(cfg["initial_capital"]),
            trading_days=int(cfg["trading_days"]),
            commission_rate=float(cfg.get("commission_rate", 0.0003)),
            slippage_rate=float(cfg.get("slippage_rate", 0.0005)),
            position_lag=int(cfg["position_lag"]),
            price_col=cfg.get("price_col", "close"),
            open_col=cfg.get("open_col", "open"),
            date_col=cfg.get("date_col", "date"),
            start_date=dw.get("start_date"),
            end_date=dw.get("end_date"),
        )
    )


def load_stock_df(base_dir: Path, stock: dict, spec: dict) -> pd.DataFrame:
    path = resolve_data_path(base_dir, stock["data_path"])
    df = load_csv(path)
    errors = validate_df(df, spec["defaults"]["validation"])
    if errors:
        raise ValueError(f"数据校验失败: {'; '.join(errors)}")
    return df


def run_one(
    engine: BacktestEngine,
    df: pd.DataFrame,
    stock: dict,
    strategy_type: str,
    params: dict,
    spec: dict,
    *,
    scenario_id: str,
    batch_id: str | None = None,
) -> dict[str, Any]:
    strategy = build_strategy(strategy_type, params, spec)
    result = engine.run(
        df,
        strategy,
        meta={
            "scenario_id": scenario_id,
            "batch_id": batch_id,
            "stock_id": stock["stock_id"],
            "stock_name": stock["name"],
            "stock_code": stock["code"],
            "market": stock["market"],
            "unit": stock.get("unit", ""),
            "strategy_type": strategy_type,
            "params": params,
        },
    )
    out = result.to_dict()
    out["dataframe"] = result.dataframe
    return out
