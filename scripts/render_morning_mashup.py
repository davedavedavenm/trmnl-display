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

    # 1. Resolve Cohesive Theme Colors
    if dark_mode == 1:
        bg_panel = BLACK
        fg_primary = WHITE
        fg_secondary = (180, 180, 180)
        card_bg = (20, 20, 20)
        card_border = WHITE
        
        if profile == "forest":
            theme_color = GREEN
            secondary_accent = ORANGE
            card1_default_bg = (10, 35, 20)
        elif profile == "slate":
            theme_color = WHITE
            secondary_accent = ORANGE
            card1_default_bg = (40, 40, 40)
        else: # navy_blue
            theme_color = BLUE
            secondary_accent = ORANGE
            card1_default_bg = (15, 35, 90)
            
        traffic_bg = (30, 30, 30)
        traffic_fg = theme_color
        status_bg = theme_color
        status_fg = BLACK if theme_color in (YELLOW, WHITE) else WHITE
        status_left_bar = theme_color
        status_icon_color = theme_color
    else:
        # Light mode
        if profile == "forest":
            bg_panel = (242, 248, 243)      # soft pale green
            card_border = GREEN
            theme_color = GREEN
            secondary_accent = ORANGE
            fg_secondary = (50, 100, 60)
            traffic_bg = (220, 244, 225)
            traffic_fg = GREEN
            card1_default_bg = (220, 244, 225)
        elif profile == "slate":
            bg_panel = (244, 244, 244)      # soft grey
            card_border = BLACK
            theme_color = BLACK
            secondary_accent = ORANGE
            fg_secondary = (110, 110, 110)
            traffic_bg = (230, 230, 230)
            traffic_fg = BLACK
            card1_default_bg = (230, 230, 230)
        else: # navy_blue
            bg_panel = (240, 244, 250)      # soft pale blue
            card_border = BLUE
            theme_color = BLUE
            secondary_accent = ORANGE
            fg_secondary = (60, 90, 140)
            traffic_bg = (220, 232, 252)
            traffic_fg = BLUE
            card1_default_bg = (220, 232, 252)

        card_bg = WHITE
        fg_primary = BLACK
        status_bg = theme_color
        status_fg = WHITE
        status_left_bar = theme_color
        status_icon_color = theme_color

    # Initialize Card 1 colors
    card1_bg = card1_default_bg
    card1_accent_bar = theme_color
    if dark_mode == 1:
        card1_fg_primary = WHITE
        card1_fg_secondary = (180, 180, 180)
        card1_badge_bg = WHITE
        card1_badge_fg = theme_color
    else:
        card1_fg_primary = BLACK
        card1_fg_secondary = fg_secondary
        card1_badge_bg = WHITE
        card1_badge_fg = theme_color

    # Overrides for warnings
    traffic_text = "LIGHT TRAFFIC"
    sub_text = "On-time arrival expected"
    try:
        eta_m = int(eta)
        if eta_m > 55:
            traffic_text = "HEAVY TRAFFIC"
            sub_text = "Heavy traffic warning!"
            
            # Card 1 overrides
            card1_bg = RED
            card1_fg_primary = WHITE
            card1_fg_secondary = WHITE
            card1_accent_bar = WHITE
            card1_badge_bg = WHITE
            card1_badge_fg = RED

            # Card 3 overrides
            status_bg = RED
            status_fg = WHITE
            status_left_bar = RED
            status_icon_color = RED
        elif eta_m > 45:
            traffic_text = "MODERATE TRAFFIC"
            sub_text = "Caution: minor delay"
            
            # Card 1 overrides
            card1_bg = ORANGE
            card1_fg_primary = WHITE
            card1_fg_secondary = WHITE
            card1_accent_bar = WHITE
            card1_badge_bg = WHITE
            card1_badge_fg = ORANGE

            # Card 3 overrides
            status_bg = ORANGE
            status_fg = WHITE
            status_left_bar = ORANGE
            status_icon_color = ORANGE
    except ValueError:
        pass

    # 2. Draw Background
    draw.rectangle([0, 0, WIDTH // 2, HEIGHT], fill=bg_panel)

    # 3. Header
    badge_font = font(14, bold=True)
    badge_w = int(draw.textlength(screen_label, font=badge_font))
    pill_x0, pill_y0 = 18, 16
    pill_x1, pill_y1 = pill_x0 + badge_w + 20, 40

    pill_bg = theme_color
    pill_fg = WHITE
    if pill_bg == YELLOW:
        pill_fg = BLACK
    elif pill_bg == WHITE and dark_mode == 0:
        pill_bg = BLACK
    elif pill_bg == BLACK and dark_mode == 1:
        pill_bg = WHITE
        pill_fg = BLACK

    draw.rounded_rectangle([(pill_x0, pill_y0), (pill_x1, pill_y1)], radius=12, fill=closest_panel_color(pill_bg))
    draw.text((pill_x0 + 10, pill_y0 + 4), screen_label.upper(), fill=closest_panel_color(pill_fg), font=badge_font)

    if updated:
        upd_font = font(12, bold=True)
        draw.text((WIDTH // 2 - 18, 28), updated, fill=closest_panel_color(fg_secondary), font=upd_font, anchor="rm")

    divider_y = 50
    draw.line([(18, divider_y), (WIDTH // 2 - 18, divider_y)], fill=closest_panel_color(fg_secondary), width=1)

    # 4. ETA Card (Card 1)
    card1_y0, card1_y1 = 62, 182
    draw.rounded_rectangle([(18, card1_y0), (WIDTH // 2 - 18, card1_y1)], radius=10, fill=card1_bg, outline=closest_panel_color(card_border), width=2)
    draw.rounded_rectangle([(20, card1_y0 + 2), (28, card1_y1 - 2)], radius=3, fill=closest_panel_color(card1_accent_bar))

    draw_clock_icon(draw, 44, card1_y0 + 18, 7, closest_panel_color(card1_fg_secondary))
    lbl_font = font(12, bold=True)
    draw.text((58, card1_y0 + 11), eta_lbl.upper(), fill=closest_panel_color(card1_fg_secondary), font=lbl_font)

    eta_font = font(54, bold=True)
    eta_str = str(eta)
    draw.text((44, card1_y0 + 36), eta_str, fill=closest_panel_color(card1_fg_primary), font=eta_font)
    eta_w = int(draw.textlength(eta_str, font=eta_font))

    unit_font = font(18, bold=True)
    draw.text((44 + eta_w + 6, card1_y0 + 64), eta_unit, fill=closest_panel_color(card1_fg_secondary), font=unit_font)

    t_font = font(11, bold=True)
    t_w = int(draw.textlength(traffic_text, font=t_font))
    t_badge_x0 = 382 - 20 - t_w - 12
    t_badge_y0 = card1_y0 + 44
    draw.rounded_rectangle([(t_badge_x0, t_badge_y0), (t_badge_x0 + t_w + 12, t_badge_y0 + 24)], radius=6, fill=closest_panel_color(card1_badge_bg))
    draw.text((t_badge_x0 + 6, t_badge_y0 + 4), traffic_text, fill=closest_panel_color(card1_badge_fg), font=t_font)

    # 5. Route Card (Card 2)
    card2_y0, card2_y1 = 196, 326
    draw.rounded_rectangle([(18, card2_y0), (WIDTH // 2 - 18, card2_y1)], radius=10, fill=card_bg, outline=closest_panel_color(card_border), width=2)
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

    # Cute Visual Timeline
    draw_route_diagram(draw, 44, card2_y0 + 96, 310, closest_panel_color(theme_color), closest_panel_color(secondary_accent))

    # 6. Status Card (Card 3)
    card3_y0, card3_y1 = 340, 464
    draw.rounded_rectangle([(18, card3_y0), (WIDTH // 2 - 18, card3_y1)], radius=10, fill=card_bg, outline=closest_panel_color(card_border), width=2)
    draw.rounded_rectangle([(20, card3_y0 + 2), (28, card3_y1 - 2)], radius=3, fill=closest_panel_color(status_left_bar))

    draw_alert_icon(draw, 44, card3_y0 + 18, 7, closest_panel_color(status_icon_color))
    draw.text((58, card3_y0 + 11), "RECOMMENDED ACTION", fill=closest_panel_color(fg_secondary), font=lbl_font)

    status_text = "LEAVE BY 7:15 AM"
    status_font = font(18, bold=True)
    draw.text((44, card3_y0 + 32), status_text, fill=closest_panel_color(fg_primary), font=status_font)

    s_font = font(12, bold=True)
    s_w = int(draw.textlength(sub_text, font=s_font))
    s_badge_x0 = 44
    s_badge_y0 = card3_y0 + 62
    
    draw.rounded_rectangle([(s_badge_x0, s_badge_y0), (s_badge_x0 + s_w + 20, s_badge_y0 + 24)], radius=6, fill=closest_panel_color(status_bg))
    draw.text((s_badge_x0 + 10, s_badge_y0 + 4), sub_text, fill=closest_panel_color(status_fg), font=s_font)


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
        bg_color = (253, 250, 242)  # Elegant light parchment
        quote_color = (30, 25, 20)  # Calligraphy ink
        watermark_color = (244, 238, 226) # Watermark shield color (subtle cream)
        
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
    draw.rectangle(card_box, outline=closest_panel_color((220, 215, 205) if dark_mode == 0 else (60, 50, 40)), width=1)
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


def render_morning_mashup(jen_data: dict[str, Any], quotes: list[dict[str, Any]], config: dict[str, Any], dark_mode: int) -> Image.Image:
    bg_color = BLACK if dark_mode == 1 else WHITE
    img = Image.new("RGB", (WIDTH, HEIGHT), bg_color)
    draw = ImageDraw.Draw(img)

    draw_left_panel(draw, jen_data, config, dark_mode)

    divider_x = WIDTH // 2
    divider_color = (100, 100, 100) if dark_mode == 1 else (0, 0, 0)
    draw.line([(divider_x, 0), (divider_x, HEIGHT)], fill=divider_color, width=2)

    quote_data = pick_random_quote(quotes)
    draw_hp_quote_card(draw, quote_data["text"], quote_data["character"], quote_data.get("book"), quote_data.get("house"), True, dark_mode)

    return img


def remap_to_panel_palette(img: Image.Image) -> Image.Image:
    palette = Image.new("P", (1, 1))
    flat: list[int] = []
    for rgb in PANEL_PALETTE:
        flat.extend(rgb)
    flat.extend([0, 0, 0] * (256 - len(PANEL_PALETTE)))
    palette.putpalette(flat)
    return img.quantize(palette=palette, dither=Image.Dither.FLOYDSTEINBERG)


def build(payload_path: Path | None = None) -> Image.Image:
    data = {}
    config = {}
    dark_mode = 0
    if payload_path is not None:
        data = load_payload(payload_path)
    else:
        data, config, dark_mode = load_data_from_db()
    quotes = load_quotes()
    return render_morning_mashup(data, quotes, config, dark_mode)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render the morning mashup (Jen Morning + HP quote) to a seven-colour indexed PNG.")
    parser.add_argument("--payload", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=OUT_PATH)
    parser.add_argument("--source-output", type=Path, default=SOURCE_PATH)
    parser.add_argument("--seed", type=int, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.source_output.parent.mkdir(parents=True, exist_ok=True)
    if args.seed is not None:
        random.seed(args.seed)
    source = build(args.payload)
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
