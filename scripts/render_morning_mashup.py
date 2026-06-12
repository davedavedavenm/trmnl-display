#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import random
import sqlite3
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_DIR = ROOT / "plugins" / "trmnl-jen-morning"
HP_PLUGIN_DIR = ROOT / "plugins" / "trmnl-hp-quotes"
QUOTES_PATH = HP_PLUGIN_DIR / "quotes.json"
DEFAULT_PAYLOAD = PLUGIN_DIR / "payload.example.json"
OUT_DIR = Path(__file__).resolve().parent / "tmp"
OUT_PATH = OUT_DIR / "sidecar_morning_mashup_next.png"
SOURCE_PATH = OUT_DIR / "sidecar_morning_mashup_source_next.png"
WIDTH = 800
HEIGHT = 480

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
ORANGE = (255, 128, 0)

HOUSE = {
    "gryffindor": {
        "primary": (116, 0, 1),
        "primary_dark": (60, 0, 0),
        "secondary": (206, 158, 26),
        "secondary_light": (230, 190, 60),
        "bg": (30, 10, 5),
        "text": (240, 235, 220)
    },
    "slytherin": {
        "primary": (26, 71, 42),
        "primary_dark": (12, 35, 20),
        "secondary": (170, 170, 170),
        "secondary_light": (200, 200, 200),
        "bg": (10, 20, 12),
        "text": (230, 235, 225)
    },
    "ravenclaw": {
        "primary": (14, 26, 62),
        "primary_dark": (6, 12, 30),
        "secondary": (142, 101, 46),
        "secondary_light": (180, 130, 60),
        "bg": (8, 14, 35),
        "text": (235, 230, 215)
    },
    "hufflepuff": {
        "primary": (236, 187, 45),
        "primary_dark": (180, 140, 20),
        "secondary": (30, 30, 30),
        "secondary_light": (60, 60, 60),
        "bg": (25, 22, 10),
        "text": (240, 235, 220)
    },
}
HOUSE_LABELS = {
    "gryffindor": "Gryffindor",
    "slytherin": "Slytherin",
    "ravenclaw": "Ravenclaw",
    "hufflepuff": "Hufflepuff"
}

PANEL_PALETTE = [BLACK, WHITE, RED, YELLOW, BLUE, GREEN, ORANGE]


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


