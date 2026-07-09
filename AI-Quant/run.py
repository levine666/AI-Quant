#!/usr/bin/env python3
"""AI-Quant 本地入口：同步数据并启动 HTTP 服务（避免 file:// 导致 fetch 失败）。"""

from __future__ import annotations

import argparse
import subprocess
import sys
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent / "scripts"


def main() -> None:
    parser = argparse.ArgumentParser(description="AI-Quant 本地开发")
    parser.add_argument(
        "command",
        nargs="?",
        default="serve",
        choices=["sync", "serve"],
        help="sync=同步 CSV, serve=启动本地 HTTP 服务",
    )
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--open", choices=["dashboard", "indicator", "strategy"], default="dashboard")
    args = parser.parse_args()

    if args.command == "sync":
        subprocess.run([sys.executable, str(SCRIPTS / "sync_data.py")], cwd=ROOT, check=True)
        return

    subprocess.run([sys.executable, str(SCRIPTS / "sync_data.py")], cwd=ROOT, check=False)

    urls = {
        "dashboard": f"http://127.0.0.1:{args.port}/dashboard.html",
        "indicator": f"http://127.0.0.1:{args.port}/indicator-lab/",
        "strategy": f"http://127.0.0.1:{args.port}/strategy-lab/",
    }
    target = urls[args.open]

    print("AI-Quant 本地服务（请勿直接双击 HTML 文件）")
    print(f"  A/H 对比:      {urls['dashboard']}")
    print(f"  Indicator Lab: {urls['indicator']}")
    print(f"  Strategy Lab:  {urls['strategy']}")
    print(f"\n正在打开 {target}\n")

    webbrowser.open(target)
    subprocess.run(
        [sys.executable, "-m", "http.server", str(args.port), "--bind", "127.0.0.1"],
        cwd=ROOT,
        check=True,
    )


if __name__ == "__main__":
    main()
