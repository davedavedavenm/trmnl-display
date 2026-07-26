#!/usr/bin/env python3
import hashlib
import json
import logging
import os
import subprocess
import threading
import time
from datetime import date, timedelta
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

HOST = os.getenv("TRMNL_MODE_BRIDGE_HOST", "0.0.0.0")
PORT = int(os.getenv("TRMNL_MODE_BRIDGE_PORT", "8787"))
TOKEN = os.getenv("TRMNL_MODE_BRIDGE_TOKEN", "")
MODE_SCRIPT = os.getenv("TRMNL_MODE_SCRIPT", "/home/dave/bin/trmnl-set-display-mode")
ALLOWED_MODES = {"idle", "calendar", "sonos", "jen_commute", "jen_morning", "dave_commute", "ha_dashboard", "alert", "status", "bus"}
HA_REFRESH_SCRIPT = os.getenv("TRMNL_HA_REFRESH_SCRIPT", "/home/dave/bin/trmnl-refresh-ha-sidecar")
HA_REFRESH_COOLDOWN_SECONDS = int(os.getenv("TRMNL_HA_REFRESH_COOLDOWN_SECONDS", "120"))
HA_REFRESH_STATE_FILE = Path(os.getenv("TRMNL_HA_REFRESH_STATE_FILE", "/tmp/trmnl-ha-sidecar-refresh.json"))
MORNING_PUSH_SCRIPT = os.getenv("TRMNL_MORNING_PUSH_SCRIPT", "/home/dave/bin/trmnl-push-morning-data")
SONOS_REFRESH_SCRIPT = os.getenv("TRMNL_SONOS_REFRESH_SCRIPT", "/home/dave/run_trmnl_sonos.sh")
SONOS_REFRESH_COOLDOWN_SECONDS = int(os.getenv("TRMNL_SONOS_REFRESH_COOLDOWN_SECONDS", "3"))
SONOS_REFRESH_STATE_FILE = Path(os.getenv("TRMNL_SONOS_REFRESH_STATE_FILE", "/tmp/trmnl-sonos-refresh.json"))

# Fire hallway dashboard calendar endpoint.
# Why: HA rest sensor in packages/fire_calendar.yaml pulls multi-account calendar
# JSON from this GET endpoint. The script reuses nango_calendar_fetch helpers so
# behaviour matches the TRMNL Pi's calendar mix but extended to 7 accounts.
FIRE_CALENDAR_SCRIPT = os.getenv("FIRE_CALENDAR_SCRIPT", "/home/dave/trmnl-display-scripts/fire_calendar_fetch.py")
FIRE_CALENDAR_TIMEOUT = int(os.getenv("FIRE_CALENDAR_TIMEOUT", "60"))
# Why: the two HA REST sensors refresh together. Coalesce their requests so
# SpaceMail receives one CalDAV session rather than two competing sessions.
FIRE_CALENDAR_CACHE_SECONDS = int(os.getenv("FIRE_CALENDAR_CACHE_SECONDS", "15"))
FIRE_CALENDAR_FETCH_LOCK = threading.Lock()
FIRE_CALENDAR_CACHE: dict = {"stored_at": 0.0, "payload": None}

# Calendar watcher config
CALENDAR_REFRESH_SCRIPT = os.getenv("TRMNL_CALENDAR_REFRESH_SCRIPT", "/home/dave/bin/trmnl-refresh-calendar-sidecar")
CALENDAR_PAYLOAD_PATH = Path(os.getenv(
    "TRMNL_CALENDAR_PAYLOAD_PATH",
    "/home/dave/trmnl-display-scripts/tmp/nango_calendar_payload.json",
))
CALENDAR_WATCH_INTERVAL_SECONDS = int(os.getenv("TRMNL_CALENDAR_WATCH_INTERVAL_SECONDS", "60"))
CALENDAR_REFRESH_COOLDOWN_SECONDS = int(os.getenv("TRMNL_CALENDAR_REFRESH_COOLDOWN_SECONDS", "120"))
CALENDAR_REFRESH_STATE_FILE = Path(os.getenv(
    "TRMNL_CALENDAR_REFRESH_STATE_FILE",
    "/tmp/trmnl-calendar-sidecar-refresh.json",
))


# ---------------------------------------------------------------------------
# Calendar payload hash-diff watcher (background thread)
# ---------------------------------------------------------------------------

def _payload_hash(path: Path) -> str | None:
    """Return a stable hash of the calendar event data, or None if unreadable."""
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        # Hash only the event content, not metadata like 'today' timestamp
        events_blob = json.dumps(data.get("days", []), sort_keys=True)
        return hashlib.sha256(events_blob.encode()).hexdigest()
    except Exception:
        return None


