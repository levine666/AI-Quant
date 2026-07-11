#!/usr/bin/env python3
"""同步 CSV 与 A/H 数据到 AI-Quant 各应用，并生成 registry。"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AI_QUANT = Path(__file__).resolve().parents[1]
SCRIPTS = AI_QUANT / "scripts"

LAB = AI_QUANT / "indicator-lab"
STRATEGY_LAB = AI_QUANT / "strategy-lab"
TURTLE_LAB = AI_QUANT / "turtle-lab"
AH_DATA = AI_QUANT / "data"

SYNC_MAP = {
    "smic_hk_00981_daily.csv": [
        ROOT / "TASK2/task02_indicator_lab/data/raw/smic_hk_00981_daily.csv",
        ROOT / "ai-quant-lab/data/smic_hk_00981_daily.csv",
        ROOT / "data/smic_00981_hk.csv",
    ],
    "smic_688981_daily.csv": [
        ROOT / "data/raw/smic/daily_688981_qfq.csv",
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


def write_csv_no_bom(src: Path, dst: Path) -> None:
    text = src.read_text(encoding="utf-8-sig")
    dst.write_text(text, encoding="utf-8")


def sync_csv_data(dst_dir: Path, label: str) -> None:
    dst_dir.mkdir(parents=True, exist_ok=True)
    for name, candidates in SYNC_MAP.items():
        target = dst_dir / name
        for src in candidates:
            if src.exists():
                write_csv_no_bom(src, target)
                print(f"  {src.relative_to(ROOT)} -> {label}/data/{name}")
                break
        else:
            if target.exists():
                print(f"  保留已有 {label}/data/{name}")
            else:
                print(f"  警告: 未找到 {name} 数据源")


def sync_ah_data() -> None:
    AH_DATA.mkdir(parents=True, exist_ok=True)
    for name in ("stock_data.js", "smic_compare.json"):
        src = ROOT / "data" / name
        if src.exists():
            shutil.copy2(src, AH_DATA / name)
            print(f"  {src.relative_to(ROOT)} -> AI-Quant/data/{name}")


def sync_public_legacy() -> None:
    """兼容旧路径：同步到仓库根 indicator-lab / strategy-lab。"""
    for src, name in [(LAB, "indicator-lab"), (STRATEGY_LAB, "strategy-lab")]:
        public = ROOT / name
        if public.exists():
            shutil.rmtree(public)
        shutil.copytree(src, public, ignore=shutil.ignore_patterns(".DS_Store"))
        (public / ".nojekyll").touch(exist_ok=True)
        print(f"  -> {name}/ (legacy)")


def main() -> None:
    print("同步 indicator-lab / strategy-lab / turtle-lab CSV …")
    sync_csv_data(LAB / "data", "indicator-lab")
    sync_csv_data(STRATEGY_LAB / "data", "strategy-lab")
    sync_csv_data(TURTLE_LAB / "data", "turtle-lab")
    sync_ah_data()
    sync_public_legacy()
    (TURTLE_LAB / ".nojekyll").touch(exist_ok=True)
    (AI_QUANT / ".nojekyll").touch(exist_ok=True)

    print("生成 apps/registry.json …")
    subprocess.run([sys.executable, str(SCRIPTS / "build_registry.py")], cwd=ROOT, check=True)
    print("完成。")


if __name__ == "__main__":
    main()
