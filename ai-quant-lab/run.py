#!/usr/bin/env python3
"""AI Quant Lab 入口：同步数据 / 跑指标 pipeline。"""

import argparse
import subprocess
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parent
SCRIPTS = LAB / "scripts"


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Quant Lab")
    parser.add_argument(
        "command",
        nargs="?",
        default="sync",
        choices=["sync", "pipeline", "serve"],
        help="sync=同步CSV, pipeline=港股指标流水线, serve=启动本地服务",
    )
    parser.add_argument("--port", type=int, default=8877, help="serve 端口")
    args = parser.parse_args()

    if args.command == "sync":
        subprocess.run([sys.executable, str(SCRIPTS / "sync_data.py")], check=True)
    elif args.command == "pipeline":
        subprocess.run([sys.executable, str(SCRIPTS / "run_pipeline.py")], check=True)
        subprocess.run([sys.executable, str(SCRIPTS / "sync_data.py")], check=False)
    elif args.command == "serve":
        print(f"启动 http://127.0.0.1:{args.port}/index.html")
        subprocess.run(
            [sys.executable, "-m", "http.server", str(args.port)],
            cwd=LAB,
            check=True,
        )


if __name__ == "__main__":
    main()
