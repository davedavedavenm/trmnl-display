#!/usr/bin/env python3
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = Path(__file__).resolve().parent / "tmp"
OUT_PATH = OUT_DIR / "sidecar_bus_departures_next.png"
SOURCE_PATH = OUT_DIR / "sidecar_bus_departures_source_next.png"
WIDTH = 800
HEIGHT = 480

LARAPAPER_DB = "/var/www/html/database/storage/database.sqlite"
BUS_PLUGIN_ID = 11

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (204, 51, 51)      # High contrast red
YELLOW = (204, 204, 0)   # High contrast yellow
BLUE = (0, 102, 204)     # High contrast blue
GREEN = (0, 153, 76)     # High contrast green
ORANGE = (204, 102, 0)   # High contrast orange

SOFT_GREY = (235, 235, 235)
DARK_GREY = (80, 80, 80)
BG_COLOR = (248, 245, 237)    # Off-white background
BORDER_COLOR = (111, 111, 111) # Card borders
PANEL_PALETTE = [BLACK, WHITE, RED, YELLOW, BLUE, GREEN, ORANGE]

ROUTE_COLORS: dict[str, tuple] = {
    "70": BLUE,
    "74": GREEN,
    "75": ORANGE,
    "76": RED,
    "77": YELLOW,
    "1": (102, 51, 153),
    "2": (0, 153, 153),
    "3": (153, 102, 51),
    "4": (51, 102, 153),
    "5": (153, 51, 102),
}
NOT_ON_TIME_MINUTES = 2


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            pass
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except OSError:
        pass
    return ImageFont.load_default()


