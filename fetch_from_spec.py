#!/usr/bin/env python3
"""按 spec/data_fetch.spec.yaml 规范批量取数、校验并落盘。"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import akshare as ak
import pandas as pd
import yaml

BASE_DIR = Path(__file__).resolve().parent
SPEC_PATH = BASE_DIR / "spec" / "data_fetch.spec.yaml"


def load_spec(path: Path = SPEC_PATH) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def date_range(lookback_days: int) -> tuple[str, str]:
    end_dt = datetime.now()
    start_dt = end_dt - timedelta(days=lookback_days)
    return start_dt.strftime("%Y%m%d"), end_dt.strftime("%Y%m%d")


def fetch_stock(stock: dict, defaults: dict) -> pd.DataFrame:
    start, end = date_range(defaults["lookback_days"])
    adjust = defaults["adjust"]
    symbol = stock["akshare_symbol"]

    last_err: Exception | None = None
    for attempt in range(defaults["retry"]["max_attempts"]):
        try:
            df = ak.stock_zh_a_daily(
                symbol=symbol,
                start_date=start,
                end_date=end,
                adjust="" if adjust == "none" else adjust,
            )
            break
        except Exception as e:
            last_err = e
            time.sleep(defaults["retry"]["delay_seconds"])
    else:
        raise RuntimeError(f"{stock['name']} 取数失败: {last_err}")

    df = df.sort_values("date").reset_index(drop=True)
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    df.insert(0, "stock_id", stock["stock_id"])
    df.insert(1, "name", stock["name"])
    df.insert(2, "code", stock["code"])
    df["adjust"] = adjust
    df["source"] = defaults["primary_source"]["interface"]
    return df


def validate_df(df: pd.DataFrame, rules: dict) -> list[str]:
    errors: list[str] = []
    if len(df) < rules["min_rows"]:
        errors.append(f"行数不足: {len(df)} < {rules['min_rows']}")

    for col in rules["required_columns"]:
        if col not in df.columns:
            errors.append(f"缺少字段: {col}")
        elif df[col].isna().mean() > rules["max_null_ratio"]:
            errors.append(f"字段 {col} 空值率过高")

    if "high" in df.columns and "low" in df.columns:
        if (df["high"] < df["low"]).any():
            errors.append("存在 high < low 的异常行")
    if "close" in df.columns and (df["close"] <= 0).any():
        errors.append("存在 close <= 0 的异常行")

    return errors


def save_outputs(
    df: pd.DataFrame,
    stock: dict,
    defaults: dict,
    naming: dict,
) -> dict[str, Path]:
    base = BASE_DIR / defaults["output"]["base_dir"] / stock["stock_id"]
    base.mkdir(parents=True, exist_ok=True)

    adjust = defaults["adjust"]
    csv_name = naming["daily_csv"].format(code=stock["code"], adjust=adjust)
    meta_name = naming["meta_json"].format(code=stock["code"])

    csv_path = base / csv_name
    df.to_csv(csv_path, index=False, encoding=defaults["output"]["encoding"])

    meta = {
        "stock_id": stock["stock_id"],
        "name": stock["name"],
        "code": stock["code"],
        "ts_code": stock["ts_code"],
        "industry": stock["industry"],
        "rows": len(df),
        "start_date": df["date"].iloc[0],
        "end_date": df["date"].iloc[-1],
        "adjust": adjust,
        "source": defaults["primary_source"],
        "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "spec_version": load_spec()["spec"]["version"],
    }
    meta_path = base / meta_name
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    return {"csv": csv_path, "meta": meta_path}


def run_fetch(spec: dict, validate_only: bool = False) -> None:
    defaults = spec["defaults"]
    naming = spec["naming"]
    validation = spec["validation"]
    report_dir = BASE_DIR / "data" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for stock in spec["stocks"]:
        print(f"\n{'='*50}")
        print(f"  {stock['name']} ({stock['code']})  [{stock['industry']}]")
        print(f"{'='*50}")

        if validate_only:
            csv_glob = list((BASE_DIR / defaults["output"]["base_dir"] / stock["stock_id"]).glob("daily_*.csv"))
            if not csv_glob:
                print("  跳过: 未找到已保存 CSV，请先执行取数")
                continue
            df = pd.read_csv(csv_glob[0])
        else:
            df = fetch_stock(stock, defaults)
            paths = save_outputs(df, stock, defaults, naming)
            print(f"  CSV  : {paths['csv']}")
            print(f"  Meta : {paths['meta']}")

        errors = validate_df(df, validation)
        status = "PASS" if not errors else "FAIL"
        print(f"  校验 : {status}  ({len(df)} 行)")
        for err in errors:
            print(f"    - {err}")

        results.append({"stock_id": stock["stock_id"], "name": stock["name"], "status": status, "errors": errors})

    report_path = report_dir / f"validation_{datetime.now():%Y%m%d_%H%M%S}.json"
    report_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n校验报告: {report_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="按 spec 规范取数")
    parser.add_argument("--spec", type=Path, default=SPEC_PATH, help="spec 文件路径")
    parser.add_argument("--validate-only", action="store_true", help="仅校验已落盘数据")
    parser.add_argument("--stock", type=str, help="仅处理指定 stock_id，如 smic/byd/cyp")
    args = parser.parse_args()

    spec = load_spec(args.spec)
    if args.stock:
        spec["stocks"] = [s for s in spec["stocks"] if s["stock_id"] == args.stock]
        if not spec["stocks"]:
            raise SystemExit(f"未找到 stock_id: {args.stock}")

    run_fetch(spec, validate_only=args.validate_only)


if __name__ == "__main__":
    main()