def font_sans(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    return font(size, bold)


def load_quotes() -> list[dict[str, Any]]:
    base_dir = Path(__file__).resolve().parent
    paths = [
        base_dir / "quotes.json",
        base_dir.parent / "plugins" / "trmnl-hp-quotes" / "quotes.json",
        Path("/home/dave/trmnl-display-scripts/quotes.json"),
    ]
    for p in paths:
        if p.exists():
            with p.open("r", encoding="utf-8") as f:
                return json.load(f)
    raise FileNotFoundError("Could not find quotes.json in search paths.")


def pick_random_quote(quotes: list[dict[str, Any]]) -> dict[str, Any]:
    return random.choice(quotes)


def load_payload(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    if isinstance(raw, dict) and isinstance(raw.get("merge_variables"), dict):
        return raw["merge_variables"]
    if isinstance(raw, dict):
        return raw
    return {}


def load_data_from_db() -> tuple[dict[str, Any], dict[str, Any], int]:
    db_paths = [
        "/var/www/html/database/storage/database.sqlite",
        str(Path.home() / "tmp" / "larapaper.sqlite"),
    ]
    data = {}
    config = {}
    dark_mode = 0
    for p in db_paths:
        if Path(p).exists():
            try:
                db = sqlite3.connect(p)
                cursor = db.cursor()
                row = cursor.execute("SELECT data_payload, configuration, dark_mode FROM plugins WHERE id = 24").fetchone()
                db.close()
                if row:
                    raw_payload, raw_config, dark_val = row
                    if raw_payload:
                        payload_data = json.loads(raw_payload)
                        if "merge_variables" in payload_data:
                            data = payload_data["merge_variables"]
                        else:
                            data = payload_data
                    if raw_config:
                        config = json.loads(raw_config)
                    dark_mode = dark_val
                    break
            except Exception as e:
                print(f"Error loading from DB {p}: {e}")

    if not data:
        try:
            with DEFAULT_PAYLOAD.open("r", encoding="utf-8") as f:
                raw = json.load(f)
                data = raw.get("merge_variables", raw)
        except Exception:
            data = {}

    return data, config, dark_mode


def wrap_text(text: str, font_obj: ImageFont.FreeTypeFont | ImageFont.ImageFont, max_width: int, draw: ImageDraw.ImageDraw) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current_line = ""
    for word in words:
        test_line = current_line + (" " if current_line else "") + word
        bbox = draw.textbbox((0, 0), test_line, font=font_obj)
        if bbox[2] - bbox[0] <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    return lines


# ==========================================
# DRAWING HELPERS FOR PREMIUM LOOK
# ==========================================

def draw_clock_icon(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, color: tuple) -> None:
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=color, width=2)
    draw.ellipse((cx - 2, cy - 2, cx + 2, cy + 2), fill=color)
    draw.line((cx, cy, cx, cy - r + 3), fill=color, width=2)
    draw.line((cx, cy, cx + r - 4, cy), fill=color, width=2)


def draw_pin_icon(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, color: tuple) -> None:
    draw.ellipse((cx - r, cy - r - 2, cx + r, cy + r - 2), fill=color)
    draw.polygon([(cx - r + 1, cy - 1), (cx, cy + r + 2), (cx + r - 1, cy - 1)], fill=color)
    draw.ellipse((cx - r // 3, cy - r - 2 + r // 3, cx + r // 3, cy - r - 2 + r // 3 * 3), fill=WHITE)


def draw_alert_icon(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, color: tuple) -> None:
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=color)
    draw.line((cx - r + 4, cy, cx - 1, cy + r - 4), fill=WHITE, width=2)
    draw.line((cx - 1, cy + r - 4, cx + r - 3, cy - r + 4), fill=WHITE, width=2)


def draw_route_diagram(draw: ImageDraw.ImageDraw, x0: int, y: int, w: int, color: tuple, secondary_color: tuple) -> None:
    draw.line((x0, y, x0 + w, y), fill=(210, 210, 210), width=2)
    draw.ellipse((x0 - 5, y - 5, x0 + 5, y + 5), fill=color, outline=BLACK, width=1)
    draw.ellipse((x0 + w - 5, y - 5, x0 + w + 5, y + 5), fill=secondary_color, outline=BLACK, width=1)

    # Draw a cute little car at 45% along the way
    car_x = x0 + int(w * 0.45)
    # Wheels
    draw.ellipse((car_x - 8, y + 3, car_x - 4, y + 7), fill=BLACK)
    draw.ellipse((car_x + 4, y + 3, car_x + 8, y + 7), fill=BLACK)
    # Car body (horizontal pill)
    draw.rounded_rectangle([(car_x - 12, y - 4), (car_x + 12, y + 3)], radius=2, fill=color, outline=BLACK, width=1)
    # Car cabin (top part)
    draw.rounded_rectangle([(car_x - 6, y - 8), (car_x + 6, y - 3)], radius=1, fill=color, outline=BLACK, width=1)


def draw_corner_ornaments(draw: ImageDraw.ImageDraw, box: tuple, size: int, color: tuple) -> None:
    x0, y0, x1, y1 = box
    # Top-left
    draw.line([(x0, y0), (x0 + size, y0)], fill=color, width=2)
    draw.line([(x0, y0), (x0, y0 + size)], fill=color, width=2)
    # Top-right
    draw.line([(x1, y0), (x1 - size, y0)], fill=color, width=2)
    draw.line([(x1, y0), (x1, y0 + size)], fill=color, width=2)
    # Bottom-left
    draw.line([(x0, y1), (x0 + size, y1)], fill=color, width=2)
    draw.line([(x0, y1), (x0, y1 - size)], fill=color, width=2)
    # Bottom-right
    draw.line([(x1, y1), (x1 - size, y1)], fill=color, width=2)
    draw.line([(x1, y1), (x1, y1 - size)], fill=color, width=2)


def draw_shield_watermark(draw: ImageDraw.ImageDraw, cx: int, cy: int, w: int, h: int, color: tuple, dark_mode: int) -> None:
    sx = cx - w // 2
    sy = cy - h // 2
    pts = [
        (sx, sy),
        (sx + w, sy),
        (sx + w, sy + h * 0.55),
        (cx, sy + h),
        (sx, sy + h * 0.55),
    ]
    draw.polygon(pts, fill=color)
    line_color = BLACK if dark_mode == 1 else WHITE
    draw.line([(cx, sy), (cx, sy + h)], fill=line_color, width=1)
    draw.line([(sx, cy), (sx + w, cy)], fill=line_color, width=1)


def draw_star(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, color: tuple) -> None:
    points = []
    for i in range(8):
        angle = i * math.pi / 4 - math.pi / 2
        dist = r if i % 2 == 0 else r // 2
        points.append((cx + dist * math.cos(angle), cy + dist * math.sin(angle)))
    draw.polygon(points, fill=color)


def draw_house_stripes(draw: ImageDraw.ImageDraw, start_x: int, y: int, width: int, house: str) -> None:
    if house == "gryffindor":
        colors = [RED, YELLOW, RED, YELLOW, RED, YELLOW, RED, YELLOW, RED]
    elif house == "slytherin":
        colors = [GREEN, WHITE, GREEN, WHITE, GREEN, WHITE, GREEN, WHITE, GREEN]
    elif house == "ravenclaw":
        colors = [BLUE, ORANGE, BLUE, ORANGE, BLUE, ORANGE, BLUE, ORANGE, BLUE]
    elif house == "hufflepuff":
        colors = [YELLOW, BLACK, YELLOW, BLACK, YELLOW, BLACK, YELLOW, BLACK, YELLOW]
    else:
        colors = [BLACK, WHITE, BLACK, WHITE, BLACK, WHITE, BLACK, WHITE, BLACK]

    stripe_w = width // len(colors)
    for i, col in enumerate(colors):
        x0 = start_x + i * stripe_w
        x1 = x0 + stripe_w
        if i == len(colors) - 1:
            x1 = start_x + width
        draw.rectangle([x0, y, x1, y + 4], fill=closest_panel_color(col))


# ==========================================
# MAIN PANEL RENDERERS
# ==========================================

def draw_swiss_typographic(draw: ImageDraw.ImageDraw, data: dict[str, Any], config: dict[str, Any], dark_mode: int, colors_dict: dict) -> None:
    fg_prim = colors_dict["fg_primary"]
    fg_sec = colors_dict["fg_secondary"]
    theme_col = colors_dict["theme_color"]
    div_col = colors_dict["divider_color"]
    traffic_bg = colors_dict["pill_bg"]
    traffic_txt = colors_dict["traffic_text"]
    sub_txt = colors_dict["sub_text"]

    # 1. Clean uppercase subtitle
    draw.text((24, 28), "01 / OUTBOUND TRANSIT", fill=closest_panel_color(fg_sec), font=font(10, bold=True))

    # 2. Main route path in bold
    route = data.get("route_label") or "Direct"
    draw.text((24, 44), f"HOME -> OFFICE via {route.upper()}", fill=closest_panel_color(theme_col), font=font(15, bold=True))

    # Thin divider
    draw.line([(24, 68), (WIDTH // 2 - 24, 68)], fill=closest_panel_color(div_col), width=1)

    # 3. Huge ETA Display
    eta = data.get("eta_minutes") or "?"
    eta_str = str(eta)
    eta_font = font(110, bold=True)
    draw.text((24, 76), eta_str, fill=closest_panel_color(fg_prim), font=eta_font)
    eta_w = int(draw.textlength(eta_str, font=eta_font))

    # Stacked label next to ETA
    draw.text((24 + eta_w + 12, 116), "MINUTES", fill=closest_panel_color(fg_prim), font=font(18, bold=True))
    draw.text((24 + eta_w + 12, 138), "ESTIMATED DRIVE", fill=closest_panel_color(fg_sec), font=font(9, bold=True))

    # 4. Bold color bar for traffic alert
    bar_y = 210
    draw.rectangle([24, bar_y, WIDTH // 2 - 24, bar_y + 6], fill=closest_panel_color(traffic_bg))

    # Traffic text
    draw.text((24, bar_y + 16), traffic_txt, fill=closest_panel_color(traffic_bg), font=font(13, bold=True))
    draw.text((24, bar_y + 34), sub_txt.upper(), fill=closest_panel_color(fg_prim), font=font(10, bold=True))

    # 5. Leave By section
    leave_y = 285
    draw.line([(24, leave_y), (WIDTH // 2 - 24, leave_y)], fill=closest_panel_color(div_col), width=1)

    draw.text((24, leave_y + 16), "DEPARTURE TARGET", fill=closest_panel_color(fg_sec), font=font(9, bold=True))
    leave_time = data.get("leave_by") or config.get("leave_by") or "7:15 AM"
    draw.text((24, leave_y + 32), f"LEAVE BY {leave_time}", fill=closest_panel_color(fg_prim), font=font(32, bold=True))

    # 6. Bottom footer
    footer_y = 390
    draw.line([(24, footer_y), (WIDTH // 2 - 24, footer_y)], fill=closest_panel_color(div_col), width=1)

    dist_txt = f"{data.get('distance_km')} KM DISTANCE" if data.get("distance_km") else "DISTANCE N/A"
    draw.text((24, footer_y + 16), dist_txt, fill=closest_panel_color(fg_prim), font=font(11, bold=True))
    arrive_by = config.get("arrive_by") or "8:30 AM"
    draw.text((WIDTH // 2 - 24, footer_y + 16), f"ARRIVE {arrive_by}", fill=closest_panel_color(fg_sec), font=font(11, bold=True), anchor="ra")


def draw_infographic_timeline(draw: ImageDraw.ImageDraw, data: dict[str, Any], config: dict[str, Any], dark_mode: int, colors_dict: dict) -> None:
    fg_prim = colors_dict["fg_primary"]
    fg_sec = colors_dict["fg_secondary"]
    theme_col = colors_dict["theme_color"]
    traffic_bg = colors_dict["pill_bg"]
    traffic_txt = colors_dict["traffic_text"]

    timeline_x = 60
    start_y = 90
    end_y = 390
    mid_y = start_y + (end_y - start_y) // 2

    # Header
    draw.text((24, 24), "COMMUTE ROADMAP", fill=closest_panel_color(fg_sec), font=font(10, bold=True))

    # Target Leave time box in top right
    leave_time = data.get("leave_by") or config.get("leave_by") or "7:15 AM"
    draw.text((WIDTH // 2 - 24, 24), f"LEAVE BY {leave_time}", fill=closest_panel_color(fg_prim), font=font(12, bold=True), anchor="ra")

    # Draw timeline base track
    draw.line([(timeline_x, start_y), (timeline_x, end_y)], fill=(225, 225, 225) if dark_mode == 0 else (45, 55, 65), width=8)

    # Highlight segment based on traffic
    draw.line([(timeline_x, start_y), (timeline_x, mid_y)], fill=closest_panel_color(GREEN), width=8)
    draw.line([(timeline_x, mid_y), (timeline_x, mid_y + 50)], fill=closest_panel_color(traffic_bg), width=8)

    # Station 1: HOME (Start)
    draw.ellipse((timeline_x - 10, start_y - 10, timeline_x + 10, start_y + 10), fill=closest_panel_color(theme_col), outline=closest_panel_color(fg_prim), width=2)
    draw.text((timeline_x + 20, start_y - 6), "HOME", fill=closest_panel_color(fg_prim), font=font(12, bold=True))

    # Station 2: TRAFFIC POINT (Middle)
    draw.ellipse((timeline_x - 10, mid_y + 25 - 10, timeline_x + 10, mid_y + 25 + 10), fill=closest_panel_color(traffic_bg), outline=closest_panel_color(fg_prim), width=2)
    route = data.get("route_label") or "Direct"
    draw.text((timeline_x + 20, mid_y + 13), f"VIA {route.upper()}", fill=closest_panel_color(fg_prim), font=font(11, bold=True))
    draw.text((timeline_x + 20, mid_y + 27), traffic_txt, fill=closest_panel_color(traffic_bg), font=font(9, bold=True))

    # Station 3: OFFICE (End)
    draw.ellipse((timeline_x - 10, end_y - 10, timeline_x + 10, end_y + 10), fill=closest_panel_color(theme_col), outline=closest_panel_color(fg_prim), width=2)
    draw.text((timeline_x + 20, end_y - 6), "OFFICE", fill=closest_panel_color(fg_prim), font=font(12, bold=True))

    # Car marker representing current progress
    car_y = mid_y - 15
    draw.rounded_rectangle([(timeline_x - 12, car_y - 6), (timeline_x + 12, car_y + 6)], radius=2, fill=closest_panel_color(theme_col), outline=closest_panel_color(fg_prim), width=1)
    draw.ellipse((timeline_x - 8, car_y + 4, timeline_x - 5, car_y + 7), fill=closest_panel_color(fg_prim))
    draw.ellipse((timeline_x + 5, car_y + 4, timeline_x + 8, car_y + 7), fill=closest_panel_color(fg_prim))

    # Large floating ETA box on the right half
    eta_x = 240
    eta_y = 150
    draw.text((eta_x, eta_y), "DRIVE TIME", fill=closest_panel_color(fg_sec), font=font(10, bold=True))

    eta = data.get("eta_minutes") or "?"
    draw.text((eta_x, eta_y + 12), str(eta), fill=closest_panel_color(fg_prim), font=font(64, bold=True))
    eta_w = int(draw.textlength(str(eta), font=font(64, bold=True)))
    draw.text((eta_x + eta_w + 6, eta_y + 54), "MINS", fill=closest_panel_color(fg_sec), font=font(14, bold=True))

    # Sub-detail: distance and arrive_by
    dist = f"{data.get('distance_km')} km" if data.get("distance_km") else "N/A"
    arrive_by = config.get("arrive_by") or "8:30 AM"
    draw.text((eta_x, eta_y + 88), f"Distance: {dist}", fill=closest_panel_color(fg_prim), font=font(11, bold=True))
    draw.text((eta_x, eta_y + 104), f"Arrive by: {arrive_by}", fill=closest_panel_color(fg_sec), font=font(11))

    # Traffic notice banner at the bottom
    draw.rectangle([24, HEIGHT - 46, WIDTH // 2 - 24, HEIGHT - 18], fill=closest_panel_color(colors_dict["banner_bg"]), outline=closest_panel_color(colors_dict["banner_outline"]), width=1)
    draw_alert_icon(draw, 40, HEIGHT - 32, 6, closest_panel_color(traffic_bg))
    draw.text((56, HEIGHT - 38), colors_dict["sub_text"].upper(), fill=closest_panel_color(fg_prim), font=font(9, bold=True))


def draw_bauhaus_geometric(draw: ImageDraw.ImageDraw, data: dict[str, Any], config: dict[str, Any], dark_mode: int, colors_dict: dict) -> None:
    fg_prim = colors_dict["fg_primary"]
    fg_sec = colors_dict["fg_secondary"]
    theme_col = colors_dict["theme_color"]
    traffic_bg = colors_dict["pill_bg"]
    traffic_txt = colors_dict["traffic_text"]

    # Bauhaus relies on thick shapes, color blocking, and geometric lines

    # 1. Left thick margin block in traffic color
    draw.rectangle([0, 0, 30, HEIGHT], fill=closest_panel_color(traffic_bg))

    # 2. Huge yellow circle for the morning target (Leave By / Sun)
    sun_x, sun_y = WIDTH // 2 - 90, 110
    sun_r = 70
    draw.ellipse((sun_x - sun_r, sun_y - sun_r, sun_x + sun_r, sun_y + sun_r), fill=closest_panel_color(YELLOW))

    leave_time = data.get("leave_by") or config.get("leave_by") or "7:15 AM"
    draw.text((sun_x, sun_y - 20), "LEAVE BY", fill=closest_panel_color(BLACK), font=font(9, bold=True), anchor="ma")
    draw.text((sun_x, sun_y - 6), leave_time, fill=closest_panel_color(BLACK), font=font(22, bold=True), anchor="ma")

    # 3. Blue/Dark quadrant block for the ETA (Bottom-Left)
    block_x, block_y = 120, 350
    block_r = 100
    draw.ellipse((block_x - block_r, block_y - block_r, block_x + block_r, block_y + block_r), fill=closest_panel_color(BLUE if dark_mode == 0 else (35, 45, 65)))

    eta = data.get("eta_minutes") or "?"
    draw.text((block_x, block_y - 40), "ETA", fill=closest_panel_color(WHITE), font=font(11, bold=True), anchor="ma")
    draw.text((block_x, block_y - 22), str(eta), fill=closest_panel_color(WHITE), font=font(64, bold=True), anchor="ma")
    draw.text((block_x, block_y + 40), "MINUTES", fill=closest_panel_color(YELLOW), font=font(11, bold=True), anchor="ma")

    # 4. Asymmetric diagonal path line crossing the canvas
    draw.line([(30, 220), (WIDTH // 2 - 30, 220)], fill=closest_panel_color(fg_prim), width=5)
    draw.line([(30, 220), (sun_x, sun_y)], fill=closest_panel_color(fg_prim), width=3)

    # 5. Metadata boxes
    # Top-Left text
    draw.text((45, 24), "COMMUTE REPORT", fill=closest_panel_color(fg_prim), font=font(14, bold=True))
    draw.text((45, 44), traffic_txt, fill=closest_panel_color(traffic_bg), font=font(11, bold=True))
    route = data.get("route_label") or "Direct"
    draw.text((45, 62), f"VIA {route.upper()}", fill=closest_panel_color(fg_sec), font=font(11, bold=True))

    # Bottom-Right text
    detail_x = WIDTH // 2 - 120
    detail_y = 270
    draw.text((detail_x, detail_y), "METRICS", fill=closest_panel_color(fg_sec), font=font(9, bold=True))

    dist = f"{data.get('distance_km')} KM" if data.get("distance_km") else "N/A"
    draw.text((detail_x, detail_y + 16), f"DIST: {dist}", fill=closest_panel_color(fg_prim), font=font(13, bold=True))
    arrive_by = config.get("arrive_by") or "8:30 AM"
    draw.text((detail_x, detail_y + 36), f"ARRV: {arrive_by}", fill=closest_panel_color(fg_prim), font=font(13, bold=True))

    # Text badge under the sun
    draw.text((sun_x, sun_y + sun_r + 8), colors_dict["sub_text"].upper(), fill=closest_panel_color(fg_prim), font=font(9, bold=True), anchor="ma")


def draw_automotive_hud(draw: ImageDraw.ImageDraw, data: dict[str, Any], config: dict[str, Any], dark_mode: int, colors_dict: dict) -> None:
    # Resolve high-contrast palette to prevent dithering noise
    if dark_mode == 1:
        fg_prim = WHITE
        fg_sec = YELLOW  # High contrast labels
        dial_bg = WHITE   # Solid white speedometer track background
        hud_bracket = YELLOW  # Solid yellow brackets
        div_c = YELLOW
    else:
        fg_prim = BLACK
        fg_sec = (100, 110, 120)
        dial_bg = (200, 200, 200)
        hud_bracket = colors_dict["theme_color"]
        div_c = colors_dict["divider_color"]

    traffic_bg = colors_dict["pill_bg"]
    traffic_txt = colors_dict["traffic_text"]

    # HUD uses high-tech telemetry graphics
    cx, cy = WIDTH // 4, 180
    r = 110

    # 1. HUD outer coordinates & brackets (using the full left panel space)
    draw_corner_ornaments(draw, (18, 18, WIDTH // 2 - 18, HEIGHT - 18), 15, closest_panel_color(hud_bracket))

    # 2. Speedometer-like Arch Dial (enlarged)
    xy = (cx - r, cy - r, cx + r, cy + r)
    draw.arc(xy, 135, 405, fill=closest_panel_color(dial_bg), width=3)

    eta = 0
    try:
        eta = int(data.get("eta_minutes") or 0)
    except ValueError:
        pass

    fill_pct = min(1.0, max(0.0, eta / 60.0))
    end_angle = 135 + int(270 * fill_pct)

    if fill_pct > 0:
        draw.arc(xy, 135, end_angle, fill=closest_panel_color(traffic_bg), width=12)

    # Dial labels & ticks
    draw.text((cx - 90, cy + 85), "0", fill=closest_panel_color(fg_sec), font=font(10, bold=True), anchor="ma")
    draw.text((cx + 90, cy + 85), "60+", fill=closest_panel_color(fg_sec), font=font(10, bold=True), anchor="ma")

    # Center digits (much larger ETA)
    draw.text((cx, cy - 35), str(eta or "?"), fill=closest_panel_color(fg_prim), font=font(72, bold=True), anchor="ma")
    draw.text((cx, cy + 40), "MINS", fill=closest_panel_color(fg_sec), font=font(14, bold=True), anchor="ma")

    # 3. Telemetry data readouts (Grid of 2 Rows x 2 Columns)
    lbl_font = font(11, bold=True)
    val_font = font(16, bold=True)

    col1_x = 42
    col2_x = 222
    row1_y = 315
    row2_y = 385

    # Row 1 Left: Route
    draw.text((col1_x, row1_y), "ROUTE", fill=closest_panel_color(fg_sec), font=lbl_font)
    route = data.get("route_label") or "Direct"
    draw.text((col1_x, row1_y + 18), route.upper(), fill=closest_panel_color(fg_prim), font=val_font)

    # Row 1 Right: Distance
    draw.text((col2_x, row1_y), "DISTANCE", fill=closest_panel_color(fg_sec), font=lbl_font)
    dist = f"{data.get('distance_km')} KM" if data.get("distance_km") else "N/A"
    draw.text((col2_x, row1_y + 18), dist, fill=closest_panel_color(fg_prim), font=val_font)

    # Row 2 Left: Leave By
    draw.text((col1_x, row2_y), "LEAVE BY", fill=closest_panel_color(fg_sec), font=lbl_font)
    leave_time = data.get("leave_by") or config.get("leave_by") or "7:15 AM"
    draw.text((col1_x, row2_y + 18), leave_time, fill=closest_panel_color(fg_prim), font=val_font)

    # Row 2 Right: Traffic
    draw.text((col2_x, row2_y), "TRAFFIC", fill=closest_panel_color(fg_sec), font=lbl_font)
    draw.text((col2_x, row2_y + 18), traffic_txt, fill=closest_panel_color(traffic_bg), font=val_font)


def draw_left_panel(draw: ImageDraw.ImageDraw, data: dict[str, Any], config: dict[str, Any], dark_mode: int) -> None:
    eta = data.get("eta_minutes") or "?"
    route = data.get("route_label") or "Direct"
    distance = data.get("distance_km")
    headline = data.get("headline") or config.get("headline_fallback") or "Time To Work"
    updated = data.get("updated_at") or ""
    screen_label = config.get("screen_label") or "Jen Morning"
    eta_lbl = config.get("eta_label") or "DRIVE TIME"
    eta_unit = config.get("eta_unit_label") or "min"
    show_dist = config.get("show_distance", True)
    dist_unit = config.get("distance_unit_label") or "km"

    if isinstance(show_dist, str):
        show_dist = show_dist.lower() == "true"

    profile = config.get("colour_profile", "navy_blue")
    style = config.get("style") or config.get("layout_variant") or "split_contrast"
    if data.get("style"):
        style = data.get("style")
    elif data.get("layout_variant"):
        style = data.get("layout_variant")

    # 1. Resolve Cohesive Theme Colors
    if dark_mode == 1 or style == "dark_tech" or style == "automotive_hud":
        # Dark mode (sleek dark blue-grey dashboard)
        fg_primary = WHITE
        fg_secondary = (140, 150, 160)

        if style == "swiss_typographic":
            bg_panel = (0, 0, 0)
            divider_color = (60, 60, 60)
        elif style == "bauhaus_geometric":
            bg_panel = (15, 20, 30)
            divider_color = (40, 50, 70)
        elif style == "automotive_hud":
            bg_panel = BLACK
            divider_color = BLUE
        elif style == "infographic_timeline":
            bg_panel = (18, 24, 32)
            divider_color = (35, 45, 55)
        else: # dark_tech
            bg_panel = (18, 24, 32)
            divider_color = (35, 45, 55)

        if profile == "forest":
            theme_color = GREEN
            secondary_accent = ORANGE
        elif profile == "slate":
            theme_color = WHITE
            secondary_accent = ORANGE
        else: # navy_blue
            theme_color = BLUE
            secondary_accent = ORANGE

        banner_bg = (28, 36, 48)
        banner_outline = divider_color
    else:
        # Light mode
        if profile == "forest":
            theme_color = GREEN
            secondary_accent = ORANGE
        elif profile == "slate":
            theme_color = BLACK
            secondary_accent = ORANGE
        else: # navy_blue
            theme_color = BLUE
            secondary_accent = ORANGE

        if style == "split_contrast":
            # Solid colored sidebar background with white widgets
            bg_panel = closest_panel_color(theme_color)
            divider_color = WHITE
            fg_primary = (18, 24, 32)
            fg_secondary = (100, 110, 120)
            banner_bg = WHITE
            banner_outline = theme_color
        elif style == "bento_grid":
            # Soft grey bento widgets page
            bg_panel = (240, 242, 245)
            divider_color = (210, 215, 220)
            fg_primary = (18, 24, 32)
            fg_secondary = (100, 110, 120)
            banner_bg = WHITE
            banner_outline = theme_color
        elif style == "swiss_typographic":
            bg_panel = (255, 255, 255)
            divider_color = (220, 220, 220)
            fg_primary = (18, 24, 32)
            fg_secondary = (100, 110, 120)
            banner_bg = (245, 245, 245)
            banner_outline = theme_color
        elif style == "infographic_timeline":
            bg_panel = (245, 247, 250)
            divider_color = (210, 215, 220)
            fg_primary = (18, 24, 32)
            fg_secondary = (100, 110, 120)
            banner_bg = WHITE
            banner_outline = theme_color
        elif style == "bauhaus_geometric":
            bg_panel = (248, 246, 240)
            divider_color = (210, 205, 195)
            fg_primary = (18, 24, 32)
            fg_secondary = (100, 110, 120)
            banner_bg = WHITE
            banner_outline = theme_color
        else:
            # Minimalist White Dashboard
            bg_panel = (250, 250, 250)
            divider_color = (230, 235, 240)
            fg_primary = (18, 24, 32)
            fg_secondary = (100, 110, 120)
            banner_bg = (242, 244, 248)
            banner_outline = theme_color

    # Resolve warning status traffic pill and banner subtext
    traffic_text = "LIGHT TRAFFIC"
    sub_text = "On-time arrival expected"

    eta_m = 0
    try:
        eta_m = int(eta)
    except ValueError:
        pass

    # Snap traffic pills to solid, undithered panel colors
    if eta_m > 55:
        traffic_text = "HEAVY TRAFFIC"
        sub_text = "Heavy traffic warning!"
        pill_bg = RED
        pill_fg = WHITE
    elif eta_m > 45:
        traffic_text = "MODERATE TRAFFIC"
        sub_text = "Caution: minor delay"
        pill_bg = ORANGE
        pill_fg = WHITE
    else:
        pill_bg = GREEN
        pill_fg = WHITE

    colors_dict = {
        "bg_panel": bg_panel,
        "divider_color": divider_color,
        "fg_primary": fg_primary,
        "fg_secondary": fg_secondary,
        "theme_color": theme_color,
        "secondary_accent": secondary_accent,
        "banner_bg": banner_bg,
        "banner_outline": banner_outline,
        "pill_bg": pill_bg,
        "pill_fg": pill_fg,
        "traffic_text": traffic_text,
        "sub_text": sub_text,
    }

    # 2. Draw Sidebar Background
    draw.rectangle([0, 0, WIDTH // 2, HEIGHT], fill=bg_panel)

    # 3. Dispatch to Specific Style Renderer
    if style == "swiss_typographic":
        draw_swiss_typographic(draw, data, config, dark_mode, colors_dict)
    elif style == "infographic_timeline":
        draw_infographic_timeline(draw, data, config, dark_mode, colors_dict)
    elif style == "bauhaus_geometric":
        draw_bauhaus_geometric(draw, data, config, dark_mode, colors_dict)
    elif style == "automotive_hud":
        draw_automotive_hud(draw, data, config, dark_mode, colors_dict)
    elif style == "split_contrast":
        card_border = WHITE

        # Card 1 (ETA)
        card1_y0, card1_y1 = 62, 182
        draw.rounded_rectangle([(18, card1_y0), (WIDTH // 2 - 18, card1_y1)], radius=10, fill=WHITE, outline=closest_panel_color(card_border), width=2)
        draw.rounded_rectangle([(20, card1_y0 + 2), (28, card1_y1 - 2)], radius=3, fill=closest_panel_color(theme_color))

        draw_clock_icon(draw, 44, card1_y0 + 18, 7, closest_panel_color(fg_secondary))
        lbl_font = font(12, bold=True)
        draw.text((58, card1_y0 + 11), eta_lbl.upper(), fill=closest_panel_color(fg_secondary), font=lbl_font)

        eta_font = font(54, bold=True)
        eta_str = str(eta)
        draw.text((44, card1_y0 + 36), eta_str, fill=closest_panel_color(fg_primary), font=eta_font)
        eta_w = int(draw.textlength(eta_str, font=eta_font))

        unit_font = font(18, bold=True)
        draw.text((44 + eta_w + 6, card1_y0 + 64), eta_unit, fill=closest_panel_color(fg_secondary), font=unit_font)

        pill_font = font(10, bold=True)
        pill_w = int(draw.textlength(traffic_text, font=pill_font)) + 16
        pill_x0, pill_y0 = 382 - 20 - pill_w, card1_y0 + 44
        draw.rounded_rectangle([(pill_x0, pill_y0), (pill_x0 + pill_w, pill_y0 + 24)], radius=6, fill=closest_panel_color(pill_bg))
        draw.text((pill_x0 + 8, pill_y0 + 5), traffic_text, fill=closest_panel_color(pill_fg), font=pill_font)

        # Card 2 (Route Card)
        card2_y0, card2_y1 = 196, 326
        draw.rounded_rectangle([(18, card2_y0), (WIDTH // 2 - 18, card2_y1)], radius=10, fill=WHITE, outline=closest_panel_color(card_border), width=2)
        draw.rounded_rectangle([(20, card2_y0 + 2), (28, card2_y1 - 2)], radius=3, fill=closest_panel_color(secondary_accent))

        draw_pin_icon(draw, 44, card2_y0 + 18, 6, closest_panel_color(fg_secondary))
        draw.text((58, card2_y0 + 11), "OPTIMAL ROUTE", fill=closest_panel_color(fg_secondary), font=lbl_font)

        route_text = f"via {route}"
        if len(route_text) > 28:
            route_text = route_text[:25] + "..."
        route_font = font(16 if len(route_text) > 22 else 20, bold=True)
        draw.text((44, card2_y0 + 32), route_text, fill=closest_panel_color(fg_primary), font=route_font)

        if show_dist and distance is not None and str(distance).strip() not in ("", "?", "unknown"):
            dist_text = f"{distance} {dist_unit}"
            dist_font = font(13, bold=True)
            draw.text((44, card2_y0 + 58), dist_text, fill=closest_panel_color(fg_secondary), font=dist_font)

        draw_route_diagram(draw, 44, card2_y0 + 96, 310, closest_panel_color(theme_color), closest_panel_color(secondary_accent))

        # Card 3 (Action Card)
        card3_y0, card3_y1 = 340, 464
        draw.rounded_rectangle([(18, card3_y0), (WIDTH // 2 - 18, card3_y1)], radius=10, fill=WHITE, outline=closest_panel_color(card_border), width=2)

        status_action_bg = RED if eta_m > 55 else (ORANGE if eta_m > 45 else theme_color)
        status_action_fg = WHITE
        draw.rounded_rectangle([(20, card3_y0 + 2), (28, card3_y1 - 2)], radius=3, fill=closest_panel_color(status_action_bg))

        draw_alert_icon(draw, 44, card3_y0 + 18, 7, closest_panel_color(status_action_bg))
        draw.text((58, card3_y0 + 11), "RECOMMENDED ACTION", fill=closest_panel_color(fg_secondary), font=lbl_font)

        leave_time = data.get("leave_by") or config.get("leave_by") or "7:15 AM"
        status_text = f"LEAVE BY {leave_time}"
        status_font = font(18, bold=True)
        draw.text((44, card3_y0 + 32), status_text, fill=closest_panel_color(fg_primary), font=status_font)

        s_font = font(12, bold=True)
        s_w = int(draw.textlength(sub_text, font=s_font))
        s_badge_x0 = 44
        s_badge_y0 = card3_y0 + 62

        draw.rounded_rectangle([(s_badge_x0, s_badge_y0), (s_badge_x0 + s_w + 20, s_badge_y0 + 24)], radius=6, fill=closest_panel_color(status_action_bg))
        draw.text((s_badge_x0 + 10, s_badge_y0 + 4), sub_text, fill=closest_panel_color(status_action_fg), font=s_font)

    elif style == "bento_grid":
        card_border = WHITE

        # Quadrant 1 (top-left, Drive Time)
        draw.rounded_rectangle([(18, 62), (194, 236)], radius=10, fill=WHITE, outline=closest_panel_color(card_border), width=2)
        lbl_font = font(10, bold=True)
        draw.text((30, 72), "DRIVE TIME", fill=closest_panel_color(fg_secondary), font=lbl_font)

        eta_font = font(48, bold=True)
        eta_str = str(eta)
        draw.text((30, 92), eta_str, fill=closest_panel_color(fg_primary), font=eta_font)
        eta_w = int(draw.textlength(eta_str, font=eta_font))

        unit_font = font(16, bold=True)
        draw.text((30 + eta_w + 4, 120), eta_unit, fill=closest_panel_color(fg_secondary), font=unit_font)

        pill_font = font(9, bold=True)
        pill_w = int(draw.textlength(traffic_text, font=pill_font)) + 12
        pill_x0, pill_y0 = 30, 196
        draw.rounded_rectangle([(pill_x0, pill_y0), (pill_x0 + pill_w, pill_y0 + 22)], radius=5, fill=closest_panel_color(pill_bg))
        draw.text((pill_x0 + 6, pill_y0 + 4), traffic_text, fill=closest_panel_color(pill_fg), font=pill_font)

        # Quadrant 2 (top-right, Leave By)
        draw.rounded_rectangle([(206, 62), (382, 236)], radius=10, fill=WHITE, outline=closest_panel_color(card_border), width=2)
        draw.text((218, 72), "LEAVE BY", fill=closest_panel_color(fg_secondary), font=lbl_font)

        leave_font = font(26, bold=True)
        leave_time = data.get("leave_by") or config.get("leave_by") or "7:15 AM"
        draw.text((218, 102), leave_time, fill=closest_panel_color(fg_primary), font=leave_font)

        arrive_by = config.get("arrive_by") or "8:30 AM"
        arrive_sub = f"to arrive by {arrive_by}"
        draw.text((218, 196), arrive_sub, fill=closest_panel_color(fg_secondary), font=font(11, bold=True))

        # Quadrant 3 (bottom-left, Best Route)
        draw.rounded_rectangle([(18, 248), (382, 386)], radius=10, fill=WHITE, outline=closest_panel_color(card_border), width=2)
        draw.text((30, 258), "BEST ROUTE", fill=closest_panel_color(fg_secondary), font=lbl_font)

        route_font = font(15, bold=True)
        route_full = f"via {route}"
        if show_dist and distance is not None and str(distance).strip() not in ("", "?", "unknown"):
            route_full += f" · {distance} {dist_unit}"
        draw.text((30, 272), route_full, fill=closest_panel_color(fg_primary), font=route_font)

        draw_route_diagram(draw, 44, 336, 310, closest_panel_color(theme_color), closest_panel_color(secondary_accent))

        # Quadrant 4 (bottom action banner)
        banner_y0, banner_y1 = 398, 464
        draw.rounded_rectangle([(18, banner_y0), (382, banner_y1)], radius=10, fill=WHITE, outline=closest_panel_color(banner_outline), width=1)

        alert_color = pill_bg
        draw_alert_icon(draw, 38, banner_y0 + 26, 7, closest_panel_color(alert_color))

        banner_text_font = font(12, bold=True)
        draw.text((56, banner_y0 + 19), sub_text.upper(), fill=closest_panel_color(fg_primary), font=banner_text_font)

    else:
        # minimalist / default
        path_lbl_font = font(10, bold=True)
        draw.text((18, 62), "YOUR COMMUTE", fill=closest_panel_color(fg_secondary), font=path_lbl_font)

        path_font = font(18, bold=True)
        home_w = int(draw.textlength("Home ", font=path_font))
        arrow_w = int(draw.textlength("-> ", font=path_font))

        draw.text((18, 76), "Home ", fill=closest_panel_color(fg_primary), font=path_font)
        draw.text((18 + home_w, 76), "-> ", fill=closest_panel_color(theme_color), font=path_font)
        draw.text((18 + home_w + arrow_w, 76), "Office", fill=closest_panel_color(fg_primary), font=path_font)

        draw.line([(18, 110), (WIDTH // 2 - 18, 110)], fill=closest_panel_color(divider_color), width=1)

        lbl_font = font(10, bold=True)
        draw.text((18, 122), eta_lbl.upper(), fill=closest_panel_color(fg_secondary), font=lbl_font)

        eta_font = font(58, bold=True)
        eta_str = str(eta)
        draw.text((18, 138), eta_str, fill=closest_panel_color(fg_primary), font=eta_font)
        eta_w = int(draw.textlength(eta_str, font=eta_font))

        unit_font = font(18, bold=True)
        draw.text((18 + eta_w + 6, 172), eta_unit, fill=closest_panel_color(fg_secondary), font=unit_font)

        pill_font = font(10, bold=True)
        pill_w = int(draw.textlength(traffic_text, font=pill_font)) + 16
        pill_x0, pill_y0 = 18, 202
        draw.rounded_rectangle([(pill_x0, pill_y0), (pill_x0 + pill_w, pill_y0 + 24)], radius=6, fill=closest_panel_color(pill_bg))
        draw.text((pill_x0 + 8, pill_y0 + 5), traffic_text, fill=closest_panel_color(pill_fg), font=pill_font)

        draw.text((210, 122), "LEAVE BY", fill=closest_panel_color(fg_secondary), font=lbl_font)

        leave_font = font(36, bold=True)
        leave_time = data.get("leave_by") or config.get("leave_by") or "7:15 AM"
        draw.text((210, 142), leave_time, fill=closest_panel_color(fg_primary), font=leave_font)

        arrive_by = config.get("arrive_by") or "8:30 AM"
        arrive_sub = f"to arrive by {arrive_by}"
        draw.text((210, 204), arrive_sub, fill=closest_panel_color(fg_secondary), font=font(12, bold=True))

        draw.line([(18, 246), (WIDTH // 2 - 18, 246)], fill=closest_panel_color(divider_color), width=1)

        draw.text((18, 258), "BEST ROUTE", fill=closest_panel_color(fg_secondary), font=lbl_font)

        route_font = font(15, bold=True)
        route_full = f"via {route}"
        if show_dist and distance is not None and str(distance).strip() not in ("", "?", "unknown"):
            route_full += f" · {distance} {dist_unit}"
        draw.text((18, 272), route_full, fill=closest_panel_color(fg_primary), font=route_font)

        draw_route_diagram(draw, 44, 336, 310, closest_panel_color(theme_color), closest_panel_color(secondary_accent))

        draw.line([(18, 396), (WIDTH // 2 - 18, 396)], fill=closest_panel_color(divider_color), width=1)

        banner_y0, banner_y1 = 412, 464
        draw.rounded_rectangle([(18, banner_y0), (WIDTH // 2 - 18, banner_y1)], radius=8, fill=closest_panel_color(banner_bg), outline=closest_panel_color(banner_outline), width=1)

        alert_color = pill_bg
        draw_alert_icon(draw, 38, banner_y0 + 26, 7, closest_panel_color(alert_color))

        banner_text_font = font(12, bold=True)
        draw.text((56, banner_y0 + 19), sub_text.upper(), fill=closest_panel_color(fg_primary), font=banner_text_font)


def draw_hp_quote_card(draw: ImageDraw.ImageDraw, quote_text: str, character: str, book: str | None, house: str | None, show_book: bool, dark_mode: int) -> None:
    h = HOUSE.get(house, HOUSE["gryffindor"]) if house else HOUSE["gryffindor"]
    start_x = WIDTH // 2

    if dark_mode == 1:
        bg_color = h["bg"]
        quote_color = h["text"]
        accent_color = h["secondary"]
        banner_bg = h["primary"]
        banner_fg = h["secondary"]
        watermark_color = (bg_color[0] + 8, bg_color[1] + 8, bg_color[2] + 8)
    else:
        bg_color = WHITE  # Pure white background to eliminate any quantization noise
        quote_color = BLACK  # Pure black ink for maximum contrast
        watermark_color = WHITE  # Invisible watermark to avoid dither noise

        # Map house names to vibrant panel colors for light mode
        if house == "gryffindor":
            banner_bg = RED
            banner_fg = YELLOW
            accent_color = RED
        elif house == "slytherin":
            banner_bg = GREEN
            banner_fg = WHITE
            accent_color = GREEN
        elif house == "ravenclaw":
            banner_bg = BLUE
            banner_fg = WHITE
            accent_color = BLUE
        elif house == "hufflepuff":
            banner_bg = YELLOW
            banner_fg = BLACK
            accent_color = ORANGE
        else:
            banner_bg = BLACK
            banner_fg = WHITE
            accent_color = BLACK

    # 1. Base parchment background
    draw.rectangle([start_x, 0, WIDTH, HEIGHT], fill=bg_color)

    # 2. Watermark shield in background center
    if dark_mode == 1:
        draw_shield_watermark(draw, start_x + 200, 240, 140, 180, closest_panel_color(watermark_color), dark_mode)

    # 3. Top Banner & House Tie Stripes
    banner_h = 36
    draw.rectangle([start_x, 0, WIDTH, banner_h], fill=closest_panel_color(banner_bg))

    # House Title
    house_name = HOUSE_LABELS.get(house, "Wizarding World") if house else "Wizarding World"
    name_font = font(15, bold=True)
    name_w = int(draw.textlength(house_name, font=name_font))
    draw.text((start_x + (WIDTH - start_x - name_w) // 2, (banner_h - 18) // 2 + 1), house_name.upper(), fill=closest_panel_color(banner_fg), font=name_font)

    # Draw the tie stripes under the banner
    draw_house_stripes(draw, start_x, banner_h, WIDTH - start_x, house or "gryffindor")

    # 4. Ornate Inner Card Border (Thin line with corner brackets)
    card_box = (start_x + 16, banner_h + 16, WIDTH - 16, HEIGHT - 16)
    draw.rectangle(card_box, outline=closest_panel_color(accent_color), width=1)
    # Bold corner brackets
    draw_corner_ornaments(draw, card_box, 16, closest_panel_color(accent_color))

    # 5. Large Quote Marks
    q_mark_font = font(64, bold=True)
    draw.text((start_x + 28, banner_h + 24), "“", fill=closest_panel_color(accent_color), font=q_mark_font)
    draw.text((WIDTH - 54, HEIGHT - 92), "”", fill=closest_panel_color(accent_color), font=q_mark_font)

    # 6. Quote Text
    text_area_x = start_x + 36
    text_area_w = WIDTH - start_x - 72
    text_area_y = banner_h + 36
    text_area_h = HEIGHT - text_area_y - 84

    quote_font_size = 24
    qf_quote = font(quote_font_size)
    wrapped = wrap_text(quote_text, qf_quote, text_area_w, draw)

    while len(wrapped) > 6 and quote_font_size > 14:
        quote_font_size -= 2
        qf_quote = font(quote_font_size)
        wrapped = wrap_text(quote_text, qf_quote, text_area_w, draw)

    line_height = quote_font_size + 6
    total_text_height = len(wrapped) * line_height
    quote_start_y = text_area_y + (text_area_h - total_text_height) // 2

    # Draw centered quote lines
    for i, line in enumerate(wrapped):
        line_w = int(draw.textlength(line, font=qf_quote))
        lx = text_area_x + (text_area_w - line_w) // 2
        draw.text((lx, quote_start_y + i * line_height), line, fill=closest_panel_color(quote_color), font=qf_quote)

    # 7. Ornate Divider (Line + Star)
    divider_y = quote_start_y + total_text_height + 14
    if divider_y < HEIGHT - 64:
        draw.line([(start_x + 120, divider_y), (WIDTH - 120, divider_y)], fill=closest_panel_color(accent_color), width=1)
        draw_star(draw, start_x + 200, divider_y, 6, closest_panel_color(accent_color))

    # 8. Footer & Attribution
    attr_bar_h = 32
    attr_y = HEIGHT - attr_bar_h

    # Gold stripe above footer banner
    draw_house_stripes(draw, start_x, attr_y - 4, WIDTH - start_x, house or "gryffindor")
    draw.rectangle([start_x, attr_y, WIDTH, HEIGHT], fill=closest_panel_color(banner_bg))

    attr_font = font(12, bold=True)
    short_book = {"Philosopher's Stone": "PS", "Chamber of Secrets": "CS", "Prisoner of Azkaban": "PA", "Goblet of Fire": "GF", "Order of the Phoenix": "OP", "Half-Blood Prince": "HBP", "Deathly Hallows": "DH"}.get(book, book) if show_book else None
    attr_text = f"— {character}"
    if short_book:
        attr_text += f", {short_book}"
    attr_w = int(draw.textlength(attr_text, font=attr_font))
    draw.text((start_x + (WIDTH - start_x - attr_w) // 2, attr_y + (attr_bar_h - 15) // 2), attr_text.upper(), fill=closest_panel_color(banner_fg), font=attr_font)


def render_morning_mashup(jen_data: dict[str, Any], quotes: list[dict[str, Any]], config: dict[str, Any], left_dark_mode: int, hp_dark_mode: int) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT), WHITE)
    draw = ImageDraw.Draw(img)

    draw_left_panel(draw, jen_data, config, left_dark_mode)

    divider_x = WIDTH // 2
    divider_color = BLACK
    draw.line([(divider_x, 0), (divider_x, HEIGHT)], fill=divider_color, width=2)

    quote_data = pick_random_quote(quotes)
    draw_hp_quote_card(draw, quote_data["text"], quote_data["character"], quote_data.get("book"), quote_data.get("house"), True, hp_dark_mode)

    return img


def remap_to_panel_palette(img: Image.Image) -> Image.Image:
    palette = Image.new("P", (1, 1))
    flat: list[int] = []
    for rgb in PANEL_PALETTE:
        flat.extend(rgb)
    flat.extend([0, 0, 0] * (256 - len(PANEL_PALETTE)))
    palette.putpalette(flat)
    return img.quantize(palette=palette, dither=0)


def build(payload_path: Path | None = None, style: str = "split_contrast") -> Image.Image:
    data = {}
    config = {}
    db_dark_mode = 0
    if payload_path is not None:
        data = load_payload(payload_path)
        config["style"] = style
    else:
        data, config, db_dark_mode = load_data_from_db()
        if "style" not in config and "layout_variant" not in config:
            config["style"] = style

    # Resolve the final active style used for rendering
    active_style = config.get("style") or config.get("layout_variant") or style
    if data.get("style"):
        active_style = data.get("style")
    elif data.get("layout_variant"):
        active_style = data.get("layout_variant")

    # Resolve left panel dark mode based on the style
    left_dark_mode = db_dark_mode
    if active_style in ("dark_tech", "automotive_hud"):
        left_dark_mode = 1
    elif active_style in ("minimalist", "swiss_typographic", "infographic_timeline", "bauhaus_geometric"):
        left_dark_mode = 0

    # Right panel dark mode is strictly determined to be light (0) as requested by user
    hp_dark_mode = 0
        
    quotes = load_quotes()
    return render_morning_mashup(data, quotes, config, left_dark_mode, hp_dark_mode)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render the morning mashup (Jen Morning + HP quote) to a seven-colour indexed PNG.")
    parser.add_argument("--payload", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=OUT_PATH)
    parser.add_argument("--source-output", type=Path, default=SOURCE_PATH)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--style", type=str, default="split_contrast", choices=["swiss_typographic", "infographic_timeline", "bauhaus_geometric", "automotive_hud", "minimalist", "dark_tech", "split_contrast", "bento_grid"])
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.source_output.parent.mkdir(parents=True, exist_ok=True)
    if args.seed is not None:
        random.seed(args.seed)
    source = build(args.payload, args.style)
    source.save(args.source_output)
    remapped = remap_to_panel_palette(source)
    remapped.save(args.output, optimize=True)
    colors = remapped.convert("RGB").getcolors(maxcolors=256) or []
    print(f"Wrote {args.output}")
    print(f"Source {args.source_output}")
    print("Palette use:")
    for count, rgb in sorted(colors, reverse=True):
        print(f"  #{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}: {count}")


if __name__ == "__main__":
    main()
