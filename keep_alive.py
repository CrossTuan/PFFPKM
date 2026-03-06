from __future__ import annotations

import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer


class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in {"/", "/healthz"}:
            body = b"ok"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.end_headers()

    def log_message(self, format: str, *args):
        return


def start_keep_alive() -> None:
    port_raw = os.getenv("PORT", "").strip()
    if not port_raw:
        print("[health] PORT is not set; health server is disabled.")
        return

    try:
        port = int(port_raw)
    except ValueError:
        print(f"[health] Invalid PORT value: {port_raw!r}; health server is disabled.")
        return

    server = HTTPServer(("0.0.0.0", port), _HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"[health] Health server listening on 0.0.0.0:{port}")
