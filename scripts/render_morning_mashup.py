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
    if profile == "forest":
        primary_accent = GREEN
        secondary_accent = BLUE
    elif profile == "slate":
        primary_accent = BLACK if dark_mode == 0 else WHITE
        secondary_accent = ORANGE
    else:  # navy_blue
        primary_accent = BLUE
        secondary_accent = ORANGE

    if dark_mode == 1:
        bg_panel = BLACK
        fg_primary = WHITE
        fg_secondary = (180, 180, 180)
        card_border = WHITE
        status_green = (50, 220, 100)
    else:
        bg_panel = WHITE
        fg_primary = BLACK
        fg_secondary = (120, 120, 120)
        card_border = BLACK
        status_green = (0, 120, 50)

    # 1. Background
    draw.rectangle([0, 0, WIDTH // 2, HEIGHT], fill=bg_panel)

    # 2. Header
    badge_font = font(14, bold=True)
    badge_w = int(draw.textlength(screen_label, font=badge_font))
    pill_x0, pill_y0 = 18, 16
    pill_x1, pill_y1 = pill_x0 + badge_w + 20, 40

    pill_bg = primary_accent
    pill_fg = WHITE
    if pill_bg == YELLOW:
        pill_fg = BLACK
    elif pill_bg == WHITE and dark_mode == 0:
        pill_bg = BLACK
    elif pill_bg == BLACK and dark_mode == 1:
        pill_bg = WHITE
        pill_fg = BLACK

    draw.rounded_rectangle([(pill_x0, pill_y0), (pill_x1, pill_y1)], radius=12, fill=closest_panel_color(pill_bg))
    draw.text((pill_x0 + 10, pill_y0 + 4), screen_label, fill=closest_panel_color(pill_fg), font=badge_font)

    if updated:
        upd_font = font(12, bold=True)
        draw.text((WIDTH // 2 - 18, 28), updated, fill=closest_panel_color(fg_secondary), font=upd_font, anchor="rm")

    divider_y = 54
    draw.line([(18, divider_y), (WIDTH // 2 - 18, divider_y)], fill=closest_panel_color(fg_secondary), width=1)

    # 3. ETA Card (Card 1)
    card1_y0, card1_y1 = 68, 198
    draw.rounded_rectangle([(18, card1_y0), (WIDTH // 2 - 18, card1_y1)], radius=10, fill=bg_panel, outline=closest_panel_color(card_border), width=2)
    draw.rounded_rectangle([(20, card1_y0 + 2), (28, card1_y1 - 2)], radius=3, fill=closest_panel_color(primary_accent))

    eta_font = font(64, bold=True)
    eta_str = str(eta)
    draw.text((44, card1_y0 + 10), eta_str, fill=closest_panel_color(fg_primary), font=eta_font)
    eta_w = int(draw.textlength(eta_str, font=eta_font))

    unit_font = font(20, bold=True)
    draw.text((44 + eta_w + 8, card1_y0 + 44), eta_unit, fill=closest_panel_color(fg_secondary), font=unit_font)

    lbl_font = font(14, bold=True)
    draw.text((44, card1_y0 + 90), eta_lbl.upper(), fill=closest_panel_color(fg_secondary), font=lbl_font)

    # 4. Route Card (Card 2)
    card2_y0, card2_y1 = 212, 338
    draw.rounded_rectangle([(18, card2_y0), (WIDTH // 2 - 18, card2_y1)], radius=10, fill=bg_panel, outline=closest_panel_color(card_border), width=2)
    draw.rounded_rectangle([(20, card2_y0 + 2), (28, card2_y1 - 2)], radius=3, fill=closest_panel_color(secondary_accent))

    sec_font = font(12, bold=True)
    draw.text((44, card2_y0 + 10), "ROUTE", fill=closest_panel_color(fg_secondary), font=sec_font)

    route_text = f"via {route}"
    if len(route_text) > 24:
        route_text = route_text[:22] + "..."
    route_font = font(18 if len(route_text) > 20 else 22, bold=True)
    draw.text((44, card2_y0 + 26), route_text, fill=closest_panel_color(fg_primary), font=route_font)

    if show_dist and distance is not None and str(distance).strip() not in ("", "?", "unknown"):
        dist_text = f"{distance} {dist_unit}"
        dist_font = font(14, bold=True)
        draw.text((44, card2_y0 + 64), dist_text, fill=closest_panel_color(fg_secondary), font=dist_font)

    headline_font = font(16, bold=True)
    draw.text((44, card2_y0 + 90), headline, fill=closest_panel_color(fg_primary), font=headline_font)

    # 5. Status Card (Card 3)
    card3_y0, card3_y1 = 352, 464
    draw.rounded_rectangle([(18, card3_y0), (WIDTH // 2 - 18, card3_y1)], radius=10, fill=bg_panel, outline=closest_panel_color(card_border), width=2)
    draw.rounded_rectangle([(20, card3_y0 + 2), (28, card3_y1 - 2)], radius=3, fill=closest_panel_color(GREEN))

    draw.text((44, card3_y0 + 10), "COMMUTE STATUS", fill=closest_panel_color(fg_secondary), font=sec_font)

    status_text = "LEAVE BY 7:15 AM"
    status_font = font(20, bold=True)
    draw.text((44, card3_y0 + 26), status_text, fill=closest_panel_color(fg_primary), font=status_font)

    sub_text = "On-time arrival expected"
    try:
        eta_m = int(eta)
        if eta_m > 55:
            sub_text = "Heavy traffic warning!"
            status_green = RED
    except ValueError:
        pass
    sub_font = font(14, bold=True)
    draw.text((44, card3_y0 + 64), sub_text, fill=closest_panel_color(status_green), font=sub_font)


def draw_hp_quote_card(draw: ImageDraw.ImageDraw, quote_text: str, character: str, book: str | None, house: str | None, show_book: bool, dark_mode: int) -> None:
    h = HOUSE.get(house, HOUSE["gryffindor"]) if house else HOUSE["gryffindor"]
    start_x = WIDTH // 2

    if dark_mode == 1:
        bg_color = h["bg"]
        quote_color = h["text"]
        accent_color = h["secondary"]
        banner_bg = h["primary"]
        banner_fg = h["secondary"]
    else:
        bg_color = (253, 250, 242)
        quote_color = (30, 25, 20)
        
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

    draw.rectangle([start_x, 0, WIDTH, HEIGHT], fill=bg_color)

    banner_h = 44
    draw.rectangle([start_x, 0, WIDTH, banner_h], fill=closest_panel_color(banner_bg))

    house_name = HOUSE_LABELS.get(house, "Wizarding World") if house else "Wizarding World"
    name_font = font(16, bold=True)
    name_w = int(draw.textlength(house_name, font=name_font))
    draw.text((start_x + (WIDTH - start_x - name_w) // 2, (banner_h - 18) // 2), house_name.upper(), fill=closest_panel_color(banner_fg), font=name_font)

    draw.line([(start_x, banner_h), (WIDTH, banner_h)], fill=closest_panel_color(accent_color), width=2)

    draw.rectangle([start_x + 10, banner_h + 10, WIDTH - 10, HEIGHT - 10], outline=closest_panel_color(accent_color), width=2)

    text_area_x = start_x + 24
    text_area_w = WIDTH - start_x - 48
    text_area_y = banner_h + 20
    text_area_h = HEIGHT - text_area_y - 54

    quote_font_size = 28
    qf_quote = font(quote_font_size)
    wrapped = wrap_text(quote_text, qf_quote, text_area_w, draw)

    while len(wrapped) > 6 and quote_font_size > 16:
        quote_font_size -= 2
        qf_quote = font(quote_font_size)
        wrapped = wrap_text(quote_text, qf_quote, text_area_w, draw)

    line_height = quote_font_size + 6
    total_text_height = len(wrapped) * line_height
    quote_start_y = text_area_y + (text_area_h - total_text_height) // 2

    for i, line in enumerate(wrapped):
        line_w = int(draw.textlength(line, font=qf_quote))
        lx = text_area_x + (text_area_w - line_w) // 2
        draw.text((lx, quote_start_y + i * line_height), line, fill=closest_panel_color(quote_color), font=qf_quote)

    attr_bar_h = 36
    attr_y = HEIGHT - attr_bar_h
    draw.line([(start_x + 10, attr_y), (WIDTH - 10, attr_y)], fill=closest_panel_color(accent_color), width=2)

    attr_font = font(13, bold=True)
    short_book = {"Philosopher's Stone": "PS", "Chamber of Secrets": "CS", "Prisoner of Azkaban": "PA", "Goblet of Fire": "GF", "Order of the Phoenix": "OP", "Half-Blood Prince": "HBP", "Deathly Hallows": "DH"}.get(book, book) if show_book else None
    attr_text = f"\u2014 {character}"
    if short_book:
        attr_text += f", {short_book}"
    attr_w = int(draw.textlength(attr_text, font=attr_font))
    draw.text((start_x + (WIDTH - start_x - attr_w) // 2, attr_y + (attr_bar_h - 15) // 2), attr_text, fill=closest_panel_color(quote_color), font=attr_font)


def render_morning_mashup(jen_data: dict[str, Any], quotes: list[dict[str, Any]], config: dict[str, Any], dark_mode: int) -> Image.Image:
    bg_color = BLACK if dark_mode == 1 else WHITE
    img = Image.new("RGB", (WIDTH, HEIGHT), bg_color)
    draw = ImageDraw.Draw(img)

    draw_left_panel(draw, jen_data, config, dark_mode)

    divider_x = WIDTH // 2
    divider_color = (100, 100, 100) if dark_mode == 1 else (200, 200, 200)
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
