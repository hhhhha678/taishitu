from __future__ import annotations

import json
import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"
sys.path.insert(0, str(ROOT / "backend"))

from app.dashboard_loader import repository  # noqa: E402


class DashboardPreviewHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def do_GET(self):
        if self.path in {"/", "/static/index.html"}:
            self.path = "/index.html"
            return super().do_GET()
        if self.path.startswith("/static/"):
            self.path = self.path.removeprefix("/static")
            return super().do_GET()
        if self.path.startswith("/api/dashboard"):
            data = json.dumps(repository.get_dashboard(), ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if self.path.startswith("/api/health"):
            data = b'{"status":"ok"}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        return super().do_GET()


if __name__ == "__main__":
    port = int(os.getenv("PORT", sys.argv[1] if len(sys.argv) > 1 else "8003"))
    ThreadingHTTPServer(("127.0.0.1", port), DashboardPreviewHandler).serve_forever()
