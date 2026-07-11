#!/usr/bin/env python3
"""按 spec/turtle_data_refresh.spec.yaml 增量刷新日线并更新 manifest。"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import akshare as ak
import pandas as pd
import yaml

BASE = Path(__file__).resolve().parent
SPEC_BACKTEST = BASE / "spec" / "backtest.spec.yaml"
MANIFEST_PATH = BASE / "data" / "turtle" / "manifest.json"
LOG_PATH = BASE / "data" / "turtle" / "refresh_log.jsonl"

HK_FETCH = {
    "smic_hk": {"interface": "stock_hk_daily", "symbol": "00981"},
}


def load_spec() -> dict:
    with SPEC_BACKTEST.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def akshare_symbol(stock: dict) -> str:
    code = stock["code"]
    market = stock.get("market", "")
    if market == "港股":
        return code
    if code.startswith("6"):
        return f"sh{code}"
    return f"sz{code}"


def fetch_a_share(symbol: str, start: str, end: str, adjust: str = "qfq") -> pd.DataFrame:
    return ak.stock_zh_a_daily(
        symbol=symbol,
        start_date=start,
        end_date=end,
        adjust="" if adjust == "none" else adjust,
    )


def fetch_hk(symbol: str, start: str, end: str, adjust: str = "qfq") -> pd.DataFrame:
    df = ak.stock_hk_daily(symbol=symbol, adjust=adjust)
    df = df.sort_values("date").reset_index(drop=True)
    df["date"] = pd.to_datetime(df["date"])
    mask = (df["date"] >= pd.Timestamp(start)) & (df["date"] <= pd.Timestamp(end))
    return df.loc[mask].reset_index(drop=True)


def normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["date"] = pd.to_datetime(out["date"]).dt.strftime("%Y-%m-%d")
    for col in ("open", "high", "low", "close", "volume"):
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    keep = [c for c in ("date", "open", "high", "low", "close", "volume") if c in out.columns]
    return out[keep].dropna(subset=["date", "close"]).sort_values("date").reset_index(drop=True)


def validate(df: pd.DataFrame) -> list[str]:
    errors: list[str] = []
    if len(df) < 60:
        errors.append(f"行数不足: {len(df)}")
    if df["date"].duplicated().any():
        errors.append("存在重复日期")
    if (df["high"] < df["low"]).any():
        errors.append("存在 high < low")
    if (df["close"] <= 0).any():
        errors.append("存在 close <= 0")
    return errors


def merge_csv(path: Path, new_df: pd.DataFrame) -> pd.DataFrame:
    if path.exists():
        old = pd.read_csv(path)
        old["date"] = pd.to_datetime(old["date"]).dt.strftime("%Y-%m-%d")
        merged = pd.concat([old, new_df], ignore_index=True)
        merged = merged.drop_duplicates(subset=["date"], keep="last")
    else:
        merged = new_df
    return merged.sort_values("date").reset_index(drop=True)


def refresh_stock(stock: dict, *, full: bool = False, lookback_days: int = 730) -> dict:
    path = BASE / stock["data_path"]
    path.parent.mkdir(parents=True, exist_ok=True)

    end_dt = datetime.now()
    if path.exists() and not full:
        local = pd.read_csv(path)
        local["date"] = pd.to_datetime(local["date"])
        last = local["date"].max()
        start_dt = last + timedelta(days=1)
    else:
        start_dt = end_dt - timedelta(days=lookback_days)

    start = start_dt.strftime("%Y%m%d")
    end = end_dt.strftime("%Y%m%d")

    last_err: Exception | None = None
    for attempt in range(3):
        try:
            if stock.get("market") == "港股":
                sym = HK_FETCH.get(stock["stock_id"], {}).get("symbol", stock["code"])
                chunk = fetch_hk(sym, start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d"))
            else:
                chunk = fetch_a_share(akshare_symbol(stock), start, end, "qfq")
            break
        except Exception as e:
            last_err = e
            time.sleep(2)
    else:
        raise RuntimeError(f"{stock['name']} 取数失败: {last_err}")

    chunk = normalize_df(chunk)
    if chunk.empty and path.exists():
        df = pd.read_csv(path)
    elif chunk.empty:
        raise RuntimeError(f"{stock['name']} 未返回任何数据")
    else:
        df = merge_csv(path, chunk)

    errors = validate(df)
    if errors:
        raise ValueError(f"{stock['name']} 校验失败: {'; '.join(errors)}")

    df.to_csv(path, index=False, encoding="utf-8")
    return {
        "stock_id": stock["stock_id"],
        "name": stock["name"],
        "code": stock["code"],
        "market": stock["market"],
        "currency": stock.get("currency", ""),
        "unit": stock.get("unit", ""),
        "data_path": stock["data_path"],
        "adjust": "qfq",
        "last_complete_date": df["date"].iloc[-1],
        "date_range": {"start": df["date"].iloc[0], "end": df["date"].iloc[-1]},
        "row_count": len(df),
        "validated_at": datetime.now().isoformat(timespec="seconds"),
        "status": "ok",
        "error_message": None,
        "new_bars": len(chunk),
    }


def write_manifest(stocks: list[dict]) -> dict:
    payload = {
        "global": {
            "version": "1.0.0",
            "refreshed_at": datetime.now().isoformat(timespec="seconds"),
            "spec_version": "1.0.0",
        },
        "stocks": stocks,
    }
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with MANIFEST_PATH.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return payload


def append_log(entry: dict) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def validate_only() -> dict:
    from quant_backtest.turtle_runner import build_manifest_from_spec

    return build_manifest_from_spec()


def main() -> None:
    parser = argparse.ArgumentParser(description="刷新海龟看板日线数据")
    parser.add_argument("--stock-id", default=None, help="仅刷新指定标的")
    parser.add_argument("--full", action="store_true", help="全量重建")
    parser.add_argument("--validate-only", action="store_true", help="仅校验并更新 manifest")
    parser.add_argument("--dry-run", action="store_true", help="不写盘")
    args = parser.parse_args()

    spec = load_spec()
    stocks = [s for s in spec["stocks"] if not s.get("alias_of")]
    if args.stock_id:
        stocks = [s for s in stocks if s["stock_id"] == args.stock_id]
        if not stocks:
            raise SystemExit(f"未找到 stock_id: {args.stock_id}")

    if args.validate_only:
        manifest = validate_only()
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
        return

    results: list[dict] = []
    for stock in stocks:
        try:
            if args.dry_run:
                print(f"[dry-run] would refresh {stock['stock_id']}")
                continue
            info = refresh_stock(stock, full=args.full)
            results.append(info)
            print(f"OK {stock['stock_id']}: +{info['new_bars']} bars → {info['last_complete_date']}")
            append_log({"ts": datetime.now().isoformat(), **info})
        except Exception as e:
            print(f"FAIL {stock['stock_id']}: {e}", file=sys.stderr)
            results.append(
                {
                    "stock_id": stock["stock_id"],
                    "name": stock["name"],
                    "status": "error",
                    "error_message": str(e),
                }
            )

    if not args.dry_run and results:
        ok = [r for r in results if r.get("status") == "ok"]
        if ok:
            write_manifest(ok)


if __name__ == "__main__":
    main()
