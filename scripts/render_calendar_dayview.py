#!/usr/bin/env python3
"""
Calendar Day View — Multi-Layout Renderer
Optimized for 7-color ACeP e-ink (Spectra), 800x480
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
DIM = (128, 128, 128)
LIGHT_DIM = (160, 160, 160)

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


def closest_panel_color(rgb: tuple[int, int, int] | list[int]) -> tuple[int, int, int]:
    if not rgb or len(rgb) < 3:
        return BLACK
    min_dist = float("inf")
    best_color = BLACK
    for p_color in PANEL_PALETTE:
        dist = sum((c1 - c2) ** 2 for c1, c2 in zip(rgb, p_color))
        if dist < min_dist:
            min_dist = dist
            best_color = p_color
    return best_color


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    base_dir = Path(__file__).resolve().parent
    local_path = base_dir / "fonts" / ("Outfit-Bold.ttf" if bold else "Outfit-Regular.ttf")
    if local_path.exists():
        try:
            return ImageFont.truetype(str(local_path), size)
        except OSError:
            pass

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


DARK_THEME = Theme(BLACK, WHITE, DIM, BLACK)
LIGHT_THEME = Theme(WHITE, BLACK, LIGHT_DIM, WHITE)


def render_empty(draw: ImageDraw.ImageDraw, theme: Theme) -> None:
    f_clock = font(64, bold=True)
    f_date = font(24, bold=True)
    f_msg = font(20)

    now = datetime.now(timezone.utc)
    date_str = now.strftime("%A %d %B %Y")

    draw.text((WIDTH // 2, HEIGHT // 2 - 15), date_str, fill=theme.dim, font=f_date, anchor="mm")
    draw.text((WIDTH // 2, HEIGHT // 2 + 25), "No events this week", fill=theme.dim, font=f_msg, anchor="mm")


def render_featured(draw: ImageDraw.ImageDraw, days: list[dict], today: str, now_str: str, theme: Theme) -> None:
    today_day = None
    for d in days:
        if d.get("date") == today:
            today_day = d
            break
    if not today_day and days:
        today_day = days[0]

    f_mast = font(18, bold=True)
    f_footer = font(16)

    if not days:
        render_empty(draw, theme)
        return

    # TOP BAR
    header_y = 22

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

    draw.line([(24, 45), (WIDTH - 24, 45)], fill=theme.dim, width=1)

    # Collect all upcoming events chronologically across the week
    all_upcoming_events = []
    for day in days:
        day_date = day.get("date", "")
        day_name = day.get("day_name", "")
        
        day_events = []
        for cal in day.get("calendars", []):
            cal_name_raw = cal.get("name", "?")
            cal_color = closest_panel_color(cal.get("color", [128, 128, 128]))
            cal_label = cal.get("label") or SOURCE_LABELS.get(cal_name_raw, cal_name_raw.split("-")[-1].capitalize()[:10])
            
            for ev in cal.get("events", []):
                day_events.append({
                    "event": ev,
                    "cal_color": cal_color,
                    "cal_label": cal_label,
                    "day_date": day_date,
                    "day_name": day_name
                })
        
        # Sort day_events by start time
        def get_event_sort_key(item):
            ev = item["event"]
            start_s = ev.get("start", "")
            if ev.get("all_day", False):
                return "00:00"
            try:
                if "T" in start_s:
                    return start_s.split("T")[1][:5]
            except Exception:
                pass
            return "23:59"
            
        day_events.sort(key=get_event_sort_key)
        all_upcoming_events.extend(day_events)

    # EVENT CARDS
    ev_y = 60
    block_h = 108
    gap = 14
    max_events = 3
    rendered_count = 0

    for ev_item in all_upcoming_events:
        if rendered_count >= max_events or ev_y > HEIGHT - 120:
            break

        ev = ev_item["event"]
        cal_color = ev_item["cal_color"]
        cal_label = ev_item["cal_label"]
        event_date_str = ev_item["day_date"]

        start_s = ev.get("start", "")
        end_s = ev.get("end", "")
        all_day = ev.get("all_day", False)
        summary = ev.get("summary", "")[:45]
        location = ev.get("location", "").strip()
        desc = ev.get("description", "").strip()
        status = ev.get("status", "confirmed")
        attendees = ev.get("attendees", [])
        attendee_count = len([a for a in attendees if a.get("status") == "accepted"])

        # Check if event is today
        is_event_today = event_date_str == today

        if all_day:
            time_label = "ALL DAY"
        else:
            try:
                st = datetime.fromisoformat(start_s.replace("Z", "+00:00"))
                time_label = st.strftime("%H:%M")
                if end_s:
                    et = datetime.fromisoformat(end_s.replace("Z", "+00:00"))
                    time_label += f" - {et.strftime('%H:%M')}"
            except (ValueError, TypeError):
                time_label = ""

        # Prepend date if not today
        if not is_event_today and event_date_str:
            try:
                ev_dt = datetime.strptime(event_date_str, "%Y-%m-%d")
                day_prefix = ev_dt.strftime("%a %d %b").upper() # e.g. "SAT 20 JUN"
                time_label = f"{day_prefix} • {time_label}"
            except Exception:
                time_label = f"{event_date_str} • {time_label}"

        # Card Outer Box: Colored outline matching the calendar's color
        draw.rounded_rectangle([(24, ev_y), (WIDTH - 24, ev_y + block_h)], radius=10, fill=theme.bg_card, outline=cal_color, width=3)

        # Left Accent Bar
        draw.rounded_rectangle([(26, ev_y + 2), (34, ev_y + block_h - 2)], radius=3, fill=cal_color)

        # Render Time/Date in cal_color
        draw.text((46, ev_y + 14), time_label, fill=cal_color, font=font(18, bold=True))

        # Render Summary
        display_summary = f"[CANCELLED] {summary}" if status == "cancelled" else summary
        draw.text((46, ev_y + 42), display_summary, fill=theme.fg, font=font(22, bold=True))

        # Cancelled Strike-through
        if status == "cancelled":
            text_w = draw.textlength(display_summary, font=font(22, bold=True))
            draw.line([(46, ev_y + 42 + 13), (46 + text_w, ev_y + 42 + 13)], fill=RED, width=3)

        # Render Location or Description
        subtext = ""
        if location:
            subtext = f"📍 {location[:55]}"
        elif desc:
            subtext = desc.replace("\n", " ").replace("\r", " ")[:60]

        if subtext:
            draw.text((46, ev_y + 74), subtext, fill=theme.fg, font=font(15))

        # Source Badge (top-right of card)
        badge_w = draw.textlength(cal_label, font=font(12, bold=True)) + 16
        badge_h = 24
        badge_x = WIDTH - 24 - 12 - badge_w
        badge_y = ev_y + 14

        badge_fg = BLACK if cal_color in (YELLOW, WHITE) else WHITE
        draw.rounded_rectangle([(badge_x, badge_y), (badge_x + badge_w, badge_y + badge_h)], radius=5, fill=cal_color)
        draw.text((badge_x + badge_w // 2, badge_y + badge_h // 2), cal_label, fill=badge_fg, font=font(12, bold=True), anchor="mm")

        # Attendee Count Badge
        if attendee_count > 0:
            attend_text = f"👥 {attendee_count}"
            a_w = draw.textlength(attend_text, font=font(11, bold=True)) + 12
            a_x = badge_x - 8 - a_w
            a_y = badge_y
            draw.rounded_rectangle([(a_x, a_y), (a_x + a_w, a_y + badge_h)], radius=5, outline=theme.dim, width=1)
            draw.text((a_x + a_w // 2, a_y + badge_h // 2), attend_text, fill=theme.fg, font=font(11, bold=True), anchor="mm")

        ev_y += block_h + gap
        rendered_count += 1

    # FOOTER: upcoming days
    footer_y = HEIGHT - 45
    draw.line([(24, footer_y - 6), (WIDTH - 24, footer_y - 6)], fill=theme.dim, width=1)

    upcoming_days = [d for d in days if d.get("date") != today]
    x_up = 24

    for day in upcoming_days[:4]:
        if x_up > WIDTH - 150:
            break

        day_name = day.get("day_name", "")
        date_str = day.get("date", "")
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            day_num = dt.strftime("%d")
            month_abbr = dt.strftime("%b").upper()
        except (ValueError, TypeError):
            day_num = date_str[-2:]
            month_abbr = ""

        total_day_events = sum(len(c.get("events", [])) for c in day.get("calendars", []))

        draw.text((x_up, footer_y + 2), f"{day_name[:3].upper()} {day_num} {month_abbr}", fill=theme.dim, font=font(14, bold=True), anchor="lm")

        # Draw dynamic color-coded bullet dot under/beside the date if there are events
        if total_day_events > 0:
            dot_color = theme.fg
            if day.get("calendars"):
                first_cal = day["calendars"][0]
                dot_color = closest_panel_color(first_cal.get("color", [128, 128, 128]))

            draw.ellipse([(x_up, footer_y + 20), (x_up + 6, footer_y + 26)], fill=dot_color)
            draw.text((x_up + 12, footer_y + 23), f"{total_day_events} event{'s' if total_day_events > 1 else ''}", fill=theme.fg, font=font(14, bold=True), anchor="lm")
        else:
            draw.text((x_up, footer_y + 23), "No events", fill=theme.dim, font=font(14), anchor="lm")

        x_up += 160

    total = sum(len(c.get("events", [])) for d in days for c in d.get("calendars", []))
    draw.text((WIDTH - 24, footer_y + 16), f"{total} EVENTS THIS WEEK", fill=theme.dim, font=f_footer, anchor="rm")


def render_agenda(draw: ImageDraw.ImageDraw, days: list[dict], today: str, now_str: str, theme: Theme) -> None:
    f_clock = font(24, bold=True)

    if not days:
        render_empty(draw, theme)
        return

    # TOP BAR
    header_y = 22
    draw.line([(24, 45), (WIDTH - 24, 45)], fill=theme.dim, width=1)

    # TWO-COLUMN AGENDA LAYOUT
    # Left Gutter: Day info (x: 24 to 164)
    # Right Gutter: Events (x: 184 to WIDTH - 24)
    divider_x = 170
    draw.line([(divider_x, 60), (divider_x, HEIGHT - 35)], fill=theme.dim, width=2)

    y = 65
    row_h = 52
    gap = 8
    max_y = HEIGHT - 45

    for day in days:
        if y > max_y - 20:
            break

        date_str = day.get("date", "")
        day_name = day.get("day_name", "")
        is_today = date_str == today

        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            day_label = dt.strftime("%b %d").upper()
        except (ValueError, TypeError):
            day_label = date_str[-5:]

        # Filter events
        day_events = []
        for cal in day.get("calendars", []):
            cal_color = closest_panel_color(cal.get("color", [128, 128, 128]))
            cal_label = cal.get("label") or cal.get("name", "")[:10]
            for ev in cal.get("events", []):
                day_events.append((ev, cal_color, cal_label))

        if not day_events:
            continue

        start_y = y

        for ev, cal_color, cal_label in day_events:
            if y > max_y:
                break

            start_s = ev.get("start", "")
            end_s = ev.get("end", "")
            all_day = ev.get("all_day", False)
            summary = ev.get("summary", "")[:42]

            if all_day:
                time_label = "ALL DAY"
            else:
                try:
                    st = datetime.fromisoformat(start_s.replace("Z", "+00:00"))
                    time_label = st.strftime("%H:%M")
                    if end_s:
                        et = datetime.fromisoformat(end_s.replace("Z", "+00:00"))
                        time_label += f" - {et.strftime('%H:%M')}"
                except (ValueError, TypeError):
                    time_label = ""

            # Accent Color Bar (x: 184 to 188)
            draw.rounded_rectangle([(divider_x + 14, y), (divider_x + 18, y + 42)], radius=2, fill=cal_color)

            # Time (x: 196)
            draw.text((divider_x + 26, y + 2), time_label, fill=theme.fg, font=font(15, bold=True))

            # Event Title (x: 196)
            draw.text((divider_x + 26, y + 22), summary, fill=theme.fg, font=font(17))

            # Source Tag
            draw.text((WIDTH - 24, y + 12), cal_label, fill=theme.dim, font=font(13, bold=True), anchor="rm")

            y += row_h + gap

        # Draw Day Header in Left Gutter
        day_center_y = start_y + (y - start_y - gap) // 2

        if is_today:
            # Highlight Today
            draw.rounded_rectangle([(24, day_center_y - 22), (divider_x - 14, day_center_y + 22)], radius=6, fill=BLUE)
            draw.text(((24 + divider_x - 14) // 2, day_center_y - 8), "TODAY", fill=WHITE, font=font(13, bold=True), anchor="mm")
            draw.text(((24 + divider_x - 14) // 2, day_center_y + 10), day_label, fill=WHITE, font=font(15, bold=True), anchor="mm")
        else:
            # Normal Day
            draw.text(((24 + divider_x - 14) // 2, day_center_y - 10), day_name[:3].upper(), fill=theme.dim, font=font(14, bold=True), anchor="mm")
            draw.text(((24 + divider_x - 14) // 2, day_center_y + 10), day_label, fill=theme.fg, font=font(16, bold=True), anchor="mm")

        # Bottom separator for this day's group
        if y < max_y:
            draw.line([(24, y - gap // 2), (WIDTH - 24, y - gap // 2)], fill=theme.dim, width=1)
            y += 6

    total = sum(len(c.get("events", [])) for d in days for c in d.get("calendars", []))
    draw.text((WIDTH - 24, HEIGHT - 20), f"{total} events this week", fill=theme.dim, font=font(14, bold=True), anchor="rm")


def render_weekstrip(draw: ImageDraw.ImageDraw, days: list[dict], today: str, now_str: str, theme: Theme) -> None:
    f_clock = font(24, bold=True)

    if not days:
        render_empty(draw, theme)
        return

    # TOP BAR
    header_y = 22
    draw.line([(24, 45), (WIDTH - 24, 45)], fill=theme.dim, width=1)

    # 7-DAY COLUMNS
    col_w = (WIDTH - 48) // 7
    x_start = 24
    strip_y = 60
    strip_h = 375

    for i in range(7):
        x = x_start + i * col_w
        cx = x + col_w // 2

        day = days[i] if i < len(days) else None
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

        # Day column rounded card
        outline_color = BLUE if is_today else theme.dim
        outline_width = 3 if is_today else 2
        draw.rounded_rectangle([(x, strip_y), (x + col_w - 4, strip_y + strip_h)], radius=8, fill=theme.bg_card, outline=outline_color, width=outline_width)

        # Header section inside card
        if is_today:
            draw.rounded_rectangle([(x + 2, strip_y + 2), (x + col_w - 6, strip_y + 48)], radius=6, fill=BLUE)
            draw.text((cx - 2, strip_y + 12), day_name, fill=WHITE, font=font(12, bold=True), anchor="ma")
            draw.text((cx - 2, strip_y + 26), day_num, fill=WHITE, font=font(20, bold=True), anchor="ma")
        else:
            draw.text((cx - 2, strip_y + 10), day_name, fill=theme.dim, font=font(12, bold=True), anchor="ma")
            draw.text((cx - 2, strip_y + 24), day_num, fill=theme.fg, font=font(20, bold=True), anchor="ma")

        draw.line([(x + 8, strip_y + 54), (x + col_w - 12, strip_y + 54)], fill=theme.dim, width=1)

        # Events list left-aligned
        ev_y = strip_y + 60
        ev_count = 0
        max_ev = 8

        # Collect events
        day_events = []
        for cal in day.get("calendars", []):
            cal_color = closest_panel_color(cal.get("color", [128, 128, 128]))
            for ev in cal.get("events", []):
                day_events.append((ev, cal_color))

        for ev, cal_color in day_events:
            if ev_y > strip_y + strip_h - 22:
                # Out of space indicator
                remaining = len(day_events) - ev_count
                draw.text((x + 8, strip_y + strip_h - 18), f"+{remaining} more", fill=theme.dim, font=font(11, bold=True))
                break

            summary = ev.get("summary", "")[:12]

            # Left Accent Dot
            draw.ellipse([(x + 8, ev_y + 6), (x + 14, ev_y + 12)], fill=cal_color)
            # Event Text
            draw.text((x + 18, ev_y + 3), summary, fill=theme.fg, font=font(11, bold=True))

            ev_y += 20
            ev_count += 1

    # FOOTER
    total = sum(len(c.get("events", [])) for d in days for c in d.get("calendars", []))
    draw.text((WIDTH - 24, HEIGHT - 20), f"{total} events this week", fill=theme.dim, font=font(14, bold=True), anchor="rm")


def render(payload: dict) -> Image.Image:
    theme_name = (payload.get("theme") or os.getenv("TRMNL_CALENDAR_THEME") or "dark").lower()
    layout = (payload.get("layout") or os.getenv("TRMNL_CALENDAR_LAYOUT") or "featured").lower()

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
