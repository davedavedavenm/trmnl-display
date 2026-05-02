#!/usr/bin/env python3
import json
import os
from pathlib import Path
import subprocess
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


HOST = os.getenv("TRMNL_MODE_BRIDGE_HOST", "0.0.0.0")
PORT = int(os.getenv("TRMNL_MODE_BRIDGE_PORT", "8787"))
TOKEN = os.getenv("TRMNL_MODE_BRIDGE_TOKEN", "")
MODE_SCRIPT = os.getenv("TRMNL_MODE_SCRIPT", "/home/dave/bin/trmnl-set-display-mode")
ALLOWED_MODES = {"idle", "calendar", "sonos", "jen_commute", "jen_morning", "dave_commute", "ha_dashboard", "alert", "status"}
HA_REFRESH_SCRIPT = os.getenv("TRMNL_HA_REFRESH_SCRIPT", "/home/dave/bin/trmnl-refresh-ha-sidecar")
HA_REFRESH_COOLDOWN_SECONDS = int(os.getenv("TRMNL_HA_REFRESH_COOLDOWN_SECONDS", "120"))
HA_REFRESH_STATE_FILE = Path(os.getenv("TRMNL_HA_REFRESH_STATE_FILE", "/tmp/trmnl-ha-sidecar-refresh.json"))


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

    def _authorized(self) -> bool:
        if not TOKEN:
            return True
        return self.headers.get("Authorization", "") == f"Bearer {TOKEN}"

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length) or b"{}")
        return payload if isinstance(payload, dict) else {}

    def _last_ha_refresh(self) -> float:
        try:
            with HA_REFRESH_STATE_FILE.open("r", encoding="utf-8") as f:
                payload = json.load(f)
            return float(payload.get("last_success", 0))
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return 0

    def _record_ha_refresh(self) -> None:
        HA_REFRESH_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with HA_REFRESH_STATE_FILE.open("w", encoding="utf-8") as f:
            json.dump({"last_success": time.time()}, f)

    def do_POST(self) -> None:
        if self.path == "/ha-dashboard/refresh":
            self._handle_ha_dashboard_refresh()
            return

        if self.path != "/mode":
            self._send(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return

        if not self._authorized():
            self._send(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
            return

        try:
            payload = self._read_json()
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

    def _handle_ha_dashboard_refresh(self) -> None:
        if not self._authorized():
            self._send(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
            return

        try:
            payload = self._read_json()
        except (ValueError, json.JSONDecodeError):
            self._send(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})
            return

        now = time.time()
        last_success = self._last_ha_refresh()
        remaining = int(HA_REFRESH_COOLDOWN_SECONDS - (now - last_success))
        if not payload.get("force") and remaining > 0:
            self._send(
                HTTPStatus.OK,
                {
                    "refresh": "skipped",
                    "reason": "cooldown",
                    "cooldown_seconds": HA_REFRESH_COOLDOWN_SECONDS,
                    "retry_after_seconds": remaining,
                },
            )
            return

        result = subprocess.run(
            [HA_REFRESH_SCRIPT],
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )

        if result.returncode == 0:
            self._record_ha_refresh()

        response = {
            "refresh": "completed" if result.returncode == 0 else "failed",
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
