from dotenv import load_dotenv
import datetime
import locale
import os
from typing import Dict, List

import icalendar
import pytz
import recurring_ical_events
import requests

load_dotenv()

PALETTE = ["black", "red", "blue", "green", "yellow", "orange"]
CATEGORY_COLOR_MAP = {
    "work": "blue",
    "family": "green",
    "personal": "red",
    "travel": "orange",
    "holiday": "yellow",
    "vacation": "yellow",
    "birthday": "red",
    "health": "green",
    "school": "blue",
    "finance": "black",
}


def env_bool(key: str, default: bool) -> bool:
    return os.getenv(key, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def env_int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, str(default)).strip())
    except ValueError:
        return default


DEBUG = env_bool("DEBUG", False)
TRMNL_TITLE = os.getenv("TRMNL_TITLE", "Calendar").strip() or "Calendar"
TRMNL_WEBHOOK_URL = os.getenv("TRMNL_WEBHOOK_URL", "").strip()
TRMNL_TZ = os.getenv("TRMNL_TZ", "Europe/London").strip() or "Europe/London"
TRMNL_DAYS = env_int("TRMNL_DAYS", 7)
TRMNL_DATE_FORMAT = os.getenv("TRMNL_DATE_FORMAT", "%d %b (%a)")
TRMNL_TIME_FORMAT = os.getenv("TRMNL_TIME_FORMAT", "%H:%M")
TRMNL_UPDATED_AT_FORMAT = os.getenv("TRMNL_UPDATED_AT_FORMAT", "%d %b %H:%M")
TRMNL_LOCALE = os.getenv("TRMNL_LOCALE")
TRMNL_NUMBER_COLUMNS = env_int("TRMNL_NUMBER_COLUMNS", 4)
TRMNL_SHOW_SOURCE_LABELS = env_bool("TRMNL_SHOW_SOURCE_LABELS", True)
TRMNL_SHOW_ALL_DAY = env_bool("TRMNL_SHOW_ALL_DAY_EVENTS", True)
TRMNL_HIDE_EMPTY_DAYS = env_bool("TRMNL_HIDE_EMPTY_DAYS", True)
TRMNL_MAX_EVENTS_PER_DAY = env_int("TRMNL_MAX_EVENTS_PER_DAY", 6)
TRMNL_TIME_FORMAT_MODE = os.getenv("TRMNL_TIME_MODE", "24h").strip().lower() or "24h"

if TRMNL_LOCALE:
    locale.setlocale(locale.LC_ALL, TRMNL_LOCALE)

NOW = datetime.datetime.now(pytz.timezone(TRMNL_TZ))
START_DATE = NOW.date()


def normalize_dt(value):
    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        if value.tzinfo is None:
            return pytz.timezone(TRMNL_TZ).localize(value)
        return value.astimezone(pytz.timezone(TRMNL_TZ))
    if isinstance(value, datetime.date):
        return value
    return None


def normalize_color(value: str, fallback: str) -> str:
    if not value:
        return fallback
    color = value.strip().lower()
    if color in PALETTE:
        return color
    if color.startswith("#"):
        return color
    return fallback


def extract_categories(event) -> List[str]:
    raw = event.get("CATEGORIES")
    if raw is None:
        return []

    if isinstance(raw, list):
        values = raw
    elif hasattr(raw, "cats"):
        values = list(raw.cats)
    else:
        values = [raw]

    categories = []
    for value in values:
        text = str(value).strip()
        if not text:
            continue
        for item in text.split(","):
            item = item.strip()
            if item:
                categories.append(item)
    return categories


def event_color_for(event, source_color: str) -> str:
    color_fields = [
        event.get("COLOR"),
        event.get("X-APPLE-CALENDAR-COLOR"),
        event.get("X-COLOR"),
    ]
    for field in color_fields:
        if field:
            resolved = normalize_color(str(field), source_color)
            if resolved != source_color or str(field).strip().lower() == source_color:
                return resolved

    categories = extract_categories(event)
    for category in categories:
        mapped = CATEGORY_COLOR_MAP.get(category.strip().lower())
        if mapped:
            return mapped

    return source_color


def build_calendar_sources() -> List[Dict[str, object]]:
    sources: List[Dict[str, object]] = []

    for idx in range(1, 7):
        enabled = env_bool(f"TRMNL_CAL{idx}_ENABLED", False)
        url = os.getenv(f"TRMNL_CAL{idx}_URL", "").strip()
        label = os.getenv(f"TRMNL_CAL{idx}_LABEL", f"Calendar {idx}").strip() or f"Calendar {idx}"
        color = os.getenv(f"TRMNL_CAL{idx}_COLOR", PALETTE[(idx - 1) % len(PALETTE)]).strip().lower()
        custom_color = os.getenv(f"TRMNL_CAL{idx}_COLOR_CUSTOM", "").strip()
        headers_raw = os.getenv(f"TRMNL_CAL{idx}_HEADERS", "").strip()

        if not enabled or not url:
            continue

        header_map = {}
        if headers_raw:
            for pair in headers_raw.split("&"):
                if "=" in pair:
                    key, value = pair.split("=", 1)
                    header_map[key.strip()] = value.strip()

        sources.append(
            {
                "url": url,
                "label": label,
                "color": custom_color or (color if color in PALETTE else "black"),
                "headers": header_map,
            }
        )

    if sources:
        return sources

    legacy_urls = [item.strip() for item in os.getenv("TRMNL_ICS_URL", "").split(",") if item.strip()]
    legacy_labels = [item.strip() for item in os.getenv("TRMNL_ICS_LABELS", "").split(",") if item.strip()]
    legacy_colors = [item.strip() for item in os.getenv("TRMNL_ICS_COLORS", "blue,red,orange,green,yellow,black").split(",") if item.strip()]

    for idx, url in enumerate(legacy_urls, start=1):
        sources.append(
            {
                "url": url,
                "label": legacy_labels[idx - 1] if idx - 1 < len(legacy_labels) else f"Calendar {idx}",
                "color": legacy_colors[(idx - 1) % len(legacy_colors)] if legacy_colors else "black",
                "headers": {},
            }
        )

    return sources


