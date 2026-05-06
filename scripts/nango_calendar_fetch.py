from __future__ import annotations

import json
import os
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

NANGO_BASE_URL = os.getenv("NANGO_BASE_URL", "https://nango.homelabmail.uk")
NANGO_SECRET_KEY = os.getenv("NANGO_SECRET_KEY", "")

CONNECTIONS = [
    {"connection_id": "google-calendar-davejenyt", "provider": "google-calendar", "label": "Dave", "color": [0, 0, 255]},
    {"connection_id": "outlook-davidmagnus", "provider": "outlook", "label": "Outlook", "color": [255, 0, 0]},
]
GOOGLE_CALENDAR_IDS = [
    ("davejenyt@gmail.com", "Dave", [0, 0, 255]),
    ("family06949947471094565362@group.calendar.google.com", "Family", [0, 255, 0]),
]


def nango_proxy_get(path: str, connection_id: str, provider: str) -> dict:
    url = f"{NANGO_BASE_URL}/proxy/{path}"
    headers = {
        "Authorization": f"Bearer {NANGO_SECRET_KEY}",
        "Connection-Id": connection_id,
        "Provider-Config-Key": provider,
    }
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.json()


def nango_get_token(connection_id: str, provider: str) -> str:
    url = f"{NANGO_BASE_URL}/connection/{connection_id}?provider_config_key={provider}"
    headers = {"Authorization": f"Bearer {NANGO_SECRET_KEY}"}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    return data.get("credentials", {}).get("access_token") or data["access_token"]


def fetch_outlook_events(connection_id: str, provider: str, time_min: str, time_max: str) -> list[dict]:
    token = nango_get_token(connection_id, provider)
    params = urllib.parse.urlencode({
        "startDateTime": time_min,
        "endDateTime": time_max,
        "$select": "subject,start,end,location",
    })
    url = f"https://graph.microsoft.com/v1.0/me/calendarview?{params}"
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    events = []
    for item in data.get("value", []):
        events.append({
            "summary": item.get("subject", "(no title)"),
            "start": item.get("start", {}).get("dateTime", ""),
            "end": item.get("end", {}).get("dateTime", ""),
            "all_day": False,
            "location": (item.get("location") or {}).get("displayName", ""),
        })
    return events


def fetch_payload() -> dict:
    now = datetime.now(timezone.utc)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)
    time_min = day_start.isoformat()
    time_max = day_end.isoformat()

    calendars_out = []

    for cal_id, label, color in GOOGLE_CALENDAR_IDS:
        conn = CONNECTIONS[0]
        params = urllib.parse.urlencode({
            "timeMin": time_min,
            "timeMax": time_max,
            "singleEvents": "true",
            "orderBy": "startTime",
        })
        encoded_cal_id = urllib.parse.quote(cal_id, safe="")
        path = f"calendar/v3/calendars/{encoded_cal_id}/events?{params}"

        events = []
        try:
            result = nango_proxy_get(path, conn["connection_id"], conn["provider"])
            for item in result.get("items", []):
                start_raw = item.get("start", {})
                end_raw = item.get("end", {})
                is_all_day = "date" in start_raw and "dateTime" not in start_raw
                events.append({
                    "summary": item.get("summary", "(no title)"),
                    "start": start_raw.get("dateTime", start_raw.get("date", "")),
                    "end": end_raw.get("dateTime", end_raw.get("date", "")),
                    "all_day": is_all_day,
                    "location": item.get("location", ""),
                })
        except requests.RequestException as e:
            print(f"Warning: failed to fetch {label}: {e}")

        calendars_out.append({"name": label, "color": color, "events": events})

    outlook_conn = CONNECTIONS[1]
    try:
        outlook_events = fetch_outlook_events(outlook_conn["connection_id"], outlook_conn["provider"], time_min, time_max)
        calendars_out.append({"name": outlook_conn["label"], "color": outlook_conn["color"], "events": outlook_events})
    except requests.RequestException as e:
        print(f"Warning: failed to fetch Outlook: {e}")

    return {
        "date": day_start.strftime("%Y-%m-%d"),
        "day_name": day_start.strftime("%A"),
        "calendars": calendars_out,
    }


def main():
    payload = fetch_payload()
    out_path = Path(__file__).resolve().parent / "tmp" / "nango_calendar_payload.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=str)
    print(f"Wrote payload to {out_path}")
    for c in payload["calendars"]:
        print(f"  {c['name']}: {len(c['events'])} events")


if __name__ == "__main__":
    main()
