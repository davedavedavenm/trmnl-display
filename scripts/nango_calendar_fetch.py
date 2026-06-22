from __future__ import annotations

import json
import os
import subprocess
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

NANGO_BASE_URL = os.getenv("NANGO_BASE_URL", "https://nango.example.com")
NANGO_SECRET_KEY = os.getenv("NANGO_SECRET_KEY", "")

PRIMARY_CALENDARS = [
    {"connection_id": "REDACTED-CONNECTION", "provider": "google-calendar", "calendar_id": "REDACTED@example.com", "color": [0, 0, 255], "label": "REDACTED-LABEL"},
    {"connection_id": "REDACTED-CONNECTION", "provider": "google-calendar", "calendar_id": "REDACTED@example.com", "color": [0, 255, 0], "label": "DAVE"},
    {"connection_id": "REDACTED-CONNECTION", "provider": "google-calendar", "calendar_id": "REDACTED@example.com", "color": [255, 0, 0], "label": "JEN"},
    {"connection_id": "REDACTED-CONNECTION", "provider": "outlook", "calendar_id": None, "color": [255, 128, 0], "label": "OUTLOOK"},
]

PALETTE_MAP = {
    "blue": [0, 0, 255],
    "green": [0, 255, 0],
    "red": [255, 0, 0],
    "orange": [255, 128, 0],
    "yellow": [255, 255, 0],
    "black": [0, 0, 0],
}


def load_plugin_config() -> dict:
    plugin_id = os.getenv("TRMNL_PLUGIN_ID", "27")
    container = os.getenv("TRMNL_LARAPAPER_CONTAINER", "larapaper-app-1")
    php = (
        "require '/var/www/html/vendor/autoload.php';"
        "$app = require '/var/www/html/bootstrap/app.php';"
        "$app->make(Illuminate\\Contracts\\Console\\Kernel::class)->bootstrap();"
        f"echo DB::table('plugins')->where('id', {plugin_id})->value('configuration') ?: '{{}}';"
    )
    try:
        result = subprocess.run(
            ["docker", "exec", container, "php", "-r", php],
            capture_output=True,
            text=True,
            timeout=15,
            check=True,
        )
        stdout = (result.stdout or "").strip()
        if stdout:
            return json.loads(stdout)
    except Exception as e:
        print(f"Warning: failed to load LaraPaper config: {e}")
    return {}


def get_provider(connection_id: str) -> str:
    if "outlook" in connection_id or connection_id in ["REDACTED-UUID", "REDACTED-UUID"]:
        return "outlook"
    return "google-calendar"


def parse_color(color_name: str, custom_hex: str) -> list[int]:
    if custom_hex:
        custom_hex = custom_hex.lstrip("#")
        if len(custom_hex) == 6:
            try:
                return [int(custom_hex[i:i+2], 16) for i in (0, 2, 4)]
            except ValueError:
                pass
    return PALETTE_MAP.get(color_name.lower(), [0, 0, 255])


def get_calendars_from_config(config: dict) -> list[dict]:
    calendars = []
    for idx in range(1, 13):
        connection_id = config.get(f"calendar_{idx}_connection_id", "").strip()
        if not connection_id:
            continue

        calendar_id = config.get(f"calendar_{idx}_calendar_id", "").strip() or None
        label = config.get(f"calendar_{idx}_label", "").strip() or None
        color_name = config.get(f"calendar_{idx}_color", "blue").strip()
        color_custom = config.get(f"calendar_{idx}_color_custom", "").strip()

        provider = get_provider(connection_id)
        color = parse_color(color_name, color_custom)

        calendars.append({
            "connection_id": connection_id,
            "provider": provider,
            "calendar_id": calendar_id,
            "color": color,
            "label": label
        })
    return calendars


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


def fetch_google_events(cal: dict, time_min: str, time_max: str) -> dict:
    calendar_id = cal.get("calendar_id") or "primary"
    params = urllib.parse.urlencode({
        "timeMin": time_min,
        "timeMax": time_max,
        "singleEvents": "true",
        "orderBy": "startTime",
    })
    path = f"calendar/v3/calendars/{urllib.parse.quote(calendar_id, safe='')}/events?{params}"
    events = []
    try:
        result = nango_proxy_get(path, cal["connection_id"], cal["provider"])
        for item in result.get("items", []):
            start_raw = item.get("start", {})
            end_raw = item.get("end", {})
            attendees = []
            for a in item.get("attendees", []) or []:
                attendees.append({
                    "email": a.get("email", ""),
                    "name": a.get("displayName", ""),
                    "status": a.get("responseStatus", "needsAction"),
                })

            events.append({
                "summary": item.get("summary", "(no title)"),
                "start": start_raw.get("dateTime", start_raw.get("date", "")),
                "end": end_raw.get("dateTime", end_raw.get("date", "")),
                "all_day": "date" in start_raw and "dateTime" not in start_raw,
                "location": item.get("location", ""),
                "description": item.get("description", ""),
                "status": item.get("status", "confirmed"),
                "attendees": attendees,
            })
    except requests.RequestException as e:
        print(f"Warning: {cal['connection_id']}: {e}")
    return {"name": cal["connection_id"], "label": cal.get("label"), "color": cal["color"], "events": events}


