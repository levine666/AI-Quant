"""Mac 中文字体配置。"""

from __future__ import annotations

from pathlib import Path

from matplotlib import font_manager
from matplotlib.font_manager import FontProperties


def get_chinese_font(size: float = 10.5) -> FontProperties:
    candidates = [
        "/System/Library/Fonts/Supplemental/Songti.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
    ]
    for path in candidates:
        if Path(path).exists():
            try:
                font_manager.fontManager.addfont(path)
            except Exception:
                pass
            return FontProperties(fname=path, size=size)
    return FontProperties(family="PingFang SC", size=size)


def apply_global_font() -> FontProperties:
    fp = get_chinese_font(10.5)
    import matplotlib.pyplot as plt

    plt.rcParams["font.sans-serif"] = [
        fp.get_name(),
        "PingFang SC",
        "Heiti SC",
        "Arial Unicode MS",
    ]
    plt.rcParams["axes.unicode_minus"] = False
    return fp
