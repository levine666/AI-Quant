#!/usr/bin/env python3
"""使用 AkShare 获取中芯国际 A 股近一年日线数据、绘图并保存 CSV。"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import akshare as ak
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

STOCK_NAME = "中芯国际"
STOCK_CODE = "688981"
SYMBOL = "sh688981"

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
FIG_DIR = BASE_DIR / "figures"


def fetch_daily() -> pd.DataFrame:
    end_dt = datetime.now()
    start_dt = end_dt - timedelta(days=365)
    start_date = start_dt.strftime("%Y%m%d")
    end_date = end_dt.strftime("%Y%m%d")

    df = ak.stock_zh_a_daily(
        symbol=SYMBOL,
        start_date=start_date,
        end_date=end_date,
        adjust="qfq",
    )
    df = df.sort_values("date").reset_index(drop=True)
    df["date"] = pd.to_datetime(df["date"])
    return df


def save_csv(df: pd.DataFrame) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out = DATA_DIR / f"smic_{STOCK_CODE}_daily.csv"
    df.assign(date=df["date"].dt.strftime("%Y-%m-%d")).to_csv(
        out, index=False, encoding="utf-8-sig"
    )
    return out


def plot_close_price(df: pd.DataFrame) -> Path:
    from font_utils import apply_global_font, get_chinese_font

    fp = apply_global_font()
    fp_title = get_chinese_font(13)
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(df["date"], df["close"], color="#1565C0", linewidth=1.6, label="收盘价")
    ax.fill_between(df["date"], df["close"], alpha=0.08, color="#1565C0")

    ax.set_title(f"图1  {STOCK_NAME}（{STOCK_CODE}）近一年每日收盘价", fontproperties=fp_title, pad=12)
    ax.set_xlabel("交易日期", fontproperties=fp)
    ax.set_ylabel("收盘价（元，前复权）", fontproperties=fp)
    ax.grid(True, linestyle="--", alpha=0.35)
    ax.legend(loc="upper left", prop=fp)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontproperties(fp)
    plt.xticks(rotation=30)
    plt.tight_layout()

    out = FIG_DIR / "fig1_close_price.png"
    fig.savefig(out, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return out


def plot_kline_volume(df: pd.DataFrame) -> Path:
    """matplotlib 手绘 K 线 + 成交量，Mac 上中文与刻度完整显示。"""
    from matplotlib.patches import Rectangle

    from font_utils import apply_global_font, get_chinese_font

    fp = apply_global_font()
    fp_title = get_chinese_font(13)
    fp_small = get_chinese_font(9)
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    plot_df = df.reset_index(drop=True)
    dates = plot_df["date"]
    x = range(len(plot_df))

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(10, 6.5), sharex=True, gridspec_kw={"height_ratios": [3, 1], "hspace": 0.08}
    )

    width = 0.6
    for idx, row in plot_df.iterrows():
        o, h, l, c = row["open"], row["high"], row["low"], row["close"]
        color = "#ef5350" if c >= o else "#26a69a"
        ax1.vlines(idx, l, h, color=color, linewidth=1)
        bottom = min(o, c)
        height = max(abs(c - o), 0.01)
        ax1.add_patch(Rectangle((idx - width / 2, bottom), width, height, facecolor=color, edgecolor=color))

    ax1.set_ylabel("价格（元）", fontproperties=fp)
    ax1.set_title(f"图2  {STOCK_NAME}（{STOCK_CODE}）日K线及成交量", fontproperties=fp_title, pad=10)
    ax1.grid(True, linestyle="--", alpha=0.35)

    vol_colors = [
        "#888888" if j == 0 else (
            "#ef5350" if plot_df["close"].iloc[j] >= plot_df["close"].iloc[j - 1] else "#26a69a"
        )
        for j in range(len(plot_df))
    ]
    ax2.bar(x, plot_df["volume"], width=0.8, color=vol_colors, alpha=0.85)
    ax2.set_ylabel("成交量（股）", fontproperties=fp)
    ax2.set_xlabel("交易日期", fontproperties=fp)
    ax2.grid(True, linestyle="--", alpha=0.35)

    def _vol_fmt(val, _pos):
        if val >= 1e8:
            return f"{val / 1e8:.1f}亿"
        if val >= 1e4:
            return f"{val / 1e4:.0f}万"
        return f"{val:.0f}"

    import numpy as np
    from matplotlib.ticker import FixedLocator

    vmax = float(plot_df["volume"].max())
    ticks = np.linspace(0, vmax, 5)
    ax2.set_yticks(ticks)
    ax2.yaxis.set_major_locator(FixedLocator(ticks))
    ax2.set_yticklabels([_vol_fmt(t, None) for t in ticks], fontproperties=fp)
    ax2.yaxis.get_offset_text().set_visible(False)

    tick_step = max(len(plot_df) // 8, 1)
    tick_idx = list(range(0, len(plot_df), tick_step))
    ax2.set_xticks(tick_idx)
    ax2.set_xticklabels([dates.iloc[i].strftime("%Y-%m") for i in tick_idx], rotation=30, fontproperties=fp)

    for ax in (ax1, ax2):
        for label in ax.get_yticklabels():
            label.set_fontproperties(fp)

    # 图例说明（红涨绿跌）
    from matplotlib.lines import Line2D
    legend_items = [
        Line2D([0], [0], color="#ef5350", lw=4, label="上涨"),
        Line2D([0], [0], color="#26a69a", lw=4, label="下跌"),
    ]
    ax1.legend(handles=legend_items, loc="upper left", prop=fp_small, framealpha=0.9)

    out = FIG_DIR / "fig2_kline_volume.png"
    fig.savefig(out, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return out


def main() -> None:
    print(f"正在通过 AkShare 获取 {STOCK_NAME}（{STOCK_CODE}）日线数据...")
    df = fetch_daily()
    csv_path = save_csv(df)
    fig1 = plot_close_price(df)
    fig2 = plot_kline_volume(df)

    ret = (df["close"].iloc[-1] / df["close"].iloc[0] - 1) * 100
    print(f"共 {len(df)} 个交易日")
    print(f"区间: {df['date'].iloc[0].date()} ~ {df['date'].iloc[-1].date()}")
    print(f"区间涨跌: {ret:+.2f}%")
    print(f"CSV : {csv_path}")
    print(f"图1 : {fig1}")
    print(f"图2 : {fig2}")


if __name__ == "__main__":
    main()
