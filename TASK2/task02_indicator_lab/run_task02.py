#!/usr/bin/env python3
"""TASK02 入口：执行 spec 全流程，并同步到 ai-quant-lab。"""

import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
LAB = BASE.parent.parent / "ai-quant-lab"


def main() -> None:
    pipeline = (LAB / "scripts" / "run_pipeline.py") if (LAB / "scripts" / "run_pipeline.py").exists() else BASE / "scripts" / "run_pipeline.py"
    sync = LAB / "scripts" / "sync_data.py"
    subprocess.run([sys.executable, str(pipeline)], check=True)
    if sync.exists():
        subprocess.run([sys.executable, str(sync)], check=False)


if __name__ == "__main__":
    main()

