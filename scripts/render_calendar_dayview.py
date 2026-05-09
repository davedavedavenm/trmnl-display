#!/usr/bin/env python3
"""
Calendar Day View — Bold Block Layout
7-color ACeP e-ink, 800x480
Design direction: Solid colored blocks, not thin strips. High contrast. Editorial feel.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

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
DIM = (70, 70, 70)
PANEL_PALETTE = [BLACK, WHITE, RED, YELLOW, BLUE, GREEN, ORANGE]

SOURCE_COLORS = {
    "REDACTED-CONNECTION": BLUE,
    "REDACTED-CONNECTION": GREEN,
    "REDACTED-CONNECTION": RED,
    "REDACTED-CONNECTION": ORANGE,
}

SOURCE_LABELS = {
    "REDACTED-CONNECTION": "REDACTED-LABEL",
    "REDACTED-CONNECTION": "DAVE",
    "REDACTED-CONNECTION": "JEN",
    "REDACTED-CONNECTION": "OUTLOOK",
}


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


def index_for_panel(img: Image.Image) -> Image.Image:
    palette_img = Image.new("P", (1, 1))
    flat = [c for rgb in PANEL_PALETTE for c in rgb]
    palette_img.putpalette(flat + [0] * (768 - len(flat)))
    return img.quantize(palette=palette_img, dither=Image.Dither.FLOYDSTEINBERG)


def render(payload: dict) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT), BLACK)
    draw = ImageDraw.Draw(img)

    f_mast = font(16, bold=True)
    f_clock = font(20, bold=True)
    f_day_name = font(28, bold=True)
    f_day_num = font(100, bold=True)
    f_month = font(22)
    f_time = font(24, bold=True)
    f_event = font(26)
    f_source = font(14, bold=True)
    f_empty = font(24, bold=True)
    f_upcoming = font(18, bold=True)
    f_day_small = font(22, bold=True)
    f_day_num_small = font(44, bold=True)

    days = payload.get("days", [])
    today = payload.get("today", "")
    now_str = datetime.now(timezone.utc).strftime("%H:%M")

    if not days:
        draw.text((WIDTH // 2, HEIGHT // 2 - 10), "No events this week", fill=WHITE, font=f_empty, anchor="mm")
        return img

    # ═══════════════════════════════════════════════════════
    # TOP BAR: Colored block header
    # ═══════════════════════════════════════════════════════
    draw.rectangle([(0, 0), (WIDTH, 48)], fill=BLUE)
    draw.text((20, 24), "AGENDA", fill=WHITE, font=f_mast, anchor="lm")
    draw.text((WIDTH - 20, 24), now_str, fill=WHITE, font=f_clock, anchor="rm")

    # ═══════════════════════════════════════════════════════
    # LAYOUT: Left date hero (280px) | Right events (520px)
    # ═══════════════════════════════════════════════════════
    rail_w = 280
    event_x = rail_w + 16

    # Find today
    today_day = None
    for d in days:
        if d.get("date") == today:
            today_day = d
            break
    if not today_day and days:
        today_day = days[0]

    if today_day:
        day_name = today_day.get("day_name", "")
        date_str = today_day.get("date", "")
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            day_num = dt.strftime("%d")
            month_abbr = dt.strftime("%b").upper()
        except (ValueError, TypeError):
            day_num = date_str[-2:]
            month_abbr = ""

        # ── LEFT: Date hero ──
        # Day name in colored block
        draw.rectangle([(16, 64), (rail_w - 16, 104)], fill=BLUE)
        draw.text((rail_w // 2, 84), day_name.upper(), fill=WHITE, font=f_day_name, anchor="mm")

        # Giant date number
        draw.text((rail_w // 2, 110), day_num, fill=WHITE, font=f_day_num, anchor="mm")

        # Month label
        draw.text((rail_w // 2, 200), month_abbr, fill=DIM, font=f_month, anchor="mm")

        # ── RIGHT: Events as solid colored blocks ──
        ev_y = 64
        calendars = today_day.get("calendars", [])
        max_events = 4

        for cal in calendars:
            cal_name_raw = cal.get("name", "?")
            cal_color = tuple(cal.get("color", [128, 128, 128]))
            cal_label = SOURCE_LABELS.get(cal_name_raw, cal_name_raw.split("-")[-1].capitalize()[:10])
            cal_events = cal.get("events", [])[:max_events]

            for ev in cal_events:
                if ev_y > HEIGHT - 70:
                    break

                start_s = ev.get("start", "")
                all_day = ev.get("all_day", False)
                summary = ev.get("summary", "")[:42]

                if all_day:
                    time_label = "ALL DAY"
                else:
                    try:
                        st = datetime.fromisoformat(start_s.replace("Z", "+00:00"))
                        time_label = st.strftime("%H:%M")
                    except (ValueError, TypeError):
                        time_label = ""

                # Solid colored event block
                block_h = 60
                draw.rectangle([(event_x, ev_y), (WIDTH - 16, ev_y + block_h)], fill=cal_color)

                # Time (white, bold)
                draw.text((event_x + 12, ev_y + 8), time_label, fill=WHITE, font=f_time, anchor="lm")

                # Event summary (white)
                draw.text((event_x + 12, ev_y + 32), summary, fill=WHITE, font=f_event, anchor="lm")

                ev_y += block_h + 8

    # ═══════════════════════════════════════════════════════
    # BOTTOM: Upcoming days strip
    # ═══════════════════════════════════════════════════════
    footer_y = HEIGHT - 56
    draw.rectangle([(0, footer_y), (WIDTH, HEIGHT)], fill=BLACK)
    draw.line([(0, footer_y), (WIDTH, footer_y)], fill=DIM, width=1)

    upcoming_days = [d for d in days if d.get("date") != today]
    x_up = 20

    for day in upcoming_days[:3]:
        if x_up > WIDTH - 100:
            break

        day_name = day.get("day_name", "")
        date_str = day.get("date", "")
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            day_num = dt.strftime("%d")
        except (ValueError, TypeError):
            day_num = date_str[-2:]

        # Day name
        draw.text((x_up, footer_y + 6), day_name[:3].upper(), fill=DIM, font=font(14, bold=True), anchor="lm")
        # Date number
        draw.text((x_up, footer_y + 22), day_num, fill=WHITE, font=f_day_small, anchor="lm")

        x_up += 120

    # Event count footer
    total = sum(len(c.get("events", [])) for d in days for c in d.get("calendars", []))
    draw.text((WIDTH - 20, footer_y + 20), f"{total} EVENTS", fill=DIM, font=font(14, bold=True), anchor="rm")

    return img


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--payload", type=Path, default=None)
    args = parser.parse_args()

    if args.payload:
        p = Path(args.payload)
        with p.open("r", encoding="utf-8") as f:
            payload = json.load(f)
    else:
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent))
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
