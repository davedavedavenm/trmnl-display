#!/usr/bin/env python3
"""
Calendar Day View — Multi-Layout Renderer
7-color ACeP e-ink, 800x480
Layouts: featured, agenda, weekstrip
Themes:  dark, light
"""
from __future__ import annotations

import json
import os
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
LIGHT_DIM = (180, 180, 180)
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


class Theme:
    def __init__(self, bg: tuple, fg: tuple, dim: tuple, bg_card: tuple | None = None):
        self.bg = bg
        self.fg = fg
        self.dim = dim
        self.bg_card = bg_card or bg


DARK_THEME = Theme(BLACK, WHITE, DIM)
LIGHT_THEME = Theme(WHITE, BLACK, LIGHT_DIM, WHITE)


def render_empty(draw: ImageDraw.ImageDraw, theme: Theme) -> None:
    f_clock = font(64, bold=True)
    f_date = font(24, bold=True)
    f_msg = font(20)

    now = datetime.now(timezone.utc)
    now_str = now.strftime("%H:%M")
    date_str = now.strftime("%A %d %B %Y")

    draw.text((WIDTH // 2, HEIGHT // 2 - 50), now_str, fill=theme.fg, font=f_clock, anchor="mm")
    draw.text((WIDTH // 2, HEIGHT // 2 + 15), date_str, fill=theme.dim, font=f_date, anchor="mm")
    draw.text((WIDTH // 2, HEIGHT // 2 + 55), "No events this week", fill=theme.dim, font=f_msg, anchor="mm")


def render_featured(draw: ImageDraw.ImageDraw, days: list[dict], today: str, now_str: str, theme: Theme) -> None:
    today_day = None
    for d in days:
        if d.get("date") == today:
            today_day = d
            break
    if not today_day and days:
        today_day = days[0]

    f_mast = font(18, bold=True)
    f_clock = font(24, bold=True)
    f_time = font(48, bold=True)
    f_event = font(52)
    f_source = font(20, bold=True)
    f_empty = font(32, bold=True)
    f_footer = font(16)

    if not days:
        render_empty(draw, theme)
        return

    # TOP BAR
    header_y = 22
    draw.text((24, header_y), now_str, fill=theme.fg, font=f_clock, anchor="lm")

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

        date_text = f"{day_name.upper()} {day_num} {month_abbr}"
        draw.text((WIDTH - 24, header_y), date_text, fill=theme.dim, font=f_mast, anchor="rm")

    draw.line([(24, 50), (WIDTH - 24, 50)], fill=theme.dim, width=1)

    # EVENT CARDS
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

                block_h = 120
                draw.rectangle([(24, ev_y), (WIDTH - 24, ev_y + block_h)], fill=cal_color)

                draw.text((44, ev_y + 16), time_label, fill=WHITE, font=f_time, anchor="lm")
                draw.text((44, ev_y + 72), summary, fill=WHITE, font=f_event, anchor="lm")

                badge_w = draw.textlength(cal_label, font=f_source) + 24
                badge_h = 32
                badge_x = WIDTH - 44 - badge_w
                badge_y = ev_y + 16
                draw.rounded_rectangle([(badge_x, badge_y), (badge_x + badge_w, badge_y + badge_h)], 6, fill=BLACK)
                draw.text((badge_x + 12, badge_y + 8), cal_label, fill=WHITE, font=f_source, anchor="lm")

                ev_y += block_h + 16

    # FOOTER: upcoming days
    footer_y = HEIGHT - 50
    draw.line([(24, footer_y - 6), (WIDTH - 24, footer_y - 6)], fill=theme.dim, width=1)

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

        draw.text((x_up, footer_y + 2), day_name[:3].upper(), fill=theme.dim, font=font(16, bold=True), anchor="lm")
        draw.text((x_up, footer_y + 22), day_num, fill=theme.fg, font=font(28, bold=True), anchor="lm")

        x_up += 90

    total = sum(len(c.get("events", [])) for d in days for c in d.get("calendars", []))
    draw.text((WIDTH - 24, footer_y + 18), f"{total} EVENTS", fill=theme.dim, font=f_footer, anchor="rm")


def render_agenda(draw: ImageDraw.ImageDraw, days: list[dict], today: str, now_str: str, theme: Theme) -> None:
    f_mast = font(18, bold=True)
    f_clock = font(24, bold=True)
    f_time = font(22, bold=True)
    f_event = font(22)
    f_source = font(14, bold=True)
    f_empty = font(28, bold=True)
    f_day = font(16, bold=True)

    if not days:
        render_empty(draw, theme)
        return

    # TOP BAR
    header_y = 22
    draw.text((24, header_y), now_str, fill=theme.fg, font=f_clock, anchor="lm")
    draw.line([(24, 50), (WIDTH - 24, 50)], fill=theme.dim, width=1)

    # COMPACT AGENDA LIST
    y = 60
    max_items = 12
    item_h = 32
    count = 0

    for day in days:
        if count >= max_items:
            break

        date_str = day.get("date", "")
        day_name = day.get("day_name", "")[:3].upper()
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            day_num = dt.strftime("%d")
        except (ValueError, TypeError):
            day_num = date_str[-2:]

        is_today = date_str == today

        for cal in day.get("calendars", []):
            cal_name_raw = cal.get("name", "?")
            cal_color = tuple(cal.get("color", [128, 128, 128]))
            cal_label = SOURCE_LABELS.get(cal_name_raw, cal_name_raw[:8])

            for ev in cal.get("events", []):
                if count >= max_items or y > HEIGHT - 40:
                    break

                start_s = ev.get("start", "")
                all_day = ev.get("all_day", False)
                summary = ev.get("summary", "")[:48]

                if all_day:
                    time_label = "ALL DAY"
                else:
                    try:
                        st = datetime.fromisoformat(start_s.replace("Z", "+00:00"))
                        time_label = st.strftime("%H:%M")
                    except (ValueError, TypeError):
                        time_label = ""

                # Accent strip
                strip_w = 6
                if is_today and theme.bg == BLACK:
                    draw.rectangle([(24, y), (24 + strip_w, y + item_h)], fill=cal_color)
                elif is_today:
                    draw.rectangle([(24, y), (24 + strip_w, y + item_h)], fill=cal_color)

                # Time
                draw.text((44, y + 6), time_label, fill=theme.fg if not all_day else theme.dim, font=f_time, anchor="lm")
                # Summary
                draw.text((130, y + 6), summary, fill=theme.fg, font=f_event, anchor="lm")
                # Source badge
                badge_w = draw.textlength(cal_label, font=f_source) + 12
                draw.text((WIDTH - 24, y + 6), cal_label, fill=theme.dim, font=f_source, anchor="rm")

                if count > 0:
                    draw.line([(44, y - 4), (WIDTH - 24, y - 4)], fill=theme.dim, width=1)
                y += item_h + 6
                count += 1

    # Day headers in left gutter
    # Already integrated above with accent strips
    total = sum(len(c.get("events", [])) for d in days for c in d.get("calendars", []))
    draw.text((WIDTH - 24, HEIGHT - 20), f"{total} events", fill=theme.dim, font=font(14, bold=True), anchor="rm")


def render_weekstrip(draw: ImageDraw.ImageDraw, days: list[dict], today: str, now_str: str, theme: Theme) -> None:
    f_mast = font(18, bold=True)
    f_clock = font(24, bold=True)
    f_day = font(16, bold=True)
    f_num = font(36, bold=True)
    f_event = font(14)
    f_source = font(12, bold=True)
    f_empty = font(28, bold=True)

    if not days:
        render_empty(draw, theme)
        return

    # TOP BAR
    header_y = 22
    draw.text((24, header_y), now_str, fill=theme.fg, font=f_clock, anchor="lm")
    draw.line([(24, 50), (WIDTH - 24, 50)], fill=theme.dim, width=1)

    # 7-DAY STRIP
    col_w = (WIDTH - 48) // 7
    x_start = 24
    strip_y = 60
    strip_h = 360

    # Fill in missing days to show full week
    all_days = list(days)
    if all_days:
        first_date = all_days[0]["date"]
        try:
            first_dt = datetime.strptime(first_date, "%Y-%m-%d")
            day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            for i in range(7):
                d = first_dt.replace(day=first_dt.day + i) if False else None
        except:
            pass

    for i in range(7):
        x = x_start + i * col_w
        cx = x + col_w // 2

        day = all_days[i] if i < len(all_days) else None
        if day is None:
            continue

        date_str = day.get("date", "")
        day_name = day.get("day_name", "")[:3].upper()
        is_today = date_str == today
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            day_num = dt.strftime("%d")
        except (ValueError, TypeError):
            day_num = date_str[-2:]

        # Day header background
        if is_today:
            draw.rectangle([(x, strip_y), (x + col_w - 2, strip_y + 56)], fill=BLUE)
            draw.text((cx, strip_y + 8), day_name, fill=WHITE, font=f_day, anchor="ma")
            draw.text((cx, strip_y + 30), day_num, fill=WHITE, font=f_num, anchor="ma")
        else:
            draw.text((cx, strip_y + 8), day_name, fill=theme.dim, font=f_day, anchor="ma")
            draw.text((cx, strip_y + 30), day_num, fill=theme.fg, font=f_num, anchor="ma")

        # Events as colored dots with labels
        ev_y = strip_y + 64
        ev_count = 0
        for cal in day.get("calendars", []):
            cal_color = tuple(cal.get("color", [128, 128, 128]))
            for ev in cal.get("events", []):
                if ev_y > strip_y + strip_h - 20 or ev_count >= 6:
                    break

                summary = ev.get("summary", "")[:12]
                # Colored dot
                dot_r = 5
                draw.ellipse([(cx - dot_r, ev_y + 4), (cx + dot_r, ev_y + 4 + dot_r * 2)], fill=cal_color)
                # Event text
                draw.text((cx, ev_y + 16), summary, fill=theme.fg, font=f_event, anchor="mt")
                ev_y += 28
                ev_count += 1

    # FOOTER
    total = sum(len(c.get("events", [])) for d in days for c in d.get("calendars", []))
    draw.text((WIDTH - 24, HEIGHT - 20), f"{total} events this week", fill=theme.dim, font=font(14, bold=True), anchor="rm")


def render(payload: dict) -> Image.Image:
    theme_name = os.getenv("TRMNL_CALENDAR_THEME", payload.get("theme", "dark")).lower()
    layout = os.getenv("TRMNL_CALENDAR_LAYOUT", payload.get("layout", "featured")).lower()

    theme = LIGHT_THEME if theme_name == "light" else DARK_THEME

    img = Image.new("RGB", (WIDTH, HEIGHT), theme.bg)
    draw = ImageDraw.Draw(img)

    days = payload.get("days", [])
    today = payload.get("today", "")
    now_str = datetime.now(timezone.utc).strftime("%H:%M")

    if layout == "agenda":
        render_agenda(draw, days, today, now_str, theme)
    elif layout == "weekstrip":
        render_weekstrip(draw, days, today, now_str, theme)
    else:
        render_featured(draw, days, today, now_str, theme)

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