def fetch_outlook_events(cal: dict, time_min: str, time_max: str) -> dict:
    try:
        token = nango_get_token(cal["connection_id"], cal["provider"])
        params = urllib.parse.urlencode({
            "startDateTime": time_min,
            "endDateTime": time_max,
            "$select": "subject,start,end,location",
        })
        calendar_id = cal.get("calendar_id")
        outlook_path = f"me/calendars/{urllib.parse.quote(calendar_id)}/calendarview" if calendar_id else "me/calendarview"
        url = f"https://graph.microsoft.com/v1.0/{outlook_path}?{params}"
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
        return {"name": cal["connection_id"], "label": cal.get("label"), "color": cal["color"], "events": events}
    except requests.RequestException as e:
        print(f"Warning: {cal['connection_id']}: {e}")
        return {"name": cal["connection_id"], "label": cal.get("label"), "color": cal["color"], "events": []}


def group_events_by_day(calendars: list[dict], start: datetime, days: int) -> list[dict]:
    day_map: dict[str, dict] = {}
    for i in range(days):
        d = start + timedelta(days=i)
        key = d.strftime("%Y-%m-%d")
        day_map[key] = {
            "date": key,
            "day_name": d.strftime("%A"),
            "calendars": {
                c["name"]: {
                    "name": c["name"],
                    "label": c.get("label"),
                    "color": c["color"],
                    "events": []
                } for c in calendars
            }
        }

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
    config = load_plugin_config()

    global NANGO_SECRET_KEY, NANGO_BASE_URL
    if not NANGO_SECRET_KEY:
        NANGO_SECRET_KEY = config.get("nango_secret_key", "")
    NANGO_BASE_URL = config.get("nango_base_url", NANGO_BASE_URL)

    theme = config.get("theme") or os.getenv("TRMNL_CALENDAR_THEME") or "dark"
    layout = config.get("layout") or os.getenv("TRMNL_CALENDAR_LAYOUT") or "featured"

    active_calendars = get_calendars_from_config(config)
    if not active_calendars:
        print("No active calendars configured in LaraPaper DB, falling back to default primary calendars")
        active_calendars = PRIMARY_CALENDARS

    now = datetime.now(timezone.utc)
    week_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = week_start + timedelta(days=7)
    time_min = week_start.isoformat()
    time_max = week_end.isoformat()

    calendars = []
    for cal in active_calendars:
        if cal["provider"] == "google-calendar":
            calendars.append(fetch_google_events(cal, time_min, time_max))
        elif cal["provider"] == "outlook":
            calendars.append(fetch_outlook_events(cal, time_min, time_max))

    days = group_events_by_day(calendars, week_start, 7)

    return {
        "days": days,
        "today": now.strftime("%Y-%m-%d"),
        "theme": theme,
        "layout": layout,
    }


def update_ha_weekend_events(payload: dict):
    from dotenv import load_dotenv
    load_dotenv("/home/dave/.env")
    ha_url = os.getenv("HA_URL", "http://192.168.1.89:8123").strip()
    ha_token = os.getenv("HA_TOKEN", "").strip()
    if not ha_token:
        print("HA_TOKEN not found in environment, skipping HA state update.")
        return

    today_str = payload.get("today", "")
    try:
        ref_date = datetime.strptime(today_str, "%Y-%m-%d").date()
    except Exception:
        ref_date = datetime.now().date()
    wd = ref_date.weekday()

    # Decide if we include Monday in our check:
    # Monday is included if today is Sunday after 12:00 PM (local time), or today is Monday
    now_local = datetime.now()
    include_monday = False
    if wd == 6:  # Sunday
        if now_local.hour >= 12:
            include_monday = True
    elif wd == 0:  # Monday
        include_monday = True

    # Calculate target dates for the current weekend (Sat/Sun) and Monday (if included)
    if wd == 6:  # Sunday
        target_dates = [
            ref_date - timedelta(days=1),  # Saturday
            ref_date,                     # Sunday
        ]
        if include_monday:
            target_dates.append(ref_date + timedelta(days=1))  # Monday
    elif wd == 5:  # Saturday
        target_dates = [
            ref_date,                     # Saturday
            ref_date + timedelta(days=1),  # Sunday
        ]
        if include_monday:
            target_dates.append(ref_date + timedelta(days=2))  # Monday
    else:  # Monday - Friday
        days_to_sat = 5 - wd
        saturday = ref_date + timedelta(days=days_to_sat)
        target_dates = [
            saturday,
            saturday + timedelta(days=1),
        ]
        if include_monday:
            target_dates.append(saturday + timedelta(days=2))  # Monday

    target_strs = {d.strftime("%Y-%m-%d") for d in target_dates}
    print(f"Checking weekend/Monday calendar events (include_monday={include_monday}) for: {sorted(target_strs)}")

    has_events = False
    for day in payload.get("days", []):
        if day.get("date") in target_strs:
            for cal in day.get("calendars", []):
                if cal.get("events"):
                    has_events = True
                    break
        if has_events:
            break

    state = "on" if has_events else "off"
    print(f"Determined weekend/Monday calendar events state: {state.upper()}")

    # Push state to Home Assistant
    url = f"{ha_url}/api/states/input_boolean.trmnl_weekend_has_calendar_events"
    headers = {
        "Authorization": f"Bearer {ha_token}",
        "Content-Type": "application/json"
    }
    data = {
        "state": state,
        "attributes": {
            "friendly_name": "TRMNL Weekend Has Calendar Events",
            "icon": "mdi:calendar-check" if has_events else "mdi:calendar-blank",
            "checked_at": datetime.now().isoformat()
        }
    }
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        if response.status_code in [200, 201]:
            print(f"Successfully updated input_boolean.trmnl_weekend_has_calendar_events to {state.upper()} in Home Assistant.")
        else:
            print(f"Failed to update HA state. HTTP {response.status_code}: {response.text}")
    except Exception as e:
        print(f"Error updating HA state: {e}")


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
    
    # Update HA with weekend/Monday events status
    update_ha_weekend_events(payload)


if __name__ == "__main__":
    main()

