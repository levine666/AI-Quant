#!/usr/bin/env python3
"""TASK2：数据诊断、指标计算与图表生成。"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

BASE = Path(__file__).resolve().parent
LAB = BASE / "task02_indicator_lab"
sys.path.insert(0, str(LAB / "scripts"))

from font_utils import apply_global_font, get_chinese_font
from indicators import add_all_indicators, compute_atr

DATA_PATH = LAB / "data" / "raw" / "smic_hk_00981_daily.csv"
FIG_DIR = BASE / "figures"
REPORT_DIR = BASE / "report"
STOCK_NAME = "中芯国际"
STOCK_CODE = "00981"
MARKET = "港股"


def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH)
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date").reset_index(drop=True)


def diagnose(df: pd.DataFrame) -> dict:
    numeric_cols = ["open", "high", "low", "close", "volume", "amount"]
    missing = df.isna().sum().to_dict()
    missing_pct = {k: round(v / len(df) * 100, 2) for k, v in missing.items()}
    desc = df[numeric_cols].describe().round(4)
    dup_dates = int(df["date"].duplicated().sum())
    invalid_price = int((df["high"] < df["low"]).sum())
    report = {
        "rows": len(df),
        "date_range": f"{df['date'].iloc[0].date()} ~ {df['date'].iloc[-1].date()}",
        "missing_count": missing,
        "missing_pct": missing_pct,
        "duplicate_dates": dup_dates,
        "invalid_high_low": invalid_price,
        "describe": desc.to_dict(),
        "diagnosed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    return report


def plot_diagnostic(df: pd.DataFrame, diag: dict) -> Path:
    """图1 数据诊断：收盘价分布与成交量描述。"""
    fp = apply_global_font()
    fp_title = get_chinese_font(12)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))

    axes[0].hist(df["close"], bins=30, color="#5b8def", alpha=0.75, edgecolor="white")
    axes[0].axvline(df["close"].mean(), color="#ef5350", linestyle="--", label=f"均值 {df['close'].mean():.2f}")
    axes[0].set_title("收盘价分布", fontproperties=fp_title)
    axes[0].set_xlabel("收盘价（港元）", fontproperties=fp)
    axes[0].set_ylabel("频数", fontproperties=fp)
    axes[0].legend(prop=get_chinese_font(9))

    vol = df["volume"] / 1e6
    axes[1].plot(df["date"], vol, color="#00897b", linewidth=1)
    axes[1].set_title("成交量时序（百万股）", fontproperties=fp_title)
    axes[1].set_xlabel("日期", fontproperties=fp)
    axes[1].set_ylabel("成交量", fontproperties=fp)
    axes[1].tick_params(axis="x", rotation=30)

    fig.suptitle(
        f"图1  {STOCK_NAME}（{STOCK_CODE}）数据基础诊断",
        fontproperties=fp_title,
        y=1.02,
    )
    plt.tight_layout()
    out = FIG_DIR / "fig1_diagnostic.png"
    fig.savefig(out, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return out


def compute_and_plot_indicators(df: pd.DataFrame) -> pd.DataFrame:
    params = {
        "rsi_period": 14,
        "macd": {"fast_period": 12, "slow_period": 26, "signal_period": 9},
        "boll": {"period": 20, "std_multiplier": 2.0},
        "atr_period": 14,
    }
    result = add_all_indicators(df, params)
    fp = apply_global_font()
    fp_title = get_chinese_font(12)
    dates = result["date"]

    # 图2 BOLL
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(dates, result["close"], label="收盘价", color="#1565C0", linewidth=1.4)
    ax.plot(dates, result["boll_mid"], label="中轨", color="#888", linewidth=1)
    ax.plot(dates, result["boll_upper"], label="上轨", color="#ef5350", linestyle="--", linewidth=0.9)
    ax.plot(dates, result["boll_lower"], label="下轨", color="#26a69a", linestyle="--", linewidth=0.9)
    ax.fill_between(dates, result["boll_lower"], result["boll_upper"], alpha=0.06, color="#888")
    ax.set_title(f"图2  {STOCK_NAME}（{STOCK_CODE}）收盘价与布林带(20,2)", fontproperties=fp_title)
    ax.set_xlabel("交易日期", fontproperties=fp)
    ax.set_ylabel("价格（港元）", fontproperties=fp)
    ax.legend(prop=get_chinese_font(9))
    ax.grid(True, linestyle="--", alpha=0.35)
    plt.xticks(rotation=30)
    plt.tight_layout()
    fig.savefig(FIG_DIR / "fig2_boll.png", dpi=180, bbox_inches="tight")
    plt.close(fig)

    # 图3 RSI
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(dates, result["rsi_14"], color="#b388ff", linewidth=1.4)
    for y, c in [(70, "#ef5350"), (50, "#888"), (30, "#26a69a")]:
        ax.axhline(y, color=c, linestyle="--", linewidth=0.8, alpha=0.7)
    ax.set_ylim(0, 100)
    ax.set_title(f"图3  {STOCK_NAME}（{STOCK_CODE}）RSI(14)", fontproperties=fp_title)
    ax.set_xlabel("交易日期", fontproperties=fp)
    ax.set_ylabel("RSI", fontproperties=fp)
    ax.grid(True, linestyle="--", alpha=0.35)
    plt.xticks(rotation=30)
    plt.tight_layout()
    fig.savefig(FIG_DIR / "fig3_rsi.png", dpi=180, bbox_inches="tight")
    plt.close(fig)

    # 图4 MACD
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True, gridspec_kw={"height_ratios": [2, 1]})
    ax1.plot(dates, result["macd_dif"], label="DIF", color="#1565C0", linewidth=1.2)
    ax1.plot(dates, result["macd_dea"], label="DEA", color="#f5a623", linewidth=1.2)
    ax1.set_title(f"图4  {STOCK_NAME}（{STOCK_CODE}）MACD(12,26,9)", fontproperties=fp_title)
    ax1.set_ylabel("MACD", fontproperties=fp)
    ax1.legend(prop=get_chinese_font(9))
    ax1.grid(True, linestyle="--", alpha=0.35)
    colors = ["#ef5350" if v >= 0 else "#26a69a" for v in result["macd_hist"]]
    ax2.bar(dates, result["macd_hist"], color=colors, width=1.0, alpha=0.85)
    ax2.axhline(0, color="#888", linewidth=0.8)
    ax2.set_xlabel("交易日期", fontproperties=fp)
    ax2.set_ylabel("柱", fontproperties=fp)
    ax2.grid(True, linestyle="--", alpha=0.35)
    plt.xticks(rotation=30)
    plt.tight_layout()
    fig.savefig(FIG_DIR / "fig4_macd.png", dpi=180, bbox_inches="tight")
    plt.close(fig)

    # 图5 ATR（扩展指标）
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(dates, result["atr_14"], color="#00897b", linewidth=1.4)
    ax.set_title(f"图5  {STOCK_NAME}（{STOCK_CODE}）ATR(14) 扩展指标", fontproperties=fp_title)
    ax.set_xlabel("交易日期", fontproperties=fp)
    ax.set_ylabel("ATR（港元）", fontproperties=fp)
    ax.grid(True, linestyle="--", alpha=0.35)
    plt.xticks(rotation=30)
    plt.tight_layout()
    fig.savefig(FIG_DIR / "fig5_atr.png", dpi=180, bbox_inches="tight")
    plt.close(fig)

    return result


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"加载数据: {DATA_PATH}")
    df = load_data()
    diag = diagnose(df)
    (REPORT_DIR / "diagnostic.json").write_text(
        json.dumps(diag, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"  {diag['rows']} 行, {diag['date_range']}")
    print(f"  缺失值: {diag['missing_count']}")

    plot_diagnostic(df, diag)
    result = compute_and_plot_indicators(df)
    result.assign(date=result["date"].dt.strftime("%Y-%m-%d")).to_csv(
        REPORT_DIR / "indicators_result.csv", index=False, encoding="utf-8-sig"
    )

    latest = result.iloc[-1]
    snap = {
        "date": str(latest["date"].date()),
        "close": round(float(latest["close"]), 2),
        "rsi_14": round(float(latest["rsi_14"]), 2),
        "macd_dif": round(float(latest["macd_dif"]), 4),
        "macd_dea": round(float(latest["macd_dea"]), 4),
        "macd_hist": round(float(latest["macd_hist"]), 4),
        "boll_mid": round(float(latest["boll_mid"]), 2),
        "atr_14": round(float(latest["atr_14"]), 4),
    }
    (REPORT_DIR / "latest_snapshot.json").write_text(
        json.dumps(snap, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("图表已保存至 figures/")
    print("最新指标:", json.dumps(snap, ensure_ascii=False))


if __name__ == "__main__":
    main()