def load_data() -> dict:
    db_paths = [
        LARAPAPER_DB,
        str(Path.home() / "tmp" / "larapaper.sqlite"),
    ]
    for p in db_paths:
        if Path(p).exists():
            db = sqlite3.connect(p)
            row = db.execute("SELECT data_payload FROM plugins WHERE id = ?", (BUS_PLUGIN_ID,)).fetchone()
            db.close()
            if row and row[0]:
                payload = json.loads(row[0])
                if "merge_variables" in payload:
                    return payload["merge_variables"]
                return payload

    example_path = ROOT / "plugins" / "trmnl-bus-departures" / "payload.example.json"
    if example_path.exists():
        with open(example_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
            if "merge_variables" in payload:
                return payload["merge_variables"]
            return payload

    msg = "Could not find LaraPaper database or example payload."
    raise FileNotFoundError(msg)


def parse_time_minutes(t: str) -> int:
    parts = t.split(":")
    return int(parts[0]) * 60 + int(parts[1])


def minutes_diff(a: str, b: str) -> int:
    return abs(parse_time_minutes(a) - parse_time_minutes(b))


def route_color(line_name: str) -> tuple:
    return ROUTE_COLORS.get(line_name, DARK_GREY)


def render(data: dict) -> Image.Image:
    # Set base background to off-white
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    font_bus = font(30, bold=True)
    font_dest = font(26, bold=True)
    font_time = font(30, bold=True)
    font_header = font(18, bold=True)
    font_small = font(16)
    font_title = font(22, bold=True)
    font_status = font(24, bold=True)
    font_stop = font(28, bold=True)

    stop_name = data.get("stop_name") or data.get("name") or "Bus Stop"
    request_time = data.get("request_time", "")
    try:
        dt = datetime.fromisoformat(request_time)
        time_str = dt.strftime("%H:%M")
        date_str = dt.strftime("%d %b %Y")
    except (ValueError, TypeError):
        time_str = ""
        date_str = ""
        dt = datetime.now(timezone.utc)

    departures = (data.get("departures") or {}).get("all", [])
    if not departures:
        draw.text((WIDTH // 2, HEIGHT // 2), "No departures available", fill=BLACK, font=font_bus, anchor="mm")
        draw.text((WIDTH // 2, HEIGHT // 2 + 30), f"Last updated: {time_str} {date_str}", fill=DARK_GREY, font=font_small, anchor="mm")
        return img

    # Header section
    draw.text((20, 32), "Bus Departures", fill=BLACK, font=font_stop, anchor="lm")
    draw.text((WIDTH - 20, 22), stop_name, fill=DARK_GREY, font=font_small, anchor="rm")
    draw.text((WIDTH - 20, 46), time_str, fill=BLACK, font=font_title, anchor="rm")

    # Separator
    draw.line([(20, 64), (WIDTH - 20, 64)], fill=BORDER_COLOR, width=2)

    # Column headers
    col_y = 72
    COL_H = 28
    draw.text((32, col_y + COL_H // 2), "Route", fill=DARK_GREY, font=font_header, anchor="lm")
    draw.text((120, col_y + COL_H // 2), "Destination", fill=DARK_GREY, font=font_header, anchor="lm")
    draw.text((470, col_y + COL_H // 2), "Time", fill=DARK_GREY, font=font_header, anchor="lm")
    draw.text((610, col_y + COL_H // 2), "Status", fill=DARK_GREY, font=font_header, anchor="lm")

    row_y = col_y + COL_H + 4
    ROW_H = 82
    visible = departures[:4]

    for i, dep in enumerate(visible):
        line = dep.get("line_name", "?")
        direction = dep.get("direction", "")
        aimed = dep.get("aimed_departure_time", "")
        estimated = dep.get("best_departure_estimate", "")

        r_color = route_color(line)

        # Draw rounded card container
        card_box = [20, row_y, WIDTH - 20, row_y + 74]
        draw.rounded_rectangle(card_box, radius=8, fill=WHITE, outline=BORDER_COLOR, width=2)

        # Draw route badge on left
        badge_box = [32, row_y + 12, 102, row_y + 62]
        draw.rounded_rectangle(badge_box, radius=6, fill=r_color)
        draw.text(((32 + 102) // 2, (row_y + 12 + row_y + 62) // 2), line, fill=WHITE, font=font_bus, anchor="mm")

        # Draw destination
        draw.text((120, row_y + 37), direction, fill=BLACK, font=font_dest, anchor="lm")

        # Draw aimed time
        draw.text((470, row_y + 37), aimed, fill=BLACK, font=font_time, anchor="lm")

        # Status badge calculations
        if estimated and aimed:
            diff = minutes_diff(estimated, aimed)
            on_time = diff <= NOT_ON_TIME_MINUTES
            if on_time:
                status_text = "On time"
                status_fill = GREEN
            elif diff <= 10:
                status_text = f"{diff}m late"
                status_fill = ORANGE
            else:
                status_text = f"{diff}m late"
                status_fill = RED
        else:
            status_text = "--"
            status_fill = DARK_GREY

        sx, sy = 610, row_y + 15
        sw = draw.textlength(status_text, font=font_status) + 20
        sh = 44
        draw.rounded_rectangle([sx, sy, sx + sw, sy + sh], radius=6, fill=status_fill)
        draw.text((sx + sw // 2, sy + sh // 2), status_text, fill=WHITE, font=font_status, anchor="mm")

        row_y += ROW_H

    footer_y = HEIGHT - 20
    if len(departures) > 4:
        draw.text((WIDTH - 20, footer_y), f"Showing 4 of {len(departures)}", fill=DARK_GREY, font=font_small, anchor="rm")

    return img


def index_for_panel(img: Image.Image) -> Image.Image:
    palette_img = Image.new("P", (1, 1))
    flat = [c for rgb in PANEL_PALETTE for c in rgb]
    palette_img.putpalette(flat + [0] * (768 - len(flat)))
    return img.quantize(palette=palette_img, dither=Image.Dither.FLOYDSTEINBERG)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data = load_data()
    src = render(data)
    src.save(str(SOURCE_PATH), "PNG")
    panel = index_for_panel(src)
    panel.save(str(OUT_PATH), "PNG")
    print(f"Source: {SOURCE_PATH}")
    print(f"Panel:  {OUT_PATH}")
    print(f"Size:   {panel.size[0]} x {panel.size[1]}, mode={panel.mode}")


if __name__ == "__main__":
    main()