def _last_calendar_refresh() -> float:
    try:
        with CALENDAR_REFRESH_STATE_FILE.open("r", encoding="utf-8") as f:
            return float(json.load(f).get("last_success", 0))
    except (OSError, ValueError, json.JSONDecodeError):
        return 0


def _record_calendar_refresh() -> None:
    CALENDAR_REFRESH_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with CALENDAR_REFRESH_STATE_FILE.open("w", encoding="utf-8") as f:
        json.dump({"last_success": time.time()}, f)


def _run_calendar_refresh(reason: str) -> bool:
    """Run the calendar sidecar refresh script. Returns True on success."""
    now = time.time()
    remaining = int(CALENDAR_REFRESH_COOLDOWN_SECONDS - (now - _last_calendar_refresh()))
    if remaining > 0:
        log.info("Calendar refresh skipped (cooldown %ds remaining, reason=%s)", remaining, reason)
        return False

    log.info("Triggering calendar sidecar refresh: %s", reason)
    result = subprocess.run(
        [CALENDAR_REFRESH_SCRIPT],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    if result.returncode == 0:
        _record_calendar_refresh()
        log.info("Calendar sidecar refresh completed OK")
        return True
    else:
        log.warning("Calendar sidecar refresh failed (rc=%d): %s", result.returncode, result.stderr.strip()[:200])
        return False


def _calendar_watcher() -> None:
    """
    Background thread: polls the nango calendar payload every CALENDAR_WATCH_INTERVAL_SECONDS.
    When the event hash changes, triggers an immediate sidecar re-render.
    """
    log.info(
        "Calendar watcher started (interval=%ds, payload=%s)",
        CALENDAR_WATCH_INTERVAL_SECONDS,
        CALENDAR_PAYLOAD_PATH,
    )
    last_hash: str | None = _payload_hash(CALENDAR_PAYLOAD_PATH)
    log.info("Calendar watcher initial hash: %s", last_hash)

    while True:
        time.sleep(CALENDAR_WATCH_INTERVAL_SECONDS)
        current_hash = _payload_hash(CALENDAR_PAYLOAD_PATH)
        if current_hash is None:
            log.debug("Calendar watcher: payload unreadable, skipping")
            continue
        if current_hash != last_hash:
            log.info(
                "Calendar watcher: payload changed (%s -> %s), triggering refresh",
                last_hash,
                current_hash,
            )
            if _run_calendar_refresh("payload-changed"):
                last_hash = current_hash
        else:
            log.debug("Calendar watcher: no change detected")


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------

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
        if self.path == "/health":
            self._send(HTTPStatus.OK, {"ok": True})
            return
        # Why: Fire dashboard pulls upcoming calendar JSON from this endpoint.
        parsed = urlparse(self.path)
        if parsed.path == "/calendar/upcoming":
            if not self._authorized():
                self._send(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
                return
            self._handle_calendar_upcoming(parsed)
            return
        self._send(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def _handle_calendar_upcoming(self, parsed) -> None:
        query = parse_qs(parsed.query)
        try:
            days = max(1, min(30, int(query.get("days", ["7"])[0])))
        except ValueError:
            days = 7
        log.info("Calendar upcoming request: days=%d", days)
        with FIRE_CALENDAR_FETCH_LOCK:
            cached = FIRE_CALENDAR_CACHE.get("payload")
            cache_age = time.time() - float(FIRE_CALENDAR_CACHE.get("stored_at", 0))
            if cached is not None and cache_age <= FIRE_CALENDAR_CACHE_SECONDS:
                payload = cached
            else:
                try:
                    # Why: one 30-day payload serves both HA sensors and avoids
                    # concurrent provider requests; each response is trimmed below.
                    result = subprocess.run(
                        ["python3", FIRE_CALENDAR_SCRIPT, "30"],
                        capture_output=True,
                        text=True,
                        check=False,
                        timeout=FIRE_CALENDAR_TIMEOUT,
                    )
                except subprocess.TimeoutExpired:
                    self._send(HTTPStatus.GATEWAY_TIMEOUT, {"error": "timeout", "timeout_s": FIRE_CALENDAR_TIMEOUT})
                    return
                if result.returncode != 0:
                    log.warning("Fire calendar fetch failed (rc=%d): %s", result.returncode, result.stderr.strip()[:200])
                    self._send(
                        HTTPStatus.BAD_GATEWAY,
                        {"error": "fetch_failed", "returncode": result.returncode, "stderr": result.stderr.strip()[:500]},
                    )
                    return
                try:
                    payload = json.loads(result.stdout)
                except json.JSONDecodeError as exc:
                    self._send(HTTPStatus.BAD_GATEWAY, {"error": "invalid_json", "detail": str(exc)})
                    return
                FIRE_CALENDAR_CACHE["payload"] = payload
                FIRE_CALENDAR_CACHE["stored_at"] = time.time()

        payload = dict(payload)
        try:
            start = date.fromisoformat(payload["today"])
            end = start + timedelta(days=days)
            payload["days"] = [
                item for item in payload.get("days", [])
                if start <= date.fromisoformat(item["date"]) < end
            ]
        except (KeyError, TypeError, ValueError):
            self._send(HTTPStatus.BAD_GATEWAY, {"error": "invalid_calendar_dates"})
            return
        body = json.dumps(payload).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

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

        if self.path == "/calendar/refresh":
            self._handle_calendar_refresh()
            return

        if self.path == "/sonos/refresh":
            self._handle_sonos_refresh()
            return

        if self.path == "/jen-morning/push":
            self._handle_jen_morning_push()
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

    def _handle_calendar_refresh(self) -> None:
        if not self._authorized():
            self._send(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
            return

        try:
            payload = self._read_json()
        except (ValueError, json.JSONDecodeError):
            self._send(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})
            return

        force = payload.get("force", False)

        now = time.time()
        remaining = int(CALENDAR_REFRESH_COOLDOWN_SECONDS - (now - _last_calendar_refresh()))
        if not force and remaining > 0:
            self._send(
                HTTPStatus.OK,
                {
                    "refresh": "skipped",
                    "reason": "cooldown",
                    "cooldown_seconds": CALENDAR_REFRESH_COOLDOWN_SECONDS,
                    "retry_after_seconds": remaining,
                },
            )
            return

        result = subprocess.run(
            [CALENDAR_REFRESH_SCRIPT],
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )

        if result.returncode == 0:
            _record_calendar_refresh()

        response = {
            "refresh": "completed" if result.returncode == 0 else "failed",
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
        status = HTTPStatus.OK if result.returncode == 0 else HTTPStatus.BAD_GATEWAY
        self._send(status, response)

    def _last_sonos_refresh(self) -> float:
        try:
            with SONOS_REFRESH_STATE_FILE.open("r", encoding="utf-8") as f:
                return float(json.load(f).get("last_success", 0))
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return 0

    def _record_sonos_refresh(self) -> None:
        SONOS_REFRESH_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with SONOS_REFRESH_STATE_FILE.open("w", encoding="utf-8") as f:
            json.dump({"last_success": time.time()}, f)

    def _handle_sonos_refresh(self) -> None:
        if not self._authorized():
            self._send(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
            return

        try:
            payload = self._read_json()
        except (ValueError, json.JSONDecodeError):
            payload = {}

        force = payload.get("force", False)

        now = time.time()
        remaining = int(SONOS_REFRESH_COOLDOWN_SECONDS - (now - self._last_sonos_refresh()))
        if not force and remaining > 0:
            log.info("Sonos refresh skipped (cooldown %ds remaining)", remaining)
            self._send(
                HTTPStatus.OK,
                {
                    "refresh": "skipped",
                    "reason": "cooldown",
                    "cooldown_seconds": SONOS_REFRESH_COOLDOWN_SECONDS,
                    "retry_after_seconds": remaining,
                },
            )
            return

        log.info("Triggering Sonos sidecar refresh")
        result = subprocess.run(
            [SONOS_REFRESH_SCRIPT],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )

        if result.returncode == 0:
            self._record_sonos_refresh()
            log.info("Sonos sidecar refresh completed OK")
        else:
            log.warning("Sonos sidecar refresh failed (rc=%d): %s", result.returncode, result.stderr.strip()[:200])

        response = {
            "refresh": "completed" if result.returncode == 0 else "failed",
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
        status = HTTPStatus.OK if result.returncode == 0 else HTTPStatus.BAD_GATEWAY
        self._send(status, response)

    def _handle_jen_morning_push(self) -> None:
        if not self._authorized():
            self._send(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
            return

        try:
            payload = self._read_json()
        except (ValueError, json.JSONDecodeError):
            self._send(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})
            return

        result = subprocess.run(
            [MORNING_PUSH_SCRIPT],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )

        response = {
            "push": "completed" if result.returncode == 0 else "failed",
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
        status = HTTPStatus.OK if result.returncode == 0 else HTTPStatus.BAD_GATEWAY
        self._send(status, response)

    def log_message(self, format: str, *args) -> None:
        return


if __name__ == "__main__":
    # Start the calendar watcher as a daemon thread
    watcher = threading.Thread(target=_calendar_watcher, daemon=True, name="calendar-watcher")
    watcher.start()

    log.info("TRMNL mode bridge listening on %s:%d", HOST, PORT)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
