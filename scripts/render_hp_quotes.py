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
PLUGIN_DIR = ROOT / "plugins" / "trmnl-hp-quotes"
QUOTES_PATH = PLUGIN_DIR / "quotes.json"
DEFAULT_PAYLOAD = PLUGIN_DIR / "payload.example.json"
OUT_DIR = Path(__file__).resolve().parent / "tmp"
OUT_PATH = OUT_DIR / "sidecar_hp_quotes_next.png"
SOURCE_PATH = OUT_DIR / "sidecar_hp_quotes_source_next.png"
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
        "text": (240, 235, 220),
        "accent": (180, 40, 10),
    },
    "slytherin": {
        "primary": (26, 71, 42),
        "primary_dark": (12, 35, 20),
        "secondary": (170, 170, 170),
        "secondary_light": (200, 200, 200),
        "bg": (10, 20, 12),
        "text": (230, 235, 225),
        "accent": (40, 100, 60),
    },
    "ravenclaw": {
        "primary": (14, 26, 62),
        "primary_dark": (6, 12, 30),
        "secondary": (142, 101, 46),
        "secondary_light": (180, 130, 60),
        "bg": (8, 14, 35),
        "text": (235, 230, 215),
        "accent": (30, 50, 100),
    },
    "hufflepuff": {
        "primary": (236, 187, 45),
        "primary_dark": (180, 140, 20),
        "secondary": (30, 30, 30),
        "secondary_light": (60, 60, 60),
        "bg": (25, 22, 10),
        "text": (240, 235, 220),
        "accent": (200, 160, 30),
    },
}
HOUSE_LABELS = {
    "gryffindor": "Gryffindor",
    "slytherin": "Slytherin",
    "ravenclaw": "Ravenclaw",
    "hufflepuff": "Hufflepuff",
}

PANEL_PALETTE = [BLACK, WHITE, RED, YELLOW, BLUE, GREEN, ORANGE]


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


