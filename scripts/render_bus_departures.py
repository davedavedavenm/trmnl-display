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
RED = (255, 0, 0)
YELLOW = (255, 255, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
ORANGE = (255, 128, 0)

SOFT_GREY = (235, 235, 235)
SOFT_YELLOW = (255, 232, 96)
SOFT_GREEN = (170, 255, 170)
SOFT_RED = (255, 180, 180)
SOFT_BLUE = (160, 205, 255)
DARK_GREY = (80, 80, 80)
MED_GREY = (160, 160, 160)
PANEL_PALETTE = [BLACK, WHITE, RED, YELLOW, BLUE, GREEN, ORANGE]

ROUTE_COLORS: dict[str, tuple] = {
    "70": (0, 102, 204),
    "74": (0, 153, 76),
    "75": (204, 102, 0),
    "76": (204, 51, 51),
    "77": (204, 204, 0),
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
                return json.loads(row[0])
    msg = (
        "Could not find LaraPaper database. "
        "Run locally: cp the database.sqlite from the container to ~/tmp/larapaper.sqlite"
    )
    raise FileNotFoundError(msg)


def parse_time_minutes(t: str) -> int:
    parts = t.split(":")
    return int(parts[0]) * 60 + int(parts[1])


def minutes_diff(a: str, b: str) -> int:
    return abs(parse_time_minutes(a) - parse_time_minutes(b))


def route_color(line_name: str) -> tuple:
    return ROUTE_COLORS.get(line_name, (100, 100, 100))


def draw_rounded_rect(draw: ImageDraw, x1: int, y1: int, x2: int, y2: int, fill: tuple, radius: int = 6):
    draw.rounded_rectangle([x1, y1, x2, y2], radius=radius, fill=fill)


def render(data: dict) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT), BLACK)
    draw = ImageDraw.Draw(img)

    font_bus = font(46, bold=True)
    font_dest = font(32)
    font_time = font(36, bold=True)
    font_header = font(20, bold=True)
    font_small = font(16)
    font_title = font(22, bold=True)
    font_status = font(28, bold=True)
    font_stop = font(32, bold=True)

    stop_name = data.get("name", "Bus Stop")
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
        draw.text((WIDTH // 2, HEIGHT // 2), "No departures available", fill=WHITE, font=font_bus, anchor="mm")
        draw.text((WIDTH // 2, HEIGHT // 2 + 30), f"Last updated: {time_str} {date_str}", fill=WHITE, font=font_small, anchor="mm")
        return img

    HEADER_H = 60
    draw.rectangle([(0, 0), (WIDTH, HEADER_H)], fill=BLACK)
    draw.text((20, HEADER_H // 2), f"Bus Departures", fill=WHITE, font=font_stop, anchor="lm")
    draw.text((WIDTH - 20, HEADER_H // 2 - 8), time_str, fill=WHITE, font=font_title, anchor="rm")
    draw.text((WIDTH - 20, HEADER_H // 2 + 14), stop_name, fill=WHITE, font=font_small, anchor="rm")

    COL_H = 38
    col_y = HEADER_H + 8
    draw.text((24, col_y + COL_H // 2), "Route", fill=WHITE, font=font_header, anchor="lm")
    draw.text((130, col_y + COL_H // 2), "Destination", fill=WHITE, font=font_header, anchor="lm")
    draw.text((470, col_y + COL_H // 2), "Time", fill=WHITE, font=font_header, anchor="lm")
    draw.text((610, col_y + COL_H // 2), "Status", fill=WHITE, font=font_header, anchor="lm")

    row_y = col_y + COL_H
    ROW_H = 78
    visible = departures[:4]

    for i, dep in enumerate(visible):
        line = dep.get("line_name", "?")
        direction = dep.get("direction", "")
        aimed = dep.get("aimed_departure_time", "")
        estimated = dep.get("best_departure_estimate", "")

        r_color = route_color(line)

        draw.rectangle([(0, row_y), (12, row_y + ROW_H)], fill=r_color)

        draw.text((28, row_y + ROW_H // 2), line, fill=WHITE, font=font_bus, anchor="lm")

        draw.text((130, row_y + ROW_H // 2), direction, fill=WHITE, font=font_dest, anchor="lm")

        draw.text((470, row_y + ROW_H // 2), aimed, fill=WHITE, font=font_time, anchor="lm")

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
            status_fill = (80, 80, 80)

        sx, sy = 610, row_y + 8
        sw = draw.textlength(status_text, font=font_status) + 20
        sh = ROW_H - 16
        draw_rounded_rect(draw, sx, sy, sx + sw, sy + sh, status_fill)
        draw.text((sx + sw // 2, sy + sh // 2), status_text, fill=WHITE, font=font_status, anchor="mm")

        row_y += ROW_H

    footer_y = max(row_y + 4, HEIGHT - 20)
    if len(departures) > 4:
        draw.text((WIDTH - 20, footer_y), f"Showing 4 of {len(departures)}", fill=WHITE, font=font_small, anchor="rm")

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
