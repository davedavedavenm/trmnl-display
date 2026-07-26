"""Regression tests for calendar-source health propagation."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

SPEC = importlib.util.spec_from_file_location("fire_calendar_fetch", SCRIPTS / "fire_calendar_fetch.py")
fire = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(fire)


def result(cal: dict, status: str) -> dict:
    error = {"type": "SyntheticFailure"} if status == "error" else None
    return fire.ncf._source_result(cal, [], error)


class FireCalendarHealthTests(unittest.TestCase):
    def setUp(self) -> None:
        self.google = {
            "connection_id": "google-test",
            "provider": "google-calendar",
            "calendar_id": "primary",
            "label": "Google Test",
            "color": [1, 2, 3],
        }
        self.outlook = {
            "connection_id": "outlook-test",
            "provider": "outlook",
            "calendar_id": None,
            "label": "Outlook Test",
            "color": [4, 5, 6],
        }

    def fetch(self, google_status: str, outlook_status: str) -> dict:
        with (
            patch.object(fire, "FIRE_CALENDARS", [self.google, self.outlook]),
            patch.object(fire, "_load_nango_env"),
            patch.object(fire, "_load_spacemail_env"),
            patch.object(
                fire.ncf,
                "fetch_google_events",
                side_effect=lambda cal, *_: result(cal, google_status),
            ),
            patch.object(
                fire.ncf,
                "fetch_outlook_events",
                side_effect=lambda cal, *_: result(cal, outlook_status),
            ),
        ):
            return fire.fetch_fire_payload(days=7)

    def test_all_sources_healthy(self) -> None:
        payload = self.fetch("ok", "ok")
        self.assertEqual(payload["health"], "healthy")
        self.assertEqual(payload["failed_sources"], [])

    def test_partial_failure_is_degraded(self) -> None:
        payload = self.fetch("ok", "error")
        self.assertEqual(payload["health"], "degraded")
        self.assertEqual(payload["failed_sources"], ["Outlook Test"])

    def test_total_failure_is_unavailable(self) -> None:
        payload = self.fetch("error", "error")
        self.assertEqual(payload["health"], "unavailable")
        self.assertEqual(payload["failed_sources"], ["Google Test", "Outlook Test"])

    def test_source_diagnostics_do_not_contain_request_details(self) -> None:
        import requests

        with patch.object(
            fire.ncf,
            "nango_proxy_get",
            side_effect=requests.ConnectionError("https://secret.example/path?token=leak"),
        ):
            source = fire.ncf.fetch_google_events(
                self.google,
                "2026-07-26T00:00:00+00:00",
                "2026-08-02T00:00:00+00:00",
            )
        self.assertEqual(source["status"], "error")
        self.assertEqual(source["error"], {"type": "ConnectionError", "http_status": None})
        self.assertNotIn("secret.example", str(source))


if __name__ == "__main__":
    unittest.main()