def load_payload(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    if isinstance(raw, dict) and isinstance(raw.get("merge_variables"), dict):
        return raw["merge_variables"]
    if isinstance(raw, dict):
        return raw
    return {}


def pick_random_quote(quotes: list[dict[str, Any]]) -> dict[str, Any]:
    return random.choice(quotes)


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


def lerp_colour(c1: tuple[int, int, int], c2: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
    )


def draw_gradient(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, c1: tuple[int, int, int], c2: tuple[int, int, int], vertical: bool = True) -> None:
    if vertical:
        for i in range(h):
            t = i / max(h - 1, 1)
            c = lerp_colour(c1, c2, t)
            draw.line([(x, y + i), (x + w, y + i)], fill=c)
    else:
        for i in range(w):
            t = i / max(w - 1, 1)
            c = lerp_colour(c1, c2, t)
            draw.line([(x + i, y), (x + i, y + h)], fill=c)


def draw_star(draw: ImageDraw.ImageDraw, cx: int, cy: int, outer_r: int, inner_r: int, colour: tuple[int, int, int]) -> None:
    points = []
    for i in range(10):
        angle = math.radians(i * 36 - 90)
        r = outer_r if i % 2 == 0 else inner_r
        points.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    draw.polygon(points, fill=colour)


def draw_shield(draw: ImageDraw.ImageDraw, cx: int, cy: int, w: int, h: int, primary: tuple[int, int, int], secondary: tuple[int, int, int]) -> None:
    sx = cx - w // 2
    sy = cy - h // 2
    pts = [
        (sx, sy),
        (sx + w, sy),
        (sx + w, sy + h * 0.55),
        (cx, sy + h),
        (sx, sy + h * 0.55),
    ]
    draw.polygon(pts, fill=primary)
    draw.polygon(pts, outline=secondary, width=2)

    inner_w = w - 6
    inner_h = h - 6
    ix = cx - inner_w // 2
    iy = sy + 3
    inner_pts = [
        (ix, iy),
        (ix + inner_w, iy),
        (ix + inner_w, iy + inner_h * 0.55),
        (cx, iy + inner_h),
        (ix, iy + inner_h * 0.55),
    ]
    draw.polygon(inner_pts, fill=secondary)

    draw.line([sx, sy + h * 0.3, sx + w, sy + h * 0.3], fill=secondary, width=1)
    draw.line([sx, sy + h * 0.7, sx + w, sy + h * 0.7], fill=secondary, width=1)


def draw_ornate_divider(draw: ImageDraw.ImageDraw, cx: int, y: int, w: int, colour: tuple[int, int, int]) -> None:
    x1 = cx - w // 2
    x2 = cx + w // 2
    draw.line([(x1, y), (x2, y)], fill=colour, width=2)
    draw_star(draw, cx, y, 6, 2, colour)
    for dx in [-w // 2, w // 2]:
        draw_star(draw, cx + dx, y, 4, 1, colour)


def draw_parchment_texture(draw: ImageDraw.ImageDraw, w: int, h: int, base: tuple[int, int, int]) -> None:
    for _ in range(3000):
        x = random.randint(0, w - 1)
        y = random.randint(0, h - 1)
        noise = random.randint(-15, 15)
        c = (
            max(0, min(255, base[0] + noise)),
            max(0, min(255, base[1] + noise)),
            max(0, min(255, base[2] + noise)),
        )
        draw.point((x, y), fill=c)


def draw_magical_sparkles(draw: ImageDraw.ImageDraw, count: int, x_range: tuple[int, int], y_range: tuple[int, int], colour: tuple[int, int, int]) -> None:
    for _ in range(count):
        sx = random.randint(x_range[0], x_range[1])
        sy = random.randint(y_range[0], y_range[1])
        size = random.randint(3, 7)
        draw_star(draw, sx, sy, size, size // 3, colour)


def draw_corner_ornament(draw: ImageDraw.ImageDraw, x: int, y: int, size: int, colour: tuple[int, int, int], horizontal: bool = True, flip: bool = False) -> None:
    if horizontal:
        if not flip:
            pts = [(x, y), (x + size, y), (x + size, y + size * 0.3)]
        else:
            pts = [(x, y), (x - size, y), (x - size, y + size * 0.3)]
    else:
        if not flip:
            pts = [(x, y), (x, y + size), (x + size * 0.3, y + size)]
        else:
            pts = [(x, y), (x, y - size), (x + size * 0.3, y - size)]
    draw.polygon(pts, fill=colour)


def render_full_screen(draw: ImageDraw.ImageDraw, quote_text: str, character: str, book: str | None, house: str | None, show_book: bool) -> None:
    h = HOUSE.get(house, HOUSE["gryffindor"]) if house else HOUSE["gryffindor"]
    house_name = HOUSE_LABELS.get(house, "Wizarding World") if house else "Wizarding World"

    draw_gradient(draw, 0, 0, WIDTH, HEIGHT, h["bg"], h["primary_dark"])

    draw_parchment_texture(draw, WIDTH, HEIGHT, h["bg"])

    banner_h = 90
    draw_gradient(draw, 0, 0, WIDTH, banner_h, h["primary"], h["primary_dark"])

    draw_shield(draw, 60, banner_h // 2, 56, 68, h["primary"], h["secondary"])

    name_font = font_sans(28, bold=True)
    bbox = draw.textbbox((0, 0), house_name, font=name_font)
    name_w = bbox[2] - bbox[0]
    draw.text((140, (banner_h - (bbox[3] - bbox[1])) // 2), house_name, fill=h["secondary"], font=name_font)

    draw_magical_sparkles(draw, 10, (140 + name_w + 30, WIDTH - 40), (8, banner_h - 8), h["secondary"])

    draw.line([(0, banner_h), (WIDTH, banner_h)], fill=h["secondary"], width=3)

    side_w = 8
    draw_gradient(draw, 0, banner_h, side_w, HEIGHT - banner_h - 50, h["primary"], h["primary_dark"])
    draw_gradient(draw, WIDTH - side_w, banner_h, side_w, HEIGHT - banner_h - 50, h["primary"], h["primary_dark"])

    text_area_x = 50
    text_area_w = WIDTH - 100
    text_area_y = banner_h + 30
    text_area_h = HEIGHT - text_area_y - 50 - 50

    draw_ornate_divider(draw, WIDTH // 2, text_area_y + 10, 200, h["secondary"])

    quote_font_size = 56
    qf_quote = font(quote_font_size, bold=False, italic=True)
    max_text_width = text_area_w - 60

    wrapped = wrap_text(quote_text, qf_quote, max_text_width, draw)
    while len(wrapped) > 3 and quote_font_size > 32:
        quote_font_size -= 2
        qf_quote = font(quote_font_size, bold=False, italic=True)
        wrapped = wrap_text(quote_text, qf_quote, max_text_width, draw)

    line_height = quote_font_size + 12
    total_text_height = len(wrapped) * line_height

    if text_area_y + total_text_height + 20 > text_area_y + text_area_h:
        quote_font_size = max(quote_font_size - 4, 28)
        qf_quote = font(quote_font_size, bold=False, italic=True)
        wrapped = wrap_text(quote_text, qf_quote, max_text_width, draw)
        line_height = quote_font_size + 10
        total_text_height = len(wrapped) * line_height

    quote_start_y = text_area_y + 30 + (text_area_h - total_text_height) // 2

    open_qf = font(64, bold=False, italic=True)
    draw.text((text_area_x + 10, quote_start_y - 16), "\u201c", fill=h["secondary"], font=open_qf)

    for i, line in enumerate(wrapped):
        bbox = draw.textbbox((0, 0), line, font=qf_quote)
        line_w = bbox[2] - bbox[0]
        lx = text_area_x + 30 + (text_area_w - 60 - line_w) // 2
        draw.text((lx, quote_start_y + i * line_height), line, fill=h["text"], font=qf_quote)

    last_line_bbox = draw.textbbox((0, 0), wrapped[-1], font=qf_quote)
    last_line_w = last_line_bbox[2] - last_line_bbox[0]
    close_x = text_area_x + 30 + (text_area_w - 60 + last_line_w) // 2 + 8
    close_y = quote_start_y + (len(wrapped) - 1) * line_height - 12
    draw.text((close_x, close_y), "\u201d", fill=h["secondary"], font=open_qf)

    bottom_bar_h = 44
    attr_y = quote_start_y + total_text_height + 20
    max_attr_y = HEIGHT - bottom_bar_h - 36
    if attr_y > max_attr_y:
        attr_y = max_attr_y
    draw_ornate_divider(draw, WIDTH // 2, attr_y - 8, 160, h["secondary"])
    draw_gradient(draw, 0, HEIGHT - bottom_bar_h, WIDTH, bottom_bar_h, h["primary_dark"], h["primary"])
    draw.line([(0, HEIGHT - bottom_bar_h), (WIDTH, HEIGHT - bottom_bar_h)], fill=h["secondary"], width=2)

    draw_magical_sparkles(draw, 5, (60, WIDTH - 60), (HEIGHT - bottom_bar_h + 8, HEIGHT - 12), h["secondary"])


def render_half_vertical(draw: ImageDraw.ImageDraw, quote_text: str, character: str, book: str | None, house: str | None, show_book: bool) -> None:
    start_x = 400
    h = HOUSE.get(house, HOUSE["gryffindor"]) if house else HOUSE["gryffindor"]
    house_name = HOUSE_LABELS.get(house, "Wizarding World") if house else "Wizarding World"

    banner_h = 48
    draw_gradient(draw, start_x, 0, 400, banner_h, h["primary"], h["primary_dark"])

    name_font = font_sans(14, bold=True)
    bbox = draw.textbbox((0, 0), house_name, font=name_font)
    name_w = bbox[2] - bbox[0]
    draw.text((start_x + (400 - name_w) // 2, (banner_h - (bbox[3] - bbox[1])) // 2), house_name, fill=h["secondary"], font=name_font)

    draw.line([(start_x, banner_h), (WIDTH, banner_h)], fill=h["secondary"], width=2)

    side_w = 4
    draw_gradient(draw, start_x, banner_h, side_w, HEIGHT - 34, h["primary"], h["primary_dark"])

    margin_x = 14
    margin_y = 10
    text_area_x = start_x + margin_x + side_w
    text_area_w = 400 - margin_x * 2 - side_w
    text_area_y = banner_h + margin_y + 14
    text_area_h = HEIGHT - text_area_y - 34 - margin_y - 6

    quote_font_size = 28
    qf_quote = font(quote_font_size, bold=False, italic=True)
    max_text_width = text_area_w - 8

    wrapped = wrap_text(quote_text, qf_quote, max_text_width, draw)
    while len(wrapped) > 5 and quote_font_size > 16:
        quote_font_size -= 2
        qf_quote = font(quote_font_size, bold=False, italic=True)
        wrapped = wrap_text(quote_text, qf_quote, max_text_width, draw)

    line_height = quote_font_size + 6
    total_text_height = len(wrapped) * line_height
    quote_start_y = text_area_y + (text_area_h - total_text_height) // 3

    for i, line in enumerate(wrapped):
        bbox = draw.textbbox((0, 0), line, font=qf_quote)
        line_w = bbox[2] - bbox[0]
        lx = text_area_x + (max_text_width - line_w) // 2
        draw.text((lx, quote_start_y + i * line_height), line, fill=h["text"], font=qf_quote)

    attr_bar_h = 30
    draw_gradient(draw, start_x, HEIGHT - attr_bar_h, 400, attr_bar_h, h["primary_dark"], h["primary"])
    draw.line([(start_x, HEIGHT - attr_bar_h), (WIDTH, HEIGHT - attr_bar_h)], fill=h["secondary"], width=1)

    attr_font = font_sans(11, bold=True)
    short_book = {
        "Philosopher's Stone": "PS", "Chamber of Secrets": "CS",
        "Prisoner of Azkaban": "PA", "Goblet of Fire": "GF",
        "Order of the Phoenix": "OP", "Half-Blood Prince": "HBP",
        "Deathly Hallows": "DH",
    }.get(book, book) if show_book else None
    attr_text = f"\u2014 {character}"
    if short_book:
        attr_text += f", {short_book}"
    bbox = draw.textbbox((0, 0), attr_text, font=attr_font)
    attr_w = bbox[2] - bbox[0]
    draw.text((start_x + (400 - attr_w) // 2, HEIGHT - attr_bar_h + (attr_bar_h - (bbox[3] - bbox[1])) // 2), attr_text, fill=h["secondary_light"], font=attr_font)


def render_quote(data: dict[str, Any], quotes: list[dict[str, Any]]) -> Image.Image:
    layout_mode = data.get("layout_mode", "full_screen")
    house_accent = data.get("house_accent", "auto")
    show_house = bool(data.get("show_house_banner", True))
    show_book = bool(data.get("show_source_book", True))

    quote_data = pick_random_quote(quotes)
    quote_text = quote_data["text"]
    character = quote_data["character"]
    book = quote_data.get("book")
    q_house = quote_data.get("house")

    display_house = q_house
    if house_accent != "auto":
        display_house = house_accent if house_accent != "none" else None
    if not show_house:
        display_house = None

    img = Image.new("RGB", (WIDTH, HEIGHT), (20, 15, 10))
    draw = ImageDraw.Draw(img)

    if layout_mode == "half_vertical":
        render_half_vertical(draw, quote_text, character, book, display_house, show_book)
    else:
        render_full_screen(draw, quote_text, character, book, display_house, show_book)

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
    return render_quote(data, quotes)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a Harry Potter quote to a seven-colour indexed PNG.")
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