def fetch_source(source: Dict[str, object]) -> List[Dict[str, object]]:
    response = requests.get(source["url"], headers=source["headers"], timeout=20)
    response.raise_for_status()

    calendar = icalendar.Calendar.from_ical(response.text)
    query = recurring_ical_events.of(calendar)
    results: List[Dict[str, object]] = []

    for offset in range(TRMNL_DAYS):
        date_value = START_DATE + datetime.timedelta(days=offset)
        day_events = query.at(date_value)
        if not day_events and TRMNL_HIDE_EMPTY_DAYS:
            continue

        items = []

        def sort_key(event):
            start_dt = normalize_dt(event.get("DTSTART").dt if event.get("DTSTART") else None)
            if isinstance(start_dt, datetime.datetime):
                return start_dt.strftime("%H:%M")
            return "00:00"

        day_events.sort(key=sort_key)

        for event in day_events:
            summary = str(event.get("SUMMARY", "No Title"))
            start_raw = normalize_dt(event.get("DTSTART").dt if event.get("DTSTART") else None)
            end_raw = normalize_dt(event.get("DTEND").dt if event.get("DTEND") else None)
            all_day = isinstance(start_raw, datetime.date) and not isinstance(start_raw, datetime.datetime)
            categories = extract_categories(event)
            resolved_color = event_color_for(event, source["color"])

            if all_day and not TRMNL_SHOW_ALL_DAY:
                continue

            item = {
                "summary": summary,
                "source_label": source["label"],
                "source_color": resolved_color,
                "calendar_color": source["color"],
                "calname": source["label"],
                "all_day": all_day,
                "categories": categories,
            }

            if all_day:
                item["start_full"] = start_raw.strftime("%Y-%m-%d") if start_raw else ""
                item["end_full"] = end_raw.strftime("%Y-%m-%d") if end_raw else ""
                item["date_time"] = item["start_full"]
            else:
                item["start"] = start_raw.strftime(TRMNL_TIME_FORMAT) if start_raw else "00:00"
                item["end"] = end_raw.strftime(TRMNL_TIME_FORMAT) if end_raw else "23:59"
                item["start_full"] = start_raw.isoformat() if start_raw else ""
                item["end_full"] = end_raw.isoformat() if end_raw else ""
                item["date_time"] = item["start_full"]

            items.append(item)

        visible_items = items[:TRMNL_MAX_EVENTS_PER_DAY]
        hidden_count = max(len(items) - len(visible_items), 0)

        if visible_items or not TRMNL_HIDE_EMPTY_DAYS:
            results.append({
                "date": date_value.strftime(TRMNL_DATE_FORMAT),
                "date_key": date_value.isoformat(),
                "events": visible_items,
                "total_events": len(items),
                "hidden_events": hidden_count,
            })

    if DEBUG:
        print(f"Fetched {source['label']} from {source['url']}")

    return results


def merge_days(source_results: List[List[Dict[str, object]]]) -> List[Dict[str, object]]:
    merged: Dict[str, Dict[str, object]] = {}
    for result in source_results:
        for day in result:
            key = day["date_key"]
            if key not in merged:
                merged[key] = {"date": day["date"], "date_key": key, "events": []}
            merged[key]["events"].extend(day["events"])

    ordered = []
    for key in sorted(merged.keys()):
        day = merged[key]
        day["events"].sort(key=lambda item: item.get("start", "00:00"))
        total_events = len(day["events"])
        day["events"] = day["events"][:TRMNL_MAX_EVENTS_PER_DAY]
        day["total_events"] = total_events
        day["hidden_events"] = max(total_events - len(day["events"]), 0)
        if day["events"] or not TRMNL_HIDE_EMPTY_DAYS:
            ordered.append(day)
    return ordered


def flatten_events(days: List[Dict[str, object]]) -> List[Dict[str, object]]:
    flat: List[Dict[str, object]] = []
    for day in days:
        flat.extend(day["events"])
    flat.sort(key=lambda item: item.get("date_time", ""))
    return flat


def main() -> None:
    if not TRMNL_WEBHOOK_URL:
        raise RuntimeError("TRMNL_WEBHOOK_URL is required")

    sources = build_calendar_sources()
    if not sources:
        raise RuntimeError("No enabled calendar sources configured")

    merged_days = merge_days([fetch_source(source) for source in sources])
    flat_events = flatten_events(merged_days)

    payload = {
        "merge_variables": {
            "updated_at": NOW.strftime(TRMNL_UPDATED_AT_FORMAT),
            "title": TRMNL_TITLE,
            "calendar": merged_days,
            "columns": TRMNL_NUMBER_COLUMNS,
            "show_source_labels": TRMNL_SHOW_SOURCE_LABELS,
            "events": flat_events,
            "time_format": TRMNL_TIME_FORMAT_MODE,
            "today_in_tz": NOW.isoformat(),
            "source_count": len(sources),
        }
    }

    response = requests.post(TRMNL_WEBHOOK_URL, json=payload, timeout=20)
    if DEBUG or response.status_code != 200:
        print(f"Status: {response.status_code}")
        print(response.text)


if __name__ == "__main__":
    main()
