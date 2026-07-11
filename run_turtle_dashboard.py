#!/usr/bin/env python3
"""启动海龟看板（Python 回测 API + 静态页面）。"""

from __future__ import annotations

import argparse
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

BASE = Path(__file__).resolve().parent


def find_free_port(host: str, start: int, tries: int = 20) -> int:
    for port in range(start, start + tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind((host, port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"无法在 {start}~{start + tries - 1} 找到可用端口")


def ensure_manifest() -> None:
    manifest = BASE / "data" / "turtle" / "manifest.json"
    if manifest.exists():
        return
    subprocess.check_call(
        [sys.executable, str(BASE / "refresh_turtle_data.py"), "--validate-only"],
        cwd=BASE,
    )


def open_browser_later(url: str, delay: float = 0.6) -> None:
    def _open() -> None:
        time.sleep(delay)
        webbrowser.open(url)

    threading.Thread(target=_open, daemon=True).start()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Turtle Lab dashboard",
        epilog="Mac 请用: python3 run_turtle_dashboard.py  或  ./start_turtle_dashboard.sh",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-open", action="store_true")
    parser.add_argument("--no-auto-port", action="store_true", help="端口占用时不自动换端口")
    args = parser.parse_args()

    ensure_manifest()

    port = args.port
    if not args.no_auto_port:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((args.host, port))
        except OSError:
            new_port = find_free_port(args.host, port + 1)
            print(f"端口 {port} 已被占用，自动改用 {new_port}")
            port = new_port

    url = f"http://{args.host}:{port}/"
    print(f"Turtle Lab → {url}")
    print("请保持此终端窗口打开；按 Ctrl+C 停止服务")

    sys.path.insert(0, str(BASE))
    from turtle_dashboard.server import run

    if not args.no_open:
        open_browser_later(url)

    run(host=args.host, port=port)


if __name__ == "__main__":
    main()
