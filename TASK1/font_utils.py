#!/usr/bin/env python3
"""Mac 中文字体配置，供 matplotlib 绘图使用。"""

from __future__ import annotations

from pathlib import Path

from matplotlib import font_manager
from matplotlib.font_manager import FontProperties


def get_chinese_font(size: float = 10.5) -> FontProperties:
    """注册并返回 Mac 可用的中文字体（宋体优先）。"""
    candidates = [
        "/System/Library/Fonts/Supplemental/Songti.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            try:
                font_manager.fontManager.addfont(path)
            except Exception:
                pass
            name = font_manager.FontProperties(fname=path).get_name()
            return FontProperties(fname=path, size=size)
    return FontProperties(family="PingFang SC", size=size)


def apply_global_font() -> FontProperties:
    """设置全局 rcParams，并返回正文字体。"""
    fp = get_chinese_font(10.5)
    family = fp.get_name()
    import matplotlib.pyplot as plt

    plt.rcParams["font.sans-serif"] = [family, "PingFang SC", "Heiti SC", "Arial Unicode MS"]
    plt.rcParams["axes.unicode_minus"] = False
    return fp
