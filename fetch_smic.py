#!/usr/bin/env python3
"""Fetch 中芯国际 A股(688981) & 港股(00981) data and save locally."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import akshare as ak
import pandas as pd

STOCK_NAME = "中芯国际"
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

A_SHARE = {
    "market": "A股",
    "name": STOCK_NAME,
    "code": "688981",
    "symbol": "sh688981",
    "currency": "CNY",
    "unit": "元",
}

HK_SHARE = {
    "market": "港股",
    "name": STOCK_NAME,
    "code": "00981",
    "symbol": "00981",
    "currency": "HKD",
    "unit": "港元",
}


def _date_range() -> tuple[str, str, datetime]:
    end_dt = datetime.now()
    start_dt = end_dt - timedelta(days=365)
    return start_dt.strftime("%Y%m%d"), end_dt.strftime("%Y%m%d"), start_dt


def fetch_a_share(start_date: str, end_date: str) -> pd.DataFrame:
    df = ak.stock_zh_a_daily(
        symbol=A_SHARE["symbol"],
        start_date=start_date,
        end_date=end_date,
        adjust="qfq",
    )
    return df.sort_values("date").reset_index(drop=True)


def fetch_hk_share(start_dt: datetime) -> pd.DataFrame:
    df = ak.stock_hk_daily(symbol=HK_SHARE["symbol"], adjust="qfq")
    df["date"] = pd.to_datetime(df["date"])
    df = df[df["date"] >= start_dt].copy()
    return df.sort_values("date").reset_index(drop=True)


def fetch_hkd_cny_rate(start_date: str, end_date: str) -> pd.DataFrame:
    df = ak.currency_boc_sina(symbol="港币", start_date=start_date, end_date=end_date)
    df = df.rename(columns={"日期": "date", "中行折算价": "rate"})
    df["date"] = pd.to_datetime(df["date"])
    df["rate"] = pd.to_numeric(df["rate"], errors="coerce")
    # 中行折算价: 100 HKD = rate CNY
    df["hkd_cny"] = df["rate"] / 100.0
    return df[["date", "hkd_cny"]].dropna().sort_values("date")


def build_market_payload(df: pd.DataFrame, info: dict, source: str) -> dict:
    df = df.copy()
    df["date"] = df["date"].astype(str).str[:10]
    records = df.to_dict(orient="records")
    meta = {
        **info,
        "start_date": df["date"].iloc[0],
        "end_date": df["date"].iloc[-1],
        "rows": len(df),
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": source,
    }
    return {"meta": meta, "data": records}


def build_comparison(a_df: pd.DataFrame, hk_df: pd.DataFrame, fx_df: pd.DataFrame) -> dict:
    a = a_df.copy()
    hk = hk_df.copy()
    fx = fx_df.copy()

    a["date"] = pd.to_datetime(a["date"])
    hk["date"] = pd.to_datetime(hk["date"])

    merged = a.merge(hk, on="date", suffixes=("_a", "_hk"))
    merged = merged.sort_values("date")
    merged = pd.merge_asof(
        merged,
        fx.sort_values("date"),
        on="date",
        direction="backward",
    )
    merged = merged.dropna(subset=["hkd_cny"]).reset_index(drop=True)

    if merged.empty:
        return {"dates": [], "metrics": {}}

    a0 = merged["close_a"].iloc[0]
    hk0 = merged["close_hk"].iloc[0]
    merged["a_index"] = (merged["close_a"] / a0 * 100).round(2)
    merged["hk_index"] = (merged["close_hk"] / hk0 * 100).round(2)
    merged["hk_cny"] = (merged["close_hk"] * merged["hkd_cny"]).round(2)
    merged["ah_premium"] = (
        (merged["close_a"] / merged["hk_cny"] - 1) * 100
    ).round(2)

    latest = merged.iloc[-1]
    first = merged.iloc[0]
    a_ret = (latest["close_a"] / first["close_a"] - 1) * 100
    hk_ret = (latest["close_hk"] / first["close_hk"] - 1) * 100

    return {
        "dates": merged["date"].dt.strftime("%Y-%m-%d").tolist(),
        "a_index": merged["a_index"].tolist(),
        "hk_index": merged["hk_index"].tolist(),
        "ah_premium": merged["ah_premium"].tolist(),
        "a_close": merged["close_a"].round(2).tolist(),
        "hk_close": merged["close_hk"].round(2).tolist(),
        "hk_cny": merged["hk_cny"].tolist(),
        "hkd_cny": merged["hkd_cny"].round(4).tolist(),
        "a_volume": merged["volume_a"].tolist(),
        "hk_volume": merged["volume_hk"].tolist(),
        "summary": {
            "overlap_days": len(merged),
            "start_date": merged["date"].iloc[0].strftime("%Y-%m-%d"),
            "end_date": merged["date"].iloc[-1].strftime("%Y-%m-%d"),
            "a_return_pct": round(a_ret, 2),
            "hk_return_pct": round(hk_ret, 2),
            "return_spread_pct": round(a_ret - hk_ret, 2),
            "latest_ah_premium_pct": round(float(latest["ah_premium"]), 2),
            "avg_ah_premium_pct": round(float(merged["ah_premium"].mean()), 2),
            "max_ah_premium_pct": round(float(merged["ah_premium"].max()), 2),
            "min_ah_premium_pct": round(float(merged["ah_premium"].min()), 2),
            "latest_hkd_cny": round(float(latest["hkd_cny"]), 4),
        },
    }


def save(payload: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    json_path = DATA_DIR / "smic_compare.json"
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    pd.DataFrame(payload["a_share"]["data"]).to_csv(
        DATA_DIR / "smic_688981_a.csv", index=False, encoding="utf-8-sig"
    )
    pd.DataFrame(payload["hk_share"]["data"]).to_csv(
        DATA_DIR / "smic_00981_hk.csv", index=False, encoding="utf-8-sig"
    )

    js_path = DATA_DIR / "stock_data.js"
    js_path.write_text(
        "window.STOCK_DATA = " + json.dumps(payload, ensure_ascii=False) + ";\n",
        encoding="utf-8",
    )

    a_meta = payload["a_share"]["meta"]
    hk_meta = payload["hk_share"]["meta"]
    cmp_summary = payload["comparison"]["summary"]

    print(f"A股  {a_meta['rows']} rows  {a_meta['start_date']} ~ {a_meta['end_date']}")
    print(f"港股 {hk_meta['rows']} rows  {hk_meta['start_date']} ~ {hk_meta['end_date']}")
    print(
        f"对比 {cmp_summary['overlap_days']} 重叠交易日  "
        f"A股涨跌 {cmp_summary['a_return_pct']:+.2f}%  "
        f"港股 {cmp_summary['hk_return_pct']:+.2f}%  "
        f"AH溢价 {cmp_summary['latest_ah_premium_pct']:+.2f}%"
    )
    print(f"  JSON: {json_path}")
    print(f"  JS  : {js_path}")


def main() -> None:
    start_date, end_date, start_dt = _date_range()

    a_df = fetch_a_share(start_date, end_date)
    hk_df = fetch_hk_share(start_dt)
    fx_df = fetch_hkd_cny_rate(start_date, end_date)

    payload = {
        "meta": {
            "name": STOCK_NAME,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        "a_share": build_market_payload(
            a_df, A_SHARE, "akshare (stock_zh_a_daily, qfq)"
        ),
        "hk_share": build_market_payload(
            hk_df, HK_SHARE, "akshare (stock_hk_daily, qfq)"
        ),
        "comparison": build_comparison(a_df, hk_df, fx_df),
    }

    save(payload)
    print("\nOpen dashboard.html in a browser to view comparison charts.")


if __name__ == "__main__":
    main()
