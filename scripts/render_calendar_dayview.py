#!/usr/bin/env python3
"""
Calendar Day View — Featured Event Layout
7-color ACeP e-ink, 800x480
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
DIM = (80, 80, 80)
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

    f_mast = font(18, bold=True)
    f_clock = font(24, bold=True)
    f_time = font(48, bold=True)
    f_event = font(52)
    f_source = font(20, bold=True)
    f_empty = font(32, bold=True)
    f_footer = font(16)

    days = payload.get("days", [])
    today = payload.get("today", "")
    now_str = datetime.now(timezone.utc).strftime("%H:%M")

    if not days:
        draw.text((WIDTH // 2, HEIGHT // 2 - 10), "No events this week", fill=WHITE, font=f_empty, anchor="mm")
        return img

    today_day = None
    for d in days:
        if d.get("date") == today:
            today_day = d
            break
    if not today_day and days:
        today_day = days[0]

    # ═══════════════════════════════════════════════════════
    # TOP BAR: Clock left, date info right
    # ═══════════════════════════════════════════════════════
    header_y = 22
    draw.text((24, header_y), now_str, fill=WHITE, font=f_clock, anchor="lm")
    
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
        
        # Date info on right side of header
        date_text = f"{day_name.upper()} {day_num} {month_abbr}"
        draw.text((WIDTH - 24, header_y), date_text, fill=DIM, font=f_mast, anchor="rm")
    
    # Separator line
    draw.line([(24, 50), (WIDTH - 24, 50)], fill=DIM, width=1)

    # ═══════════════════════════════════════════════════════
    # MAIN: Featured event cards (large, full-width)
    # ═══════════════════════════════════════════════════════
    ev_y = 66
    
    if today_day:
        calendars = today_day.get("calendars", [])
        max_events = 3

        for cal in calendars:
            cal_name_raw = cal.get("name", "?")
            cal_color = tuple(cal.get("color", [128, 128, 128]))
            cal_label = SOURCE_LABELS.get(cal_name_raw, cal_name_raw.split("-")[-1].capitalize()[:10])
            cal_events = cal.get("events", [])[:max_events]

            for ev in cal_events:
                if ev_y > HEIGHT - 80:
                    break

                start_s = ev.get("start", "")
                all_day = ev.get("all_day", False)
                summary = ev.get("summary", "")[:35]

                if all_day:
                    time_label = "ALL DAY"
                else:
                    try:
                        st = datetime.fromisoformat(start_s.replace("Z", "+00:00"))
                        time_label = st.strftime("%H:%M")
                    except (ValueError, TypeError):
                        time_label = ""

                # Large colored block
                block_h = 120
                draw.rectangle([(24, ev_y), (WIDTH - 24, ev_y + block_h)], fill=cal_color)

                # Time (top-left)
                draw.text((44, ev_y + 16), time_label, fill=WHITE, font=f_time, anchor="lm")

                # Event summary (below time)
                draw.text((44, ev_y + 72), summary, fill=WHITE, font=f_event, anchor="lm")

                # Source badge (top-right)
                badge_w = draw.textlength(cal_label, font=f_source) + 24
                badge_h = 32
                badge_x = WIDTH - 44 - badge_w
                badge_y = ev_y + 16
                draw.rounded_rectangle([(badge_x, badge_y), (badge_x + badge_w, badge_y + badge_h)], 6, fill=BLACK)
                draw.text((badge_x + 12, badge_y + 8), cal_label, fill=WHITE, font=f_source, anchor="lm")

                ev_y += block_h + 16

    # ═══════════════════════════════════════════════════════
    # BOTTOM: Upcoming days strip
    # ═══════════════════════════════════════════════════════
    footer_y = HEIGHT - 50
    draw.line([(24, footer_y - 6), (WIDTH - 24, footer_y - 6)], fill=DIM, width=1)

    upcoming_days = [d for d in days if d.get("date") != today]
    x_up = 24

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

        draw.text((x_up, footer_y + 2), day_name[:3].upper(), fill=DIM, font=font(16, bold=True), anchor="lm")
        draw.text((x_up, footer_y + 22), day_num, fill=WHITE, font=font(28, bold=True), anchor="lm")

        x_up += 90

    total = sum(len(c.get("events", [])) for d in days for c in d.get("calendars", []))
    draw.text((WIDTH - 24, footer_y + 18), f"{total} EVENTS", fill=DIM, font=f_footer, anchor="rm")

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
