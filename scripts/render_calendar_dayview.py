#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = Path(__file__).resolve().parent / "tmp"
OUT_PATH = OUT_DIR / "sidecar_calendar_day_next.png"
SOURCE_PATH = OUT_DIR / "sidecar_calendar_day_source_next.png"
WIDTH = 800
HEIGHT = 480

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
ORANGE = (255, 128, 0)

PANEL_PALETTE = [BLACK, WHITE, RED, YELLOW, BLUE, GREEN, ORANGE]

CALENDAR_COLORS = [
    ("Dave", BLUE),
    ("Family", GREEN),
    ("Outlook", RED),
    ("Birthdays", YELLOW),
    ("Holidays", ORANGE),
]

NOON = (160, 160, 160)
DARK_BG = (35, 35, 35)
CARD_BG = (50, 50, 50)
ACCENT_GREY = (70, 70, 70)
DIM = (140, 140, 140)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for c in candidates:
        try:
            return ImageFont.truetype(c, size)
        except OSError:
            pass
    return ImageFont.load_default()


def parse_iso(t: str) -> datetime:
    if t.endswith("Z"):
        t = t[:-1] + "+00:00"
    return datetime.fromisoformat(t)


def draw_rounded(draw: ImageDraw, x1: int, y1: int, x2: int, y2: int, fill: tuple, radius: int = 6):
    draw.rounded_rectangle([x1, y1, x2, y2], radius=radius, fill=fill)


