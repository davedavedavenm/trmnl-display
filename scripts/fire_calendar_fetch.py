#!/usr/bin/env python3
"""
fire_calendar_fetch.py — extended calendar fetcher for the hallway panel.

Covers more calendars than the TRMNL sidecar's default slot set, reusing the
nango_calendar_fetch helpers (plus a CalDAV path for providers without a Nango
OAuth integration) so behaviour stays consistent with the TRMNL sidecar.

The calendar list is NOT hardcoded: it is loaded from the FIRE_CALENDARS_JSON
env var, or from the JSON file at FIRE_CALENDARS_FILE (default: fire_calendars.json
next to this script). Each entry has connection_id, provider
(google-calendar|outlook|caldav), calendar_id, color, and label. Nango
credentials come from NANGO_* env vars (loaded from the Nango env file); CalDAV
credentials/server from CALDAV_* env vars (loaded from the CalDAV env file).

Output: JSON on stdout consumable by the HA `rest` sensor in
packages/fire_calendar.yaml. Schema:
    {
        "days": [{date, day_name, calendars: [{name, label, color, events}]}],
        "today": "YYYY-MM-DD",
        "calendars": [{label, color, name}],
        "generated_at": "iso8601",
        "source": "fire_calendar_fetch.py",
        "health": "healthy|degraded|unavailable",
        "failed_sources": ["calendar label"]
    }
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nango_calendar_fetch as ncf  # noqa: E402

def _load_fire_calendars() -> list[dict]:
    raw = os.getenv("FIRE_CALENDARS_JSON", "").strip()
    if raw:
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            print(f"Warning: FIRE_CALENDARS_JSON invalid: {exc}", file=sys.stderr)
    path = Path(os.getenv("FIRE_CALENDARS_FILE", str(Path(__file__).resolve().parent / "fire_calendars.json")))
    if path.exists():
        try:
            with path.open(encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            print(f"Warning: failed to load {path}: {exc}", file=sys.stderr)
    return []


FIRE_CALENDARS = _load_fire_calendars()


def _load_nango_env() -> None:
    env_file = os.getenv("NANGO_ENV_FILE", "/home/dave/.env.nango")
    if not os.path.exists(env_file):
        return
    with open(env_file, encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            val = val.strip().strip('"').strip("'")
            os.environ.setdefault(key.strip(), val)


def _load_spacemail_env() -> None:
    env_file = os.getenv("SPACEMAIL_ENV_FILE", "/home/dave/.env.spacemail")
    if not os.path.exists(env_file):
        return
    with open(env_file, encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


def fetch_caldav_events(cal: dict, time_min: str, time_max: str) -> dict:
    """Fetch events from a CalDAV server (SpaceMail) in the same shape as the
    ncf fetchers. Recurring events are expanded client-side with
    recurring_ical_events because server-side expand support varies."""
    events = []
    error = None
    try:
        import caldav
        import recurring_ical_events
        from icalendar import Calendar as ICal

        url = os.getenv("CALDAV_SERVER_URL", "")
        user = os.getenv("CALDAV_USERNAME", "")
        pw = os.getenv("CALDAV_PASSWORD", "")
        start_dt = datetime.fromisoformat(time_min)
        end_dt = datetime.fromisoformat(time_max)

        # Why: SpaceMail is behind Cloudflare and occasionally closes a DAV
        # connection. A browser-like UA plus one immediate retry keeps a
        # transient close from becoming a false empty calendar.
        client_kwargs = {
            "url": url,
            "username": user,
            "password": pw,
            "timeout": 30,
            "headers": {"User-Agent": "TRMNL-Fire-Calendar/1.0"},
        }
        last_exc = None
        for attempt in range(4):
            try:
                attempt_events = []
                # Keep the client open through both discovery and REPORT/search;
                # Calendar objects retain the client's authenticated session.
                with caldav.DAVClient(**client_kwargs) as client:
                    dav_calendars = client.principal().calendars()
                    if not dav_calendars:
                        raise RuntimeError("CalDAV returned no calendar collections")
                    for dav_cal in dav_calendars:
                        found = dav_cal.search(start=start_dt, end=end_dt, event=True)
                        for obj in found:
                            try:
                                ical = ICal.from_ical(obj.data)
                            except Exception:
                                continue
                            for occ in recurring_ical_events.of(ical).between(start_dt, end_dt):
                                dtstart = occ.get("DTSTART")
                                dtend = occ.get("DTEND") or dtstart
                                sv, ev_ = dtstart.dt, dtend.dt
                                all_day = not isinstance(sv, datetime)
                                attempt_events.append({
                                    "summary": str(occ.get("SUMMARY", "(no title)")),
                                    "start": sv.isoformat(),
                                    "end": ev_.isoformat(),
                                    "all_day": all_day,
                                    "location": str(occ.get("LOCATION", "") or ""),
                                    "description": str(occ.get("DESCRIPTION", "") or ""),
                                    "status": str(occ.get("STATUS", "CONFIRMED")).lower(),
                                    "attendees": [],
                                })
                events = attempt_events
                last_exc = None
                break
            except Exception as exc:
                last_exc = exc
                if attempt < 3:
                    time.sleep(0.5 * (2 ** attempt))
        if last_exc is not None:
            raise last_exc
    except Exception as exc:
        error = {"type": type(exc).__name__}
        print(f"Warning: CalDAV fetch failed for {cal['connection_id']}: {error}", file=sys.stderr)

    # De-duplicate occurrences that appear via multiple DAV collections.
    seen = set()
    unique = []
    for ev2 in events:
        key = (ev2["summary"], ev2["start"], ev2["end"])
        if key not in seen:
            seen.add(key)
            unique.append(ev2)
    unique.sort(key=lambda x: x["start"])

    return ncf._source_result(cal, unique, error)


def fetch_fire_payload(days: int = 7) -> dict:
    _load_nango_env()
    _load_spacemail_env()
    ncf.NANGO_SECRET_KEY = os.getenv("NANGO_SECRET_KEY", "")
    ncf.NANGO_BASE_URL = os.getenv("NANGO_BASE_URL", "")

    now = datetime.now(timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=days)
    time_min = start.isoformat()
    time_max = end.isoformat()

    calendars = []
    for cal in FIRE_CALENDARS:
        if cal["provider"] == "google-calendar":
            calendars.append(ncf.fetch_google_events(cal, time_min, time_max))
        elif cal["provider"] == "outlook":
            calendars.append(ncf.fetch_outlook_events(cal, time_min, time_max))
        elif cal["provider"] == "caldav":
            calendars.append(fetch_caldav_events(cal, time_min, time_max))

    day_breakdown = ncf.group_events_by_day(calendars, start, days)
    provider_by_name = {
        item["connection_id"]: item["provider"] for item in FIRE_CALENDARS
    }
    sources = [
        {
            "name": cal["name"],
            "label": cal.get("label") or cal["name"],
            "provider": provider_by_name.get(cal["name"], "unknown"),
            "status": cal.get("status", "ok"),
            "error": cal.get("error"),
            "event_count": len(cal.get("events", [])),
        }
        for cal in calendars
    ]
    aggregate = ncf.aggregate_health(calendars)

    return {
        "days": day_breakdown,
        "today": now.strftime("%Y-%m-%d"),
        "calendars": [
            {"label": c["label"], "color": c["color"], "name": c["connection_id"]}
            for c in FIRE_CALENDARS
        ],
        "generated_at": now.isoformat(),
        "source": "fire_calendar_fetch.py",
        "health": aggregate["health"],
        "failed_sources": aggregate["failed_sources"],
        "sources": sources,
    }


if __name__ == "__main__":
    days_arg = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    # Why: ncf fetchers print per-calendar warnings to stdout; any such line
    # prepended to the JSON makes the bridge's json.loads fail ("invalid_json").
    # Redirect stdout to stderr during fetching so stdout carries pure JSON.
    import contextlib
    real_stdout = sys.stdout
    with contextlib.redirect_stdout(sys.stderr):
        payload = fetch_fire_payload(days=days_arg)
    json.dump(payload, real_stdout, indent=2, default=str)
    real_stdout.write("\n")
