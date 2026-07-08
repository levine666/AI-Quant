#!/usr/bin/env python3
"""兼容入口：转发到 ai-quant-lab/scripts/sync_data.py。"""

import subprocess
import sys
from pathlib import Path

LAB_SYNC = Path(__file__).resolve().parents[3] / "ai-quant-lab" / "scripts" / "sync_data.py"


def main() -> None:
    if not LAB_SYNC.exists():
        raise SystemExit(f"未找到 {LAB_SYNC}")
    subprocess.run([sys.executable, str(LAB_SYNC)], check=True)


if __name__ == "__main__":
    main()
