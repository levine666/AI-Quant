"""海龟看板回测：加载数据、执行引擎、序列化 API 响应。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from .config import BacktestConfig
from .data import load_csv
from .engine import BacktestEngine
from .metrics import compute_metrics
from .strategies.turtle import TurtleStrategy

BASE_DIR = Path(__file__).resolve().parent.parent
BACKTEST_SPEC = BASE_DIR / "spec" / "backtest.spec.yaml"
MANIFEST_PATH = BASE_DIR / "data" / "turtle" / "manifest.json"

SYSTEM_PRESETS = {
    "system_1": {"entry_period": 20, "exit_period": 10, "atr_period": 20, "stop_n_multiplier": 2.0},
    "system_2": {"entry_period": 55, "exit_period": 20, "atr_period": 20, "stop_n_multiplier": 2.0},
}


def load_backtest_spec() -> dict:
    with BACKTEST_SPEC.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def stock_index(spec: dict | None = None) -> dict[str, dict]:
    spec = spec or load_backtest_spec()
    return {s["stock_id"]: s for s in spec["stocks"]}


def resolve_params(body: dict) -> dict[str, Any]:
    system = body.get("system", "custom")
    params = dict(body.get("params") or {})
    if system in SYSTEM_PRESETS:
        merged = {**SYSTEM_PRESETS[system], **params}
    else:
        merged = {
            "entry_period": int(params.get("entry_period", 20)),
            "exit_period": int(params.get("exit_period", 10)),
            "atr_period": int(params.get("atr_period", 20)),
            "stop_n_multiplier": float(params.get("stop_n_multiplier", 2.0)),
        }
    return merged


def build_trades(df: pd.DataFrame, *, position_lag: int = 1) -> list[dict]:
    trades: list[dict] = []
    open_trade: dict | None = None
    dates = df["date"].astype(str).str[:10]
    opens = df["open"].fillna(df["close"]).astype(float)
    closes = df["close"].astype(float)

    for i in range(len(df)):
        exec_idx = i + position_lag
        if df["buy_signal"].iloc[i] and open_trade is None and exec_idx < len(df):
            open_trade = {
                "entry_date": dates.iloc[exec_idx],
                "entry_price": float(opens.iloc[exec_idx]),
            }

        if df["sell_signal"].iloc[i] and open_trade is not None:
            exit_px = float(closes.iloc[i])
            entry_px = open_trade["entry_price"]
            ret_pct = (exit_px - entry_px) / entry_px * 100
            entry_dt = pd.Timestamp(open_trade["entry_date"])
            exit_dt = pd.Timestamp(dates.iloc[i])
            trades.append(
                {
                    "trade_id": len(trades) + 1,
                    "entry_date": open_trade["entry_date"],
                    "entry_price": round(entry_px, 4),
                    "exit_date": dates.iloc[i],
                    "exit_price": round(exit_px, 4),
                    "exit_reason": "channel/stop",
                    "holding_days": int((exit_dt - entry_dt).days),
                    "return_pct": round(ret_pct, 2),
                }
            )
            open_trade = None

    if open_trade is not None:
        exit_px = float(closes.iloc[-1])
        entry_px = open_trade["entry_price"]
        ret_pct = (exit_px - entry_px) / entry_px * 100
        entry_dt = pd.Timestamp(open_trade["entry_date"])
        exit_dt = pd.Timestamp(dates.iloc[-1])
        trades.append(
            {
                "trade_id": len(trades) + 1,
                "entry_date": open_trade["entry_date"],
                "entry_price": round(entry_px, 4),
                "exit_date": None,
                "exit_price": None,
                "exit_reason": "end_of_backtest",
                "holding_days": int((exit_dt - entry_dt).days),
                "return_pct": round(ret_pct, 2),
            }
        )
    return trades


def trade_metrics(trades: list[dict]) -> dict[str, Any]:
    closed = [t for t in trades if t.get("exit_date")]
    wins = [t for t in closed if t["return_pct"] > 0]
    losses = [t for t in closed if t["return_pct"] <= 0]
    gross_profit = sum(t["return_pct"] for t in wins)
    gross_loss = sum(abs(t["return_pct"]) for t in losses)
    return {
        "win_rate_pct": round(len(wins) / len(closed) * 100, 1) if closed else 0.0,
        "profit_factor": round(gross_profit / gross_loss, 2) if gross_loss > 0 else None,
        "total_trades": len(closed),
    }


def _to_native(obj: Any) -> Any:
    if isinstance(obj, (np.floating, np.integer)):
        return obj.item()
    if isinstance(obj, dict):
        return {k: _to_native(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_native(x) for x in obj]
    return obj


def _nan_to_none(v: Any) -> Any:
    if isinstance(v, float) and (np.isnan(v) or np.isinf(v)):
        return None
    return v


def serialize_series(df: pd.DataFrame) -> dict:
    dates = df["date"].astype(str).str[:10].tolist()
    ohlc = df.apply(
        lambda r: [
            float(r["open"] if pd.notna(r.get("open")) else r["close"]),
            float(r["close"]),
            float(r["low"]),
            float(r["high"]),
        ],
        axis=1,
    ).tolist()

    def col(name: str) -> list:
        if name not in df.columns:
            return [None] * len(df)
        return [_nan_to_none(float(x)) if pd.notna(x) else None for x in df[name]]

    return {
        "dates": dates,
        "ohlc": ohlc,
        "donchian_entry_high": col("donchian_entry_high"),
        "donchian_exit_low": col("donchian_exit_low"),
        "atr_n": col("atr_n"),
        "stop_price": col("stop_price"),
        "equity": [round(float(x), 2) for x in df["equity"]],
        "bh_equity": [round(float(x), 2) for x in df["bh_equity"]],
        "buySignal": [bool(x) for x in df["buy_signal"]],
        "sellSignal": [bool(x) for x in df["sell_signal"]],
    }


def run_turtle_backtest(body: dict) -> dict:
    spec = load_backtest_spec()
    stocks = stock_index(spec)
    stock_id = body.get("stock_id", "smic_hk")
    if stock_id not in stocks:
        return {"error": f"未知标的: {stock_id}"}

    stock = stocks[stock_id]
    params = resolve_params(body)
    engine_cfg = body.get("engine") or {}

    try:
        strategy = TurtleStrategy(**params)
    except ValueError as e:
        return {"error": str(e)}

    path = BASE_DIR / stock["data_path"]
    if not path.exists():
        return {"error": f"数据文件不存在: {path}"}

    df = load_csv(path)
    cfg = BacktestConfig(
        initial_capital=float(engine_cfg.get("initial_capital", 100_000)),
        commission_rate=float(engine_cfg.get("commission_rate", 0.0003)),
        slippage_rate=float(engine_cfg.get("slippage_rate", 0.0005)),
        position_lag=int(engine_cfg.get("position_lag", 1)),
        start_date=body.get("start_date") or None,
        end_date=body.get("end_date") or None,
    )

    warmup = max(params["entry_period"], params["exit_period"], params["atr_period"]) + 5
    window_df = df.copy()
    if cfg.start_date:
        window_df = window_df[window_df["date"] >= pd.Timestamp(cfg.start_date)]
    if cfg.end_date:
        window_df = window_df[window_df["date"] <= pd.Timestamp(cfg.end_date)]
    if len(window_df) < warmup:
        return {"error": f"回测区间至少需要 {warmup} 个交易日，当前 {len(window_df)}"}

    engine = BacktestEngine(cfg)
    result = engine.run(window_df, strategy, meta={"stock_id": stock_id})
    out_df = result.dataframe
    trades = build_trades(out_df, position_lag=cfg.position_lag)
    extra = trade_metrics(trades)
    metrics = _to_native({**result.metrics, **extra})

    return _to_native({
        "stock": {
            "stock_id": stock_id,
            "name": stock["name"],
            "code": stock["code"],
            "market": stock["market"],
            "currency": stock.get("currency", ""),
            "unit": stock.get("unit", ""),
        },
        "date_window": {
            "start": metrics["start_date"],
            "end": metrics["end_date"],
            "rows": metrics["rows"],
        },
        "params": params,
        "metrics": metrics,
        "series": serialize_series(out_df),
        "trades": trades,
    })


def load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        import json

        with MANIFEST_PATH.open(encoding="utf-8") as f:
            return json.load(f)
    return build_manifest_from_spec()


def build_manifest_from_spec() -> dict:
    import json
    from datetime import datetime

    spec = load_backtest_spec()
    stocks_out = []
    for s in spec["stocks"]:
        if s.get("alias_of"):
            continue
        path = BASE_DIR / s["data_path"]
        if not path.exists():
            continue
        df = load_csv(path)
        stocks_out.append(
            {
                "stock_id": s["stock_id"],
                "name": s["name"],
                "code": s["code"],
                "market": s["market"],
                "currency": s.get("currency", ""),
                "unit": s.get("unit", ""),
                "data_path": s["data_path"],
                "adjust": "qfq",
                "last_complete_date": str(df["date"].iloc[-1].date()),
                "date_range": {
                    "start": str(df["date"].iloc[0].date()),
                    "end": str(df["date"].iloc[-1].date()),
                },
                "row_count": len(df),
                "validated_at": datetime.now().isoformat(timespec="seconds"),
                "status": "ok",
                "error_message": None,
            }
        )

    payload = {
        "global": {
            "version": "1.0.0",
            "refreshed_at": datetime.now().isoformat(timespec="seconds"),
            "spec_version": "1.0.0",
        },
        "stocks": stocks_out,
    }
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with MANIFEST_PATH.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return payload
