#!/usr/bin/env python3
"""按 indicator_lab.spec.yaml 执行取数、算指标、出图。"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import akshare as ak
import matplotlib.pyplot as plt
import pandas as pd
import yaml

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "scripts"))

from font_utils import apply_global_font, get_chinese_font
from indicators import add_all_indicators

SPEC_PATH = BASE / "spec" / "indicator_lab.spec.yaml"


def load_spec() -> dict:
    with SPEC_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def fetch_hk_daily(spec: dict) -> pd.DataFrame:
    cfg = spec["data_fetch"]
    lookback = cfg["lookback_days"]
    start_dt = datetime.now() - timedelta(days=lookback)

    df = ak.stock_hk_daily(
        symbol=cfg["params"]["symbol"],
        adjust=cfg["params"]["adjust"],
    )
    df["date"] = pd.to_datetime(df["date"])
    df = df[df["date"] >= start_dt].sort_values("date").drop_duplicates("date")
    df = df.reset_index(drop=True)
    return df


def validate_raw(df: pd.DataFrame, spec: dict) -> list[str]:
    rules = spec["validation"]["raw"]
    errors = []
    if len(df) < rules["min_rows"]:
        errors.append(f"行数 {len(df)} < {rules['min_rows']}")
    for col in rules["required"]:
        if col not in df.columns:
            errors.append(f"缺少列 {col}")
    if (df["high"] < df["low"]).any():
        errors.append("存在 high < low")
    if (df["close"] <= 0).any():
        errors.append("存在 close <= 0")
    return errors


def plot_figures(df: pd.DataFrame, spec: dict) -> None:
    fig_dir = BASE / "data" / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    fp = apply_global_font()
    fp_title = get_chinese_font(12)
    dates = df["date"]

    # 图1 BOLL
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(dates, df["close"], label="收盘价", color="#1565C0", linewidth=1.4)
    ax.plot(dates, df["boll_mid"], label="中轨", color="#888", linewidth=1)
    ax.plot(dates, df["boll_upper"], label="上轨", color="#ef5350", linewidth=0.9, linestyle="--")
    ax.plot(dates, df["boll_lower"], label="下轨", color="#26a69a", linewidth=0.9, linestyle="--")
    ax.fill_between(dates, df["boll_lower"], df["boll_upper"], alpha=0.06, color="#888")
    ax.set_title(spec["indicators"]["BOLL"]["plot"]["title"], fontproperties=fp_title)
    ax.set_xlabel("交易日期", fontproperties=fp)
    ax.set_ylabel("价格（港元）", fontproperties=fp)
    ax.legend(prop=get_chinese_font(9))
    ax.grid(True, linestyle="--", alpha=0.35)
    plt.xticks(rotation=30)
    plt.tight_layout()
    fig.savefig(fig_dir / "fig_boll.png", dpi=180, bbox_inches="tight")
    plt.close(fig)

    # 图2 RSI
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(dates, df["rsi_14"], color="#7b1fa2", linewidth=1.4)
    for y, c in [(70, "#ef5350"), (50, "#888"), (30, "#26a69a")]:
        ax.axhline(y, color=c, linestyle="--", linewidth=0.8, alpha=0.7)
    ax.set_ylim(0, 100)
    ax.set_title(spec["indicators"]["RSI"]["plot"]["title"], fontproperties=fp_title)
    ax.set_xlabel("交易日期", fontproperties=fp)
    ax.set_ylabel("RSI", fontproperties=fp)
    ax.grid(True, linestyle="--", alpha=0.35)
    plt.xticks(rotation=30)
    plt.tight_layout()
    fig.savefig(fig_dir / "fig_rsi.png", dpi=180, bbox_inches="tight")
    plt.close(fig)

    # 图3 MACD
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True, gridspec_kw={"height_ratios": [2, 1]})
    ax1.plot(dates, df["macd_dif"], label="DIF", color="#1565C0", linewidth=1.2)
    ax1.plot(dates, df["macd_dea"], label="DEA", color="#f5a623", linewidth=1.2)
    ax1.set_title(spec["indicators"]["MACD"]["plot"]["title"], fontproperties=fp_title)
    ax1.set_ylabel("MACD", fontproperties=fp)
    ax1.legend(prop=get_chinese_font(9))
    ax1.grid(True, linestyle="--", alpha=0.35)
    colors = ["#ef5350" if v >= 0 else "#26a69a" for v in df["macd_hist"]]
    ax2.bar(dates, df["macd_hist"], color=colors, width=1.0, alpha=0.85)
    ax2.axhline(0, color="#888", linewidth=0.8)
    ax2.set_xlabel("交易日期", fontproperties=fp)
    ax2.set_ylabel("柱", fontproperties=fp)
    ax2.grid(True, linestyle="--", alpha=0.35)
    plt.xticks(rotation=30)
    plt.tight_layout()
    fig.savefig(fig_dir / "fig_macd.png", dpi=180, bbox_inches="tight")
    plt.close(fig)

    # 图4 ATR
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(dates, df["atr_14"], color="#00897b", linewidth=1.4)
    ax.set_title(spec["indicators"]["ATR"]["plot"]["title"], fontproperties=fp_title)
    ax.set_xlabel("交易日期", fontproperties=fp)
    ax.set_ylabel("ATR（港元）", fontproperties=fp)
    ax.grid(True, linestyle="--", alpha=0.35)
    plt.xticks(rotation=30)
    plt.tight_layout()
    fig.savefig(fig_dir / "fig_atr.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    spec = load_spec()
    ind_cfg = spec["indicators"]
    params = {
        "rsi_period": ind_cfg["RSI"]["parameters"]["period"],
        "macd": ind_cfg["MACD"]["parameters"],
        "boll": ind_cfg["BOLL"]["parameters"],
        "atr_period": ind_cfg["ATR"]["parameters"]["period"],
    }

    print(">>> P2 获取港股日线")
    df_raw = fetch_hk_daily(spec)
    errors = validate_raw(df_raw, spec)
    if errors:
        raise RuntimeError("原始数据校验失败: " + "; ".join(errors))

    raw_dir = BASE / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = BASE / spec["data_fetch"]["output"]["raw_csv"]
    df_raw.assign(date=df_raw["date"].dt.strftime("%Y-%m-%d")).to_csv(
        raw_path, index=False, encoding="utf-8-sig"
    )
    print(f"  原始数据: {raw_path} ({len(df_raw)} 行)")

    print(">>> P3 计算指标")
    df = add_all_indicators(df_raw, params)
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")

    proc_dir = BASE / "data" / "processed"
    proc_dir.mkdir(parents=True, exist_ok=True)
    proc_path = BASE / spec["naming"]["processed"]
    df.to_csv(proc_path, index=False, encoding="utf-8-sig")
    print(f"  指标数据: {proc_path}")

    latest = df.iloc[-1]
    meta = {
        "instrument": spec["instrument"],
        "rows": len(df),
        "start_date": df["date"].iloc[0],
        "end_date": df["date"].iloc[-1],
        "computed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "spec_version": spec["spec"]["version"],
        "nan_counts": df[spec["schema"]["processed_daily"]["required_columns"]].isna().sum().to_dict(),
        "latest_snapshot": {
            "date": latest["date"],
            "close": round(float(latest["close"]), 2),
            "rsi_14": round(float(latest["rsi_14"]), 2),
            "macd_dif": round(float(latest["macd_dif"]), 4),
            "macd_dea": round(float(latest["macd_dea"]), 4),
            "macd_hist": round(float(latest["macd_hist"]), 4),
            "boll_mid": round(float(latest["boll_mid"]), 2),
            "boll_upper": round(float(latest["boll_upper"]), 2),
            "boll_lower": round(float(latest["boll_lower"]), 2),
            "atr_14": round(float(latest["atr_14"]), 4),
        },
    }
    meta_path = BASE / spec["naming"]["meta"]
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  元数据  : {meta_path}")

    print(">>> P4 生成图表")
    df_plot = df.copy()
    df_plot["date"] = pd.to_datetime(df_plot["date"])
    plot_figures(df_plot, spec)
    print(f"  图表目录: {BASE / 'data' / 'figures'}")

    print("\n完成。最新指标摘要:")
    print(json.dumps(meta["latest_snapshot"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
