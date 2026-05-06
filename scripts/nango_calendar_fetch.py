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


def fetch_google_events(cal_id: str, label: str, color: list, time_min: str, time_max: str) -> dict:
    conn = CONNECTIONS[0]
    params = urllib.parse.urlencode({
        "timeMin": time_min,
        "timeMax": time_max,
        "singleEvents": "true",
        "orderBy": "startTime",
    })
    path = f"calendar/v3/calendars/{urllib.parse.quote(cal_id, safe='')}/events?{params}"
    events = []
    try:
        result = nango_proxy_get(path, conn["connection_id"], conn["provider"])
        for item in result.get("items", []):
            start_raw = item.get("start", {})
            end_raw = item.get("end", {})
            events.append({
                "summary": item.get("summary", "(no title)"),
                "start": start_raw.get("dateTime", start_raw.get("date", "")),
                "end": end_raw.get("dateTime", end_raw.get("date", "")),
                "all_day": "date" in start_raw and "dateTime" not in start_raw,
                "location": item.get("location", ""),
            })
    except requests.RequestException as e:
        print(f"Warning: {label}: {e}")
    return {"name": label, "color": color, "events": events}


def fetch_outlook_events(connection_id: str, provider: str, time_min: str, time_max: str) -> dict:
    try:
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
        return {"name": "Outlook", "color": [255, 0, 0], "events": events}
    except requests.RequestException as e:
        print(f"Warning: Outlook: {e}")
        return {"name": "Outlook", "color": [255, 0, 0], "events": []}


def group_events_by_day(calendars: list[dict], start: datetime, days: int) -> list[dict]:
    day_map: dict[str, dict] = {}
    for i in range(days):
        d = start + timedelta(days=i)
        key = d.strftime("%Y-%m-%d")
        day_map[key] = {"date": key, "day_name": d.strftime("%A"), "calendars": {c["name"]: {"name": c["name"], "color": c["color"], "events": []} for c in calendars}}

    for cal in calendars:
        for ev in cal["events"]:
            start_str = ev.get("start", "")
            try:
                if ev["all_day"]:
                    ev_date = datetime.strptime(start_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                else:
                    ev_date = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                key = ev_date.strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                key = start_str[:10] if start_str else ""

            if key in day_map:
                day_map[key]["calendars"][cal["name"]]["events"].append(ev)

    result = []
    for key in sorted(day_map.keys()):
        day = day_map[key]
        active_cals = [c for c in day["calendars"].values() if c["events"]]
        if active_cals:
            result.append({"date": day["date"], "day_name": day["day_name"], "calendars": active_cals})
    return result


def fetch_payload() -> dict:
    now = datetime.now(timezone.utc)
    week_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = week_start + timedelta(days=7)
    time_min = week_start.isoformat()
    time_max = week_end.isoformat()

    calendars = []
    for cal_id, label, color in GOOGLE_CALENDAR_IDS:
        calendars.append(fetch_google_events(cal_id, label, color, time_min, time_max))

    calendars.append(fetch_outlook_events(CONNECTIONS[1]["connection_id"], CONNECTIONS[1]["provider"], time_min, time_max))

    days = group_events_by_day(calendars, week_start, 7)

    return {"days": days, "today": now.strftime("%Y-%m-%d")}


def main():
    payload = fetch_payload()
    out_path = Path(__file__).resolve().parent / "tmp" / "nango_calendar_payload.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=str)
    total_events = sum(len(c["events"]) for day in payload["days"] for c in day["calendars"])
    print(f"Wrote payload: {len(payload['days'])} days with events, {total_events} total events")
    for day in payload["days"]:
        for c in day["calendars"]:
            for e in c["events"]:
                print(f"  {day['date']} {c['name']}: {e['summary']}")


if __name__ == "__main__":
    main()
