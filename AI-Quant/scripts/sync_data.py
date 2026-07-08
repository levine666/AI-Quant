#!/usr/bin/env python3
"""同步日线 CSV 到 AI-Quant/indicator-lab/data，供 GitHub Pages 前端读取。"""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LAB = Path(__file__).resolve().parents[1] / "indicator-lab"
DST = LAB / "data"

SYNC_MAP = {
    "smic_hk_00981_daily.csv": [
        ROOT / "TASK2/task02_indicator_lab/data/raw/smic_hk_00981_daily.csv",
        ROOT / "ai-quant-lab/data/smic_hk_00981_daily.csv",
        ROOT / "data/smic_00981_hk.csv",
    ],
    "smic_688981_daily.csv": [
        ROOT / "data/raw/smic/daily_688981_qfq.csv",
        ROOT / "TASK1/data/smic_688981_daily.csv",
        ROOT / "data/smic_688981_a.csv",
    ],
    "byd_002594_daily.csv": [
        ROOT / "data/raw/byd/daily_002594_qfq.csv",
        ROOT / "ai-quant-lab/data/byd_002594_daily.csv",
    ],
    "cyp_600900_daily.csv": [
        ROOT / "data/raw/cyp/daily_600900_qfq.csv",
        ROOT / "ai-quant-lab/data/cyp_600900_daily.csv",
    ],
}


def main() -> None:
    DST.mkdir(parents=True, exist_ok=True)
    for name, candidates in SYNC_MAP.items():
        target = DST / name
        for src in candidates:
            if src.exists():
                shutil.copy2(src, target)
                print(f"  {src.relative_to(ROOT)} -> indicator-lab/data/{name}")
                break
        else:
            if target.exists():
                print(f"  保留已有 indicator-lab/data/{name}")
            else:
                print(f"  警告: 未找到 {name} 数据源")

    print("\nindicator-lab/data/ 文件清单:")
    for f in sorted(DST.glob("*.csv")):
        rows = sum(1 for _ in f.open(encoding="utf-8-sig")) - 1
        print(f"  {f.name}: {rows} 行")


if __name__ == "__main__":
    main()