def render(payload: dict) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT), WHITE)
    draw = ImageDraw.Draw(img)

    font_title = font(28, bold=True)
    font_date = font(18)
    font_event_time = font(20, bold=True)
    font_event_title = font(20)
    font_event_loc = font(15)
    font_empty = font(24, bold=True)
    font_key = font(13)

    day_str = payload.get("date", "")
    day_name = payload.get("day_name", "")
    calendars = payload.get("calendars", [])

    try:
        dt = datetime.strptime(day_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        display_date = dt.strftime("%-d %B %Y")
    except (ValueError, TypeError):
        display_date = day_str
        dt = datetime.now(timezone.utc)

    # Header
    HEADER_H = 50
    draw.rectangle([(0, 0), (WIDTH, HEADER_H)], fill=BLACK)
    draw.text((20, HEADER_H // 2), f"{day_name}", fill=WHITE, font=font_title, anchor="lm")
    draw.text((WIDTH - 20, HEADER_H // 2), display_date, fill=WHITE, font=font_date, anchor="rm")

    # Collect + sort events
    all_events = []
    for cal in calendars:
        cal_name = cal.get("name", "?")
        cal_color = tuple(cal.get("color", [128, 128, 128]))
        for ev in cal.get("events", []):
            start_s = ev.get("start", "")
            end_s = ev.get("end", "")
            all_day = ev.get("all_day", False)
            start_dt = parse_iso(start_s) if start_s and not all_day else None
            end_dt = parse_iso(end_s) if end_s and not all_day else None
            all_events.append({
                "summary": ev.get("summary", ""),
                "start": start_dt,
                "end": end_dt,
                "all_day": all_day,
                "location": ev.get("location", ""),
                "calendar": cal_name,
                "color": cal_color,
            })

    if not all_events:
        mid = (WIDTH // 2, HEIGHT // 2 - 10)
        draw.text(mid, "No events today", fill=BLACK, font=font_empty, anchor="mm")
        draw.text((WIDTH // 2, mid[1] + 30), "Enjoy your day", fill=NOON, font=font_date, anchor="mm")
        return img

    all_day_events = [e for e in all_events if e["all_day"]]
    timed_events = [e for e in all_events if not e["all_day"]]
    timed_events.sort(key=lambda e: (e["start"] or dt, e["summary"]))

    # All-day bar
    row_y = HEADER_H + 4
    if all_day_events:
        draw.rectangle([(0, row_y), (WIDTH, row_y + 28)], fill=SOFT_YELLOW)
        for i, ev in enumerate(all_day_events[:6]):
            x = 16 + i * (WIDTH // 6)
            draw_rounded(draw, x, row_y + 4, x + (WIDTH // 6) - 8, row_y + 24, ev["color"], 4)
            draw.text((x + 6, row_y + 14), ev["summary"][:18], fill=WHITE, font=font_key, anchor="lm")
        row_y += 34

    # Calendar key stripe
    active_cals = {c["name"]: tuple(c["color"]) for c in calendars if c.get("events")}
    if active_cals:
        kx = 16
        for cname, ccol in active_cals.items():
            draw.rectangle([(kx, row_y + 2), (kx + 8, row_y + 12)], fill=ccol)
            draw.text((kx + 13, row_y + 7), cname, fill=BLACK, font=font_key, anchor="lm")
            kx += 90
        row_y += 18

    ROW_H = 30
    # Event list
    for ev in timed_events:
        ev_start = ev["start"].astimezone() if ev["start"] else None
        ev_end = ev["end"].astimezone() if ev["end"] else None
        time_label = ""
        if ev_start and ev_end:
            time_label = f"{ev_start.strftime('%H:%M')}-{ev_end.strftime('%H:%M')}"
        elif ev_start:
            time_label = ev_start.strftime('%H:%M')

        # Colour dot
        draw.rounded_rectangle([(14, row_y + 4), (20, row_y + ROW_H - 4)], 3, fill=ev["color"])

        # Time
        tw = draw.textlength(time_label, font=font_event_time)
        draw.text((30, row_y + ROW_H // 2), time_label, fill=BLACK, font=font_event_time, anchor="lm")

        # Title
        tx = 30 + tw + 12
        draw.text((tx, row_y + ROW_H // 2), ev["summary"][:50], fill=BLACK, font=font_event_title, anchor="lm")

        # Location on second line if present
        if ev.get("location"):
            draw.text((30, row_y + ROW_H - 6), ev["location"][:55], fill=NOON, font=font_event_loc, anchor="lm")

        row_y += ROW_H + 2
        if row_y > HEIGHT - 10:
            break

    all_day_events = [e for e in all_events if e["all_day"]]
    timed_events = [e for e in all_events if not e["all_day"]]
    timed_events.sort(key=lambda e: (e["start"] or dt, e["summary"]))

    # Layout
    CONTENT_TOP = HEADER_H + 4
    CONTENT_H = HEIGHT - CONTENT_TOP - 6

    row_y = HEADER_H + 4

    # All-day bar
    if all_day_events:
        draw.rectangle([(0, row_y), (WIDTH, row_y + 28)], fill=SOFT_YELLOW)
        for i, ev in enumerate(all_day_events[:6]):
            x = 20 + i * 130
            draw_rounded(draw, x, row_y + 4, x + 120, row_y + 24, ev["color"], 4)
            draw.text((x + 8, row_y + 14), ev["summary"][:18], fill=WHITE, font=font_key, anchor="lm")
        row_y += 34

    # Calendar key stripe
    active_cals = [(c["name"], tuple(c["color"])) for c in calendars if c.get("events")]
    if active_cals:
        kx = 20
        for cname, ccol in active_cals:
            draw.rectangle([(kx, row_y + 2), (kx + 10, row_y + 14)], fill=ccol)
            draw.text((kx + 16, row_y + 8), cname, fill=BLACK, font=font_key, anchor="lm")
            kx += 100
        row_y += 22

    # Event list
    for ev in timed_events:
        ev_start = ev["start"].astimezone() if ev["start"] else None
        ev_end = ev["end"].astimezone() if ev["end"] else None
        time_label = ""
        if ev_start and ev_end:
            time_label = f"{ev_start.strftime('%H:%M')} - {ev_end.strftime('%H:%M')}"
        elif ev_start:
            time_label = ev_start.strftime('%H:%M')

        ROW_H = 52
        draw.rectangle([(0, row_y), (12, row_y + ROW_H)], fill=ev["color"])

        draw.text((24, row_y + 18), time_label, fill=BLACK, font=font_event_time, anchor="lm")

        tx = 180
        draw.text((tx, row_y + 18), ev["summary"][:50], fill=BLACK, font=font_event_title, anchor="lm")

        if ev.get("location"):
            draw.text((tx, row_y + 38), ev["location"][:55], fill=NOON, font=font_event_loc, anchor="lm")

        row_y += ROW_H + 4
        if row_y > HEIGHT - 10:
            break

    return img


def index_for_panel(img: Image.Image) -> Image.Image:
    palette_img = Image.new("P", (1, 1))
    flat = [c for rgb in PANEL_PALETTE for c in rgb]
    palette_img.putpalette(flat + [0] * (768 - len(flat)))
    return img.quantize(palette=palette_img, dither=Image.Dither.NONE)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--payload", type=Path, default=None, help="Path to payload JSON")
    args = parser.parse_args()

    if args.payload:
        p = Path(args.payload)
        with p.open("r", encoding="utf-8") as f:
            raw = json.load(f)
        if isinstance(raw, dict) and isinstance(raw.get("merge_variables"), dict):
            payload = raw["merge_variables"]
        else:
            payload = raw
    else:
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        from nango_calendar_fetch import fetch_payload
        payload = fetch_payload()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    src = render(payload)
    src.save(str(SOURCE_PATH), "PNG")
    panel = index_for_panel(src)
    panel.save(str(OUT_PATH), "PNG")
    print(f"Source: {SOURCE_PATH}")
    print(f"Panel:  {OUT_PATH}")
    print(f"Size:   {panel.size[0]} x {panel.size[1]}, mode={panel.mode}")


if __name__ == "__main__":
    main()
