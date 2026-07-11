#!/usr/bin/env python3
"""按 spec/backtest.spec.yaml 规范批量执行策略回测。"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

BASE_DIR = Path(__file__).resolve().parent
SPEC_PATH = BASE_DIR / "spec" / "backtest.spec.yaml"
sys.path.insert(0, str(BASE_DIR))

from quant_backtest.scanner import ParameterScanner
from quant_backtest.spec_runner import (
    build_engine,
    load_stock_df,
    run_one,
    stock_index,
)


def load_spec(path: Path = SPEC_PATH) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_equity_csv(df: pd.DataFrame, out_path: Path, cols: list[str]) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    keep = [c for c in cols if c in df.columns]
    df[keep].to_csv(out_path, index=False, encoding="utf-8")


def expand_batches(spec: dict) -> list[dict]:
    runs: list[dict] = []
    for batch in spec.get("scenarios", {}).get("batches", []):
        batch_id = batch["batch_id"]
        strategy_type = batch.get("strategy", "dual_ma")
        if isinstance(strategy_type, dict):
            strategy_type = strategy_type.get("type", "dual_ma")

        if "runs" in batch:
            for item in batch["runs"]:
                runs.append(
                    {
                        "scenario_id": item["scenario_id"],
                        "batch_id": batch_id,
                        "stock_id": batch.get("stock_id"),
                        "strategy_type": strategy_type,
                        "params": item["params"],
                    }
                )
        elif "stock_ids" in batch:
            params = batch.get("params", {})
            for sid in batch["stock_ids"]:
                runs.append(
                    {
                        "scenario_id": f"{batch_id}_{sid}_ma{params.get('short')}_{params.get('long')}",
                        "batch_id": batch_id,
                        "stock_id": sid,
                        "strategy_type": strategy_type,
                        "params": params,
                    }
                )
    return runs


def run_param_scan(spec: dict) -> dict[str, Any]:
    scan_cfg = spec.get("param_scan")
    if not scan_cfg or not scan_cfg.get("enabled", False):
        raise SystemExit("param_scan 未启用，请在 spec/backtest.spec.yaml 中设置 param_scan.enabled: true")

    scanner = ParameterScanner(spec, BASE_DIR)
    return scanner.run(scan_cfg)


def run_backtest(spec: dict, *, plot: bool = False, scenario_filter: str | None = None) -> Path:
    engine_cfg = spec["defaults"]["engine"]
    out_cfg = spec["defaults"]["output"]
    naming = spec["naming"]
    stocks = stock_index(spec)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    engine = build_engine(spec)
    base_out = BASE_DIR / out_cfg["base_dir"]
    base_out.mkdir(parents=True, exist_ok=True)

    all_results: list[dict] = []
    equity_cols = [
        "date", "close", "ma_short", "ma_long", "position",
        "equity", "bh_equity", "buy_signal", "sell_signal",
    ]

    primary = spec["scenarios"]["primary"]
    if not scenario_filter or scenario_filter in ("primary", primary["scenario_id"]):
        p = primary["strategy"]
        stock = stocks[primary["stock_id"]]
        df = load_stock_df(BASE_DIR, stock, spec)
        r = run_one(
            engine, df, stock, p["type"], p["params"], spec,
            scenario_id=primary["scenario_id"], batch_id="primary",
        )
        all_results.append(r)
        if out_cfg.get("save_equity_csv", True):
            save_equity_csv(
                r["dataframe"],
                base_out / naming["equity_csv"].format(scenario_id=primary["scenario_id"]),
                equity_cols,
            )

    for item in expand_batches(spec):
        if scenario_filter and scenario_filter not in (item["scenario_id"], item["batch_id"]):
            continue
        stock = stocks[item["stock_id"]]
        df = load_stock_df(BASE_DIR, stock, spec)
        r = run_one(
            engine, df, stock, item["strategy_type"], item["params"], spec,
            scenario_id=item["scenario_id"], batch_id=item["batch_id"],
        )
        all_results.append(r)
        if out_cfg.get("save_equity_csv", True):
            save_equity_csv(
                r["dataframe"],
                base_out / naming["equity_csv"].format(scenario_id=item["scenario_id"]),
                equity_cols,
            )

    slim_results = []
    summary_rows = []
    for r in all_results:
        meta = r.get("meta", {})
        metrics = r.get("metrics", {})
        slim_results.append({
            "scenario_id": meta.get("scenario_id"),
            "batch_id": meta.get("batch_id"),
            "strategy": r.get("strategy"),
            "meta": meta,
            "metrics": metrics,
            "config": r.get("config"),
        })
        summary_rows.append({
            "scenario_id": meta.get("scenario_id"),
            "batch_id": meta.get("batch_id"),
            "stock_id": meta.get("stock_id"),
            "stock_name": meta.get("stock_name"),
            "code": meta.get("stock_code"),
            "strategy": r.get("strategy"),
            "short": meta.get("params", {}).get("short"),
            "long": meta.get("params", {}).get("long"),
            **metrics,
        })

    report = {
        "spec": spec["spec"],
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "engine": engine_cfg,
        "results": slim_results,
    }

    report_path = base_out / naming["report_json"].format(timestamp=ts)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    summary_path = base_out / naming["summary_csv"].format(timestamp=ts)
    pd.DataFrame(summary_rows).to_csv(summary_path, index=False, encoding="utf-8")

    print(f"\n回测完成: {len(all_results)} 个场景")
    print(f"  报告 JSON: {report_path}")
    print(f"  汇总 CSV: {summary_path}")

    for row in summary_rows:
        print(
            f"  [{row['scenario_id']}] {row['stock_name']}({row['code']}) "
            f"回报={row.get('cumulative_return_pct')}% "
            f"MDD={row.get('max_drawdown_pct')}% "
            f"Sharpe={row.get('sharpe_ratio')}"
        )

    if plot or out_cfg.get("plot"):
        task3 = BASE_DIR / "TASK3" / "task3_analysis.py"
        if task3.exists():
            print("\n>>> 生成 TASK3 图表")
            subprocess.run([sys.executable, str(task3)], check=True)

    return report_path


def apply_date_overrides(spec: dict, start: str | None, end: str | None) -> dict:
    if not start and not end:
        return spec
    spec = dict(spec)
    spec["defaults"] = dict(spec["defaults"])
    dw = dict(spec["defaults"].get("date_window", {}))
    if start:
        dw["start_date"] = start
    if end:
        dw["end_date"] = end
    spec["defaults"]["date_window"] = dw
    return spec


def main() -> None:
    parser = argparse.ArgumentParser(description="按 spec 规范执行策略回测")
    parser.add_argument("--spec", type=Path, default=SPEC_PATH, help="spec 文件路径")
    parser.add_argument("--plot", action="store_true", help="回测后生成 TASK3 图表")
    parser.add_argument("--scenario", type=str, help="仅运行指定 scenario_id 或 batch_id")
    parser.add_argument("--scan", action="store_true", help="运行 param_scan 参数网格扫描")
    parser.add_argument("--scan-only", action="store_true", help="仅扫描，不跑常规回测")
    parser.add_argument("--start-date", type=str, help="回测起始日 YYYY-MM-DD（覆盖 spec）")
    parser.add_argument("--end-date", type=str, help="回测结束日 YYYY-MM-DD（覆盖 spec）")
    args = parser.parse_args()

    spec = apply_date_overrides(load_spec(args.spec), args.start_date, args.end_date)

    if args.scan or args.scan_only:
        run_param_scan(spec)

    if not args.scan_only:
        run_backtest(spec, plot=args.plot, scenario_filter=args.scenario)


if __name__ == "__main__":
    main()
