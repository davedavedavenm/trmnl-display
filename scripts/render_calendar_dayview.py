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


def hour_y(hour: int, start_hour: int, end_hour: int, top: int, height: int) -> int:
    total_h = end_hour - start_hour
    frac = (hour - start_hour) / total_h
    return int(top + frac * height)


def render(payload: dict) -> Image.Image:
    bg = (30, 30, 30)
    img = Image.new("RGB", (WIDTH, HEIGHT), bg)
    draw = ImageDraw.Draw(img)

    font_title = font(28, bold=True)
    font_day = font(20)
    font_head = font(14, bold=True)
    font_hour = font(13)
    font_event_title = font(17, bold=True)
    font_event_loc = font(12)
    font_event_time = font(13)
    font_empty = font(18)
    font_footer = font(12)

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
    HEADER_H = 56
    draw.rectangle([(0, 0), (WIDTH, HEADER_H)], fill=(20, 20, 20))
    draw.text((20, HEADER_H // 2), f"{day_name}", fill=WHITE, font=font_title, anchor="lm")
    draw.text((20, HEADER_H - 8), display_date, fill=DIM, font=font_day, anchor="lm")

    # Calendar key
    key_x = 320
    key_y = 12
    for i, (cname, ccol) in enumerate(CALENDAR_COLORS):
        any_from_cal = any(c.get("name") == cname for c in calendars)
        if any_from_cal:
            kx = key_x + (i % 3) * 160
            ky = key_y + (i // 3) * 18
            draw.rectangle([(kx, ky), (kx + 10, ky + 10)], fill=ccol)
            draw.text((kx + 16, ky + 5), cname, fill=DIM, font=font_footer, anchor="lm")

    # Collect all events
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
        mid = (WIDTH // 2, HEIGHT // 2 + 20)
        draw.text(mid, "No events today", fill=WHITE, font=font_empty, anchor="mm")
        draw.text((WIDTH // 2, mid[1] + 28), "Enjoy your day", fill=DIM, font=font_empty, anchor="mm")
        return img

    all_day_events = [e for e in all_events if e["all_day"]]
    timed_events = [e for e in all_events if not e["all_day"]]
    timed_events.sort(key=lambda e: (e["start"] or dt, e["summary"]))

    # Layout
    CONTENT_TOP = HEADER_H + 4
    CONTENT_H = HEIGHT - CONTENT_TOP - 6

    # All-day strip
    ads_h = 0
    if all_day_events:
        ads_h = 34
        draw.rectangle([(0, CONTENT_TOP), (WIDTH, CONTENT_TOP + ads_h)], fill=CARD_BG)
        for i, ev in enumerate(all_day_events[:4]):
            x = 14 + i * 195
            draw.rectangle([(x, CONTENT_TOP + 8), (x + 4, CONTENT_TOP + ads_h - 8)], fill=ev["color"])
            tw = draw.textlength(ev["summary"], font=font_event_loc)
            draw.text((x + 10, CONTENT_TOP + ads_h // 2), ev["summary"][:22], fill=WHITE, font=font_event_loc, anchor="lm")

    # Timeline
    tl_top = CONTENT_TOP + ads_h + 4
    tl_h = CONTENT_H - ads_h - 4
    start_h = 6
    end_h = 23
    total_hours = end_h - start_h

    # Hour labels
    for h in range(start_h, end_h + 1):
        y = hour_y(h, start_h, end_h, tl_top, tl_h)
        ampm = f"{h:02d}:00"
        draw.text((8, y), ampm, fill=DIM, font=font_hour, anchor="rm")
        draw.line([(50, y), (WIDTH - 10, y)], fill=(50, 50, 50), width=1)

    # Current time line
    now = datetime.now(timezone.utc)
    if start_h <= now.hour < end_h:
        cy = hour_y(now.hour + now.minute / 60, start_h, end_h, tl_top, tl_h)
        draw.line([(50, cy), (WIDTH - 10, cy)], fill=RED, width=2)

    # Event bars
    for ev in timed_events:
        if not ev["start"] or not ev["end"]:
            continue
        ev_start = ev["start"].astimezone()
        ev_end = ev["end"].astimezone()
        ev_day_start = dt.replace(hour=start_h, minute=0)
        ev_day_end = dt.replace(hour=end_h, minute=0) + timedelta(hours=1)

        clamp_s = max(ev_start, ev_day_start)
        clamp_e = min(ev_end, ev_day_end)
        if clamp_s >= clamp_e:
            continue

        y1 = hour_y(clamp_s.hour + clamp_s.minute / 60, start_h, end_h, tl_top, tl_h)
        y2 = hour_y(clamp_e.hour + clamp_e.minute / 60, start_h, end_h, tl_top, tl_h)
        bar_h = max(y2 - y1, 14)

        draw.rectangle([(54, y1), (56, y1 + bar_h)], fill=ev["color"])
        draw_rounded(draw, 62, y1, WIDTH - 14, y1 + bar_h, ev["color"], radius=4)
        draw.text((72, y1 + bar_h // 2), ev["summary"][:40], fill=WHITE, font=font_event_title, anchor="lm")

        time_label = f"{ev_start.strftime('%H:%M')} - {ev_end.strftime('%H:%M')}"
        draw.text((WIDTH - 24, y1 + bar_h // 2), time_label, fill=WHITE, font=font_event_time, anchor="rm")

        if ev["location"]:
            draw.text((72, y1 + bar_h // 2 + 14), ev["location"][:35], fill=DIM, font=font_event_loc, anchor="lm")

    return img


def index_for_panel(img: Image.Image) -> Image.Image:
    palette_img = Image.new("P", (1, 1))
    flat = [c for rgb in PANEL_PALETTE for c in rgb]
    palette_img.putpalette(flat + [0] * (768 - len(flat)))
    return img.quantize(palette=palette_img, dither=Image.Dither.FLOYDSTEINBERG)


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
