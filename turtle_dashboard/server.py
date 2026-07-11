"""Turtle Lab HTTP 服务：静态看板 + /api/* JSON 接口。"""

from __future__ import annotations

import json
import mimetypes
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

BASE = Path(__file__).resolve().parent.parent
DASHBOARD = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

from quant_backtest.turtle_runner import (  # noqa: E402
    build_manifest_from_spec,
    load_manifest,
    run_turtle_backtest,
)


class TurtleHandler(BaseHTTPRequestHandler):
    server_version = "TurtleLab/1.0"

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _json_response(self, code: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw.decode("utf-8"))

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/manifest":
            try:
                manifest = load_manifest()
            except Exception:
                manifest = build_manifest_from_spec()
            self._json_response(200, manifest)
            return
        if path == "/api/health":
            self._json_response(200, {"status": "ok"})
            return
        self._serve_static(path)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/backtest":
            body = self._read_json()
            result = run_turtle_backtest(body)
            code = 400 if result.get("error") else 200
            self._json_response(code, result)
            return
        if path == "/api/refresh":
            body = self._read_json()
            stock_id = body.get("stock_id")
            cmd = [sys.executable, str(BASE / "refresh_turtle_data.py")]
            if stock_id:
                cmd.extend(["--stock-id", stock_id])
            try:
                subprocess.run(cmd, cwd=BASE, check=True, capture_output=True, text=True)
                manifest = load_manifest()
                self._json_response(200, {"ok": True, "manifest": manifest})
            except subprocess.CalledProcessError as e:
                self._json_response(
                    500,
                    {"ok": False, "error": e.stderr or str(e)},
                )
            return
        self.send_error(404)

    def _serve_static(self, url_path: str) -> None:
        if url_path in ("/", ""):
            url_path = "/index.html"
        file_path = (DASHBOARD / url_path.lstrip("/")).resolve()
        if not str(file_path).startswith(str(DASHBOARD.resolve())):
            self.send_error(403)
            return
        if not file_path.exists() or not file_path.is_file():
            self.send_error(404)
            return
        content = file_path.read_bytes()
        mime, _ = mimetypes.guess_type(str(file_path))
        self.send_response(200)
        self.send_header("Content-Type", mime or "application/octet-stream")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


def run(host: str = "127.0.0.1", port: int = 8765, *, open_browser: bool = False) -> None:
    if not (BASE / "data" / "turtle" / "manifest.json").exists():
        build_manifest_from_spec()

    class ReuseServer(ThreadingHTTPServer):
        allow_reuse_address = True

    server = ReuseServer((host, port), TurtleHandler)
    url = f"http://{host}:{port}/"
    if open_browser:
        import threading
        import time
        import webbrowser

        def _open() -> None:
            time.sleep(0.5)
            webbrowser.open(url)

        threading.Thread(target=_open, daemon=True).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止服务")


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8765)
    run(**vars(p.parse_args()))
