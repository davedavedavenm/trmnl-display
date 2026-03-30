#!/usr/bin/env python3
import json
import os
import subprocess
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


HOST = os.getenv("TRMNL_MODE_BRIDGE_HOST", "0.0.0.0")
PORT = int(os.getenv("TRMNL_MODE_BRIDGE_PORT", "8787"))
TOKEN = os.getenv("TRMNL_MODE_BRIDGE_TOKEN", "")
MODE_SCRIPT = os.getenv("TRMNL_MODE_SCRIPT", "/home/dave/bin/trmnl-set-display-mode")
ALLOWED_MODES = {"idle", "calendar", "sonos", "jen_commute", "dave_commute", "alert", "status"}


class Handler(BaseHTTPRequestHandler):
    server_version = "TRMNLModeBridge/1.0"

    def _send(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path != "/health":
            self._send(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        self._send(HTTPStatus.OK, {"ok": True})

    def do_POST(self) -> None:
        if self.path != "/mode":
            self._send(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return

        if TOKEN:
            auth = self.headers.get("Authorization", "")
            if auth != f"Bearer {TOKEN}":
                self._send(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
                return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError):
            self._send(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})
            return

        mode = payload.get("mode", "")
        if mode not in ALLOWED_MODES:
            self._send(HTTPStatus.BAD_REQUEST, {"error": "invalid_mode", "mode": mode})
            return

        result = subprocess.run(
            [MODE_SCRIPT, mode],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )

        response = {
            "mode": mode,
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
        status = HTTPStatus.OK if result.returncode == 0 else HTTPStatus.BAD_GATEWAY
        self._send(status, response)

    def log_message(self, format: str, *args) -> None:
        return


if __name__ == "__main__":
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
