#!/usr/bin/env python3
"""从本地 CSV 生成 turtle_dashboard/static/demo_data.js（供 dry-run 看板使用）。"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = Path(__file__).resolve().parent / "static"

STOCKS = [
    ("smic_hk", "中芯国际", "00981", "港股", "HKD", "港元",
     BASE / "TASK2/task02_indicator_lab/data/raw/smic_hk_00981_daily.csv"),
    ("smic_a", "中芯国际", "688981", "A股", "CNY", "元",
     BASE / "data/raw/smic/daily_688981_qfq.csv"),
    ("byd", "比亚迪", "002594", "A股", "CNY", "元",
     BASE / "data/raw/byd/daily_002594_qfq.csv"),
    ("cyp", "长江电力", "600900", "A股", "CNY", "元",
     BASE / "data/raw/cyp/daily_600900_qfq.csv"),
]


def load_bars(path: Path) -> list[dict]:
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    cols = ["date", "open", "high", "low", "close", "volume"]
    for c in cols:
        if c not in df.columns:
            raise ValueError(f"{path} 缺少列 {c}")
    rows = df[cols].to_dict("records")
    for r in rows:
        for k in ("open", "high", "low", "close", "volume"):
            r[k] = float(r[k])
    return rows


def main() -> None:
    payload = {
        "global": {
            "refreshed_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "spec_version": "1.0.0",
        },
        "stocks": [],
    }
    for sid, name, code, market, currency, unit, path in STOCKS:
        if not path.exists():
            print(f"skip missing: {path}")
            continue
        bars = load_bars(path)
        payload["stocks"].append(
            {
                "stock_id": sid,
                "name": name,
                "code": code,
                "market": market,
                "currency": currency,
                "unit": unit,
                "last_complete_date": bars[-1]["date"],
                "date_range": {"start": bars[0]["date"], "end": bars[-1]["date"]},
                "row_count": len(bars),
                "status": "ok",
                "bars": bars,
            }
        )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    js_path = OUT_DIR / "demo_data.js"
    js_path.write_text(
        "window.DEMO_DATA = " + json.dumps(payload, ensure_ascii=False, indent=2) + ";\n",
        encoding="utf-8",
    )
    print(f"Wrote {js_path} ({js_path.stat().st_size:,} bytes, {len(payload['stocks'])} stocks)")


if __name__ == "__main__":
    main()
