#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont, ImageFilter


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
    "gryffindor": {"primary": (116, 0, 1), "primary_dark": (60, 0, 0), "secondary": (206, 158, 26), "secondary_light": (230, 190, 60), "bg": (30, 10, 5), "text": (240, 235, 220)},
    "slytherin": {"primary": (26, 71, 42), "primary_dark": (12, 35, 20), "secondary": (170, 170, 170), "secondary_light": (200, 200, 200), "bg": (10, 20, 12), "text": (230, 235, 225)},
    "ravenclaw": {"primary": (14, 26, 62), "primary_dark": (6, 12, 30), "secondary": (142, 101, 46), "secondary_light": (180, 130, 60), "bg": (8, 14, 35), "text": (235, 230, 215)},
    "hufflepuff": {"primary": (236, 187, 45), "primary_dark": (180, 140, 20), "secondary": (30, 30, 30), "secondary_light": (60, 60, 60), "bg": (25, 22, 10), "text": (240, 235, 220)},
}
HOUSE_LABELS = {"gryffindor": "Gryffindor", "slytherin": "Slytherin", "ravenclaw": "Ravenclaw", "hufflepuff": "Hufflepuff"}

PANEL_PALETTE = [BLACK, WHITE, RED, YELLOW, BLUE, GREEN, ORANGE]

MAP_BG = (248, 245, 240)
MAP_ROAD_MAJOR = (255, 255, 255)
MAP_ROAD_MINOR = (252, 249, 244)
MAP_ROAD_OUTLINE = (210, 205, 195)
MAP_BUILDING = (225, 220, 210)
MAP_BUILDING_DARK = (200, 195, 185)
MAP_PARK = (218, 232, 205)
MAP_WATER = (200, 220, 235)
MAP_LABEL_BG = (255, 255, 255)

CARD_BG = (255, 255, 255)
CARD_SHADOW = (0, 0, 0)
TEXT_PRIMARY = (0, 0, 0)
TEXT_SECONDARY = (90, 90, 90)

ROUTE_COLOUR = (66, 133, 244)
ROUTE_GLOW = (66, 133, 244, 80)
ACCENT = (234, 88, 12)
ACCENT_DARK = (180, 60, 10)
GREEN_ACCENT = (52, 168, 83)


