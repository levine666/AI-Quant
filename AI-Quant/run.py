#!/usr/bin/env python3
"""AI-Quant 本地入口：同步数据并启动 HTTP 服务。"""

from __future__ import annotations

import argparse
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AI_QUANT = Path(__file__).resolve().parent
SCRIPTS = AI_QUANT / "scripts"


def find_free_port(host: str, start: int) -> int:
    for port in range(start, start + 30):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind((host, port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"无法找到可用端口（从 {start} 起）")


def wait_for_server(url: str, timeout: float = 15.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, TimeoutError, ConnectionResetError):
            time.sleep(0.25)
    return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AI-Quant 本地开发",
        epilog="Mac 请用: python3 AI-Quant/run.py serve",
    )
    parser.add_argument("command", nargs="?", default="serve", choices=["sync", "serve"])
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument(
        "--open",
        choices=["home", "ah_compare", "indicator", "strategy", "turtle"],
        default="home",
    )
    parser.add_argument("--api", action="store_true", help="启用 Python 回测 API")
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()

    if args.command == "sync":
        subprocess.run([sys.executable, str(SCRIPTS / "sync_data.py")], cwd=ROOT, check=True)
        return

    print("正在同步数据…")
    subprocess.run([sys.executable, str(SCRIPTS / "sync_data.py")], cwd=ROOT, check=False)

    host = "127.0.0.1"
    try:
        port = find_free_port(host, args.port)
    except RuntimeError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)

    if port != args.port:
        print(f"注意: 端口 {args.port} 已被占用，改用 {port}")

    paths = {
        "home": "/",
        "ah_compare": "/ah-compare/",
        "indicator": "/indicator-lab/",
        "strategy": "/strategy-lab/",
        "turtle": "/turtle-lab/",
    }
    base = f"http://{host}:{port}"
    home_url = base + "/"
    target = base + paths[args.open]

    print("")
    print("=" * 50)
    print("  AI-Quant 本地服务")
    print("=" * 50)
    print(f"  首页:  {home_url}")
    print(f"  海龟:  {base}/turtle-lab/")
    print("")
    print("  ⚠ 请保持此窗口运行，关闭即停止服务")
    print("  ⚠ 请勿双击 HTML 文件，必须用浏览器打开上面地址")
    print("=" * 50)
    print("")

    if args.api:
        sys.path.insert(0, str(ROOT))
        import threading

        import turtle_dashboard.server as srv

        srv.DASHBOARD = AI_QUANT

        class ReuseServer(srv.ThreadingHTTPServer):
            allow_reuse_address = True

        server = ReuseServer((host, port), srv.TurtleHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
    else:
        proc = subprocess.Popen(
            [sys.executable, "-m", "http.server", str(port), "--bind", host],
            cwd=AI_QUANT,
        )

    if not wait_for_server(home_url):
        print("错误: 服务启动超时，请检查终端报错。", file=sys.stderr)
        if not args.api:
            proc.terminate()
        sys.exit(1)

    print(f"✓ 服务已就绪 → {home_url}\n")

    if not args.no_open:
        webbrowser.open(target)

    try:
        if args.api:
            thread.join()
        else:
            proc.wait()
    except KeyboardInterrupt:
        print("\n已停止。")
        if not args.api:
            proc.terminate()


if __name__ == "__main__":
    main()