def font(size: int, bold: bool = False, italic: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if italic and bold:
        candidates = ["C:/Windows/Fonts/georgiaz.ttf", "C:/Windows/Fonts/timesbi.ttf"]
    elif italic:
        candidates = ["C:/Windows/Fonts/georgiai.ttf", "C:/Windows/Fonts/timesi.ttf"]
    elif bold:
        candidates = ["C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/georgiab.ttf"]
    else:
        candidates = ["C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/georgia.ttf"]
    for c in candidates:
        try:
            return ImageFont.truetype(c, size)
        except OSError:
            pass
    return ImageFont.load_default()


def font_sans(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for c in candidates:
        try:
            return ImageFont.truetype(c, size)
        except OSError:
            pass
    return ImageFont.load_default()


def load_quotes(path: Path = QUOTES_PATH) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


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


def wrap_text(text: str, font: ImageFont.FreeTypeFont | ImageFont.ImageFont, max_width: int, draw: ImageDraw.ImageDraw) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current_line = ""
    for word in words:
        test_line = current_line + (" " if current_line else "") + word
        bbox = draw.textbbox((0, 0), test_line, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    return lines


def draw_rounded_rect(draw: ImageDraw.ImageDraw, xy: tuple[int, int, int, int], radius: int, fill: tuple[int, int, int], outline: tuple[int, int, int] | None = None, width: int = 1) -> None:
    x0, y0, x1, y1 = xy
    r = radius
    draw.rectangle([x0 + r, y0, x1 - r, y1], fill=fill)
    draw.rectangle([x0, y0 + r, x1, y1 - r], fill=fill)
    draw.pieslice([x0, y0, x0 + r * 2, y0 + r * 2], 180, 270, fill=fill)
    draw.pieslice([x1 - r * 2, y0, x1, y0 + r * 2], 270, 360, fill=fill)
    draw.pieslice([x0, y1 - r * 2, x0 + r * 2, y1], 90, 180, fill=fill)
    draw.pieslice([x1 - r * 2, y1 - r * 2, x1, y1], 0, 90, fill=fill)
    if outline:
        draw.arc([x0, y0, x0 + r * 2, y0 + r * 2], 180, 270, fill=outline, width=width)
        draw.arc([x1 - r * 2, y0, x1, y0 + r * 2], 270, 360, fill=outline, width=width)
        draw.arc([x0, y1 - r * 2, x0 + r * 2, y1], 90, 180, fill=outline, width=width)
        draw.arc([x1 - r * 2, y1 - r * 2, x1, y1], 0, 90, fill=outline, width=width)
        draw.line([(x0 + r, y0), (x1 - r, y0)], fill=outline, width=width)
        draw.line([(x0 + r, y1), (x1 - r, y1)], fill=outline, width=width)
        draw.line([(x0, y0 + r), (x0, y1 - r)], fill=outline, width=width)
        draw.line([(x1, y0 + r), (x1, y1 - r)], fill=outline, width=width)


def lerp_colour(c1: tuple[int, int, int], c2: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return (int(c1[0] + (c2[0] - c1[0]) * t), int(c1[1] + (c2[1] - c1[1]) * t), int(c1[2] + (c2[2] - c1[2]) * t))


def draw_gradient(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, c1: tuple[int, int, int], c2: tuple[int, int, int], vertical: bool = True) -> None:
    if vertical:
        for i in range(h):
            t = i / max(h - 1, 1)
            draw.line([(x, y + i), (x + w, y + i)], fill=lerp_colour(c1, c2, t))
    else:
        for i in range(w):
            t = i / max(w - 1, 1)
            draw.line([(x + i, y), (x + i, y + h)], fill=lerp_colour(c1, c2, t))


def draw_left_panel(draw: ImageDraw.ImageDraw, data: dict[str, Any]) -> None:
    eta = data.get("eta_minutes") or "?"
    route = data.get("route_label") or "Direct"
    distance = data.get("distance_km")
    headline = data.get("headline") or "Time To Work"
    updated = data.get("updated_at") or ""

    panel_w = WIDTH // 2
    draw_gradient(draw, 0, 0, panel_w, HEIGHT, (30, 60, 120), (20, 40, 90))

    header_h = 44
    draw_gradient(draw, 0, 0, panel_w, header_h, (40, 80, 160), (25, 55, 130))
    label_font = font_sans(13, bold=True)
    draw.text((16, (header_h - 16) // 2), "JEN MORNING", fill=WHITE, font=label_font)

    if updated:
        upd_font = font_sans(11)
        bbox = draw.textbbox((0, 0), updated, font=upd_font)
        draw.text((panel_w - bbox[2] - 16, (header_h - bbox[3]) // 2), updated, fill=(180, 200, 240), font=upd_font)

    eta_font = font_sans(80, bold=True)
    bbox = draw.textbbox((0, 0), str(eta), font=eta_font)
    eta_w = bbox[2] - bbox[0]
    eta_x = (panel_w - eta_w) // 2
    draw.text((eta_x, 80), str(eta), fill=(100, 180, 255), font=eta_font)

    unit_font = font_sans(22, bold=True)
    unit_bbox = draw.textbbox((0, 0), "min", font=unit_font)
    unit_w = unit_bbox[2] - unit_bbox[0]
    draw.text((eta_x + eta_w + 10, 100), "min", fill=(100, 180, 255), font=unit_font)

    label_font2 = font_sans(12, bold=True)
    label_bbox = draw.textbbox((0, 0), "DRIVE TIME", font=label_font2)
    label_x = (panel_w - label_bbox[2]) // 2
    draw.text((label_x, 140), "DRIVE TIME", fill=(150, 180, 220), font=label_font2)

    card_y = 180
    card_x = 20
    card_w = panel_w - 40
    card_h = 56
    draw_rounded_rect(draw, [card_x, card_y, card_x + card_w, card_y + card_h], radius=12, fill=(255, 255, 255))

    route_font = font_sans(18, bold=True)
    draw.text((card_x + 16, card_y + 10), f"via {route}", fill=(30, 60, 120), font=route_font)

    if distance is not None and str(distance).strip() not in ("", "?", "unknown"):
        dist_font = font_sans(14)
        bbox = draw.textbbox((0, 0), f"{distance} km", font=dist_font)
        draw.text((card_x + card_w - bbox[2] - 16, card_y + 18), f"{distance} km", fill=(100, 100, 100), font=dist_font)

    dest_font = font_sans(13)
    draw.text((card_x + 16, card_y + 34), headline, fill=(80, 80, 80), font=dest_font)

    status_y = card_y + card_h + 20
    status_h = 48
    draw_rounded_rect(draw, [card_x, status_y, card_x + card_w, status_y + status_h], radius=12, fill=(40, 100, 60))

    status_font = font_sans(16, bold=True)
    status_text = "LEAVE BY 7:15 AM"
    bbox = draw.textbbox((0, 0), status_text, font=status_font)
    draw.text((card_x + (card_w - bbox[2]) // 2, status_y + 14), status_text, fill=WHITE, font=status_font)

    sub_font = font_sans(11)
    sub_text = "On-time arrival expected"
    bbox = draw.textbbox((0, 0), sub_text, font=sub_font)
    draw.text((card_x + (card_w - bbox[2]) // 2, status_y + 32), sub_text, fill=(180, 220, 200), font=sub_font)

    bottom_y = status_y + status_h + 16
    draw.line([(card_x, bottom_y), (card_x + card_w, bottom_y)], fill=(60, 100, 160), width=1)

    traffic_font = font_sans(12, bold=True)
    traffic_text = "TRAFFIC: LIGHT"
    bbox = draw.textbbox((0, 0), traffic_text, font=traffic_font)
    draw.text((card_x + (card_w - bbox[2]) // 2, bottom_y + 10), traffic_text, fill=(100, 180, 255), font=traffic_font)

    weather_font = font_sans(11)
    weather_text = "12°C  Partly Cloudy"
    bbox = draw.textbbox((0, 0), weather_text, font=weather_font)
    draw.text((card_x + (card_w - bbox[2]) // 2, bottom_y + 28), weather_text, fill=(150, 180, 220), font=weather_font)


def draw_hp_quote_card(draw: ImageDraw.ImageDraw, quote_text: str, character: str, book: str | None, house: str | None, show_book: bool) -> None:
    h = HOUSE.get(house, HOUSE["gryffindor"]) if house else HOUSE["gryffindor"]

    start_x = WIDTH // 2
    draw_gradient(draw, start_x, 0, WIDTH, HEIGHT, h["bg"], h["primary_dark"])

    banner_h = 48
    draw_gradient(draw, start_x, 0, WIDTH, banner_h, h["primary"], h["primary_dark"])

    name_font = font_sans(14, bold=True)
    house_name = HOUSE_LABELS.get(house, "Wizarding World") if house else "Wizarding World"
    bbox = draw.textbbox((0, 0), house_name, font=name_font)
    name_w = bbox[2] - bbox[0]
    draw.text((start_x + (WIDTH - start_x - name_w) // 2, (banner_h - (bbox[3] - bbox[1])) // 2), house_name, fill=h["secondary"], font=name_font)

    draw.line([(start_x, banner_h), (WIDTH, banner_h)], fill=h["secondary"], width=2)

    margin_x = 20
    margin_y = 16
    text_area_x = start_x + margin_x
    text_area_w = WIDTH - start_x - margin_x * 2
    text_area_y = banner_h + margin_y
    text_area_h = HEIGHT - text_area_y - 50

    quote_font_size = 28
    qf_quote = font(quote_font_size, italic=True)
    max_text_width = text_area_w

    wrapped = wrap_text(quote_text, qf_quote, max_text_width, draw)
    while len(wrapped) > 5 and quote_font_size > 18:
        quote_font_size -= 2
        qf_quote = font(quote_font_size, italic=True)
        wrapped = wrap_text(quote_text, qf_quote, max_text_width, draw)

    line_height = quote_font_size + 6
    total_text_height = len(wrapped) * line_height
    quote_start_y = text_area_y + (text_area_h - total_text_height) // 3

    for i, line in enumerate(wrapped):
        bbox = draw.textbbox((0, 0), line, font=qf_quote)
        line_w = bbox[2] - bbox[0]
        lx = text_area_x + (max_text_width - line_w) // 2
        draw.text((lx, quote_start_y + i * line_height), line, fill=h["text"], font=qf_quote)

    attr_bar_h = 40
    attr_y = HEIGHT - attr_bar_h
    draw.line([(start_x, attr_y), (WIDTH, attr_y)], fill=h["secondary"], width=1)

    attr_font = font_sans(12, bold=True)
    short_book = {"Philosopher's Stone": "PS", "Chamber of Secrets": "CS", "Prisoner of Azkaban": "PA", "Goblet of Fire": "GF", "Order of the Phoenix": "OP", "Half-Blood Prince": "HBP", "Deathly Hallows": "DH"}.get(book, book) if show_book else None
    attr_text = f"\u2014 {character}"
    if short_book:
        attr_text += f", {short_book}"
    bbox = draw.textbbox((0, 0), attr_text, font=attr_font)
    attr_w = bbox[2] - bbox[0]
    draw.text((start_x + (WIDTH - start_x - attr_w) // 2, attr_y + (attr_bar_h - (bbox[3] - bbox[1])) // 2), attr_text, fill=h["secondary_light"], font=attr_font)


def render_morning_mashup(jen_data: dict[str, Any], quotes: list[dict[str, Any]]) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT), (20, 40, 90))
    draw = ImageDraw.Draw(img)

    draw_left_panel(draw, jen_data)

    divider_x = WIDTH // 2
    draw.line([(divider_x, 0), (divider_x, HEIGHT)], fill=(60, 100, 160), width=2)

    quote_data = pick_random_quote(quotes)
    draw_hp_quote_card(draw, quote_data["text"], quote_data["character"], quote_data.get("book"), quote_data.get("house"), True)

    return img


def remap_to_panel_palette(img: Image.Image) -> Image.Image:
    palette = Image.new("P", (1, 1))
    flat: list[int] = []
    for rgb in PANEL_PALETTE:
        flat.extend(rgb)
    flat.extend([0, 0, 0] * (256 - len(PANEL_PALETTE)))
    palette.putpalette(flat)
    return img.quantize(palette=palette, dither=Image.Dither.FLOYDSTEINBERG)


def build(payload_path: Path = DEFAULT_PAYLOAD) -> Image.Image:
    data = load_payload(payload_path)
    quotes = load_quotes()
    return render_morning_mashup(data, quotes)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render the morning mashup (Jen Morning + HP quote) to a seven-colour indexed PNG.")
    parser.add_argument("--payload", type=Path, default=DEFAULT_PAYLOAD)
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
