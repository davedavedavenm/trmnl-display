#!/usr/bin/env python3
"""
Jen Commute — Colour Sidecar Renderer
Optimised for 7-color ACeP e-ink (Spectra), 800x480.
Reads the plugin's webhook payload from the LaraPaper DB and renders
a deliberate seven-colour image that the BYOS polling client fetches.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

OUT_DIR = Path(__file__).resolve().parent / "tmp"
OUT_PATH = OUT_DIR / "sidecar_jen_commute_next.png"
SOURCE_PATH = OUT_DIR / "sidecar_jen_commute_source_next.png"
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

PANEL_PALETTE = [BLACK, WHITE, RED, YELLOW, BLUE, GREEN]


def closest_panel_color(rgb: tuple[int, int, int] | list[int]) -> tuple[int, int, int]:
    if not rgb or len(rgb) < 3:
        return BLACK
    min_dist = float("inf")
    best = BLACK
    for pc in PANEL_PALETTE:
        dist = sum((c1 - c2) ** 2 for c1, c2 in zip(rgb, pc))
        if dist < min_dist:
            min_dist = dist
            best = pc
    return best


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    base = Path(__file__).resolve().parent
    local = base / "fonts" / ("Outfit-Bold.ttf" if bold else "Outfit-Regular.ttf")
    if local.exists():
        try:
            return ImageFont.truetype(str(local), size)
        except OSError:
            pass
    for c in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]:
        try:
            return ImageFont.truetype(c, size)
        except OSError:
            pass
    return ImageFont.load_default()


def load_data_from_db() -> tuple[dict[str, Any], dict[str, Any], int]:
    db_paths = [
        "/var/www/html/database/storage/database.sqlite",
        str(Path.home() / "tmp" / "larapaper.sqlite"),
    ]
    for p in db_paths:
        if Path(p).exists():
            try:
                db = sqlite3.connect(p)
                row = db.execute(
                    "SELECT data_payload, configuration, dark_mode FROM plugins WHERE id = 22"
                ).fetchone()
                db.close()
                if row:
                    raw_payload, raw_config, dark_val = row
                    data = {}
                    config = {}
                    if raw_payload:
                        payload = json.loads(raw_payload)
                        data = payload.get("merge_variables", payload)
                    if raw_config:
                        config = json.loads(raw_config)
                    return data, config, dark_val or 0
            except Exception as e:
                print(f"DB load error {p}: {e}")
    return {}, {}, 0


def load_payload(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    if isinstance(raw, dict) and isinstance(raw.get("merge_variables"), dict):
        return raw["merge_variables"]
    return raw if isinstance(raw, dict) else {}


def wrap_text(text: str, f, max_w: int, draw: ImageDraw.ImageDraw) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur = ""
    for w in words:
        test = cur + (" " if cur else "") + w
        bbox = draw.textbbox((0, 0), test, font=f)
        if bbox[2] - bbox[0] <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def get_urgency(eta: int) -> tuple[tuple[int, int, int], str]:
    if eta <= 0:
        return GREEN, "ARRIVING"
    if eta <= 10:
        return GREEN, "ALMOST HOME"
    if eta <= 25:
        return BLUE, "EN ROUTE"
    if eta <= 45:
        return ORANGE, "COMMUTING"
    return RED, "LONG COMMUTE"


def get_state_color(state: str) -> tuple[int, int, int]:
    return {
        "journey_started": BLUE,
        "via_clean_bean": ORANGE,
        "near_home": GREEN,
        "at_work": YELLOW,
        "completed": DIM,
    }.get(state, DIM)


def get_prep_color(status: str) -> tuple[int, int, int]:
    s = status.lower().strip()
    if "active" in s:
        return GREEN
    if s == "needed" or "is needed" in s or "preparation needed" in s:
        return YELLOW
    return (20, 20, 20)


def draw_arrow(
    draw: ImageDraw.ImageDraw,
    cx: int,
    cy: int,
    half_w: int,
    half_h: int,
    pointing_left: bool,
    color: tuple[int, int, int],
) -> None:
    """Draw a solid triangular arrow.

    The panel font (Outfit) has no glyph for the Unicode arrows, so drawing the
    triangle directly avoids the missing-glyph 'tofu' box that appeared on screen.
    pointing_left=True means heading home (←); False means outbound (→).
    """
    if pointing_left:
        pts = [(cx - half_w, cy), (cx + half_w, cy - half_h), (cx + half_w, cy + half_h)]
    else:
        pts = [(cx + half_w, cy), (cx - half_w, cy - half_h), (cx - half_w, cy + half_h)]
    draw.polygon(pts, fill=color)


def render(data: dict[str, Any], config: dict[str, Any], dark_mode: int) -> Image.Image:
    import math

    show_prep = config.get("show_home_prep", True)

    headline = str(data.get("headline", "Commute Standby"))
    heading_home = str(data.get("heading_home", "No"))
    commute_state = str(data.get("commute_state", "idle"))
    updated_at = str(data.get("updated_at", ""))
    route_label = str(data.get("route_label", "Unknown"))
    home_prep_status = str(data.get("home_prep_status", "Not Needed"))

    try:
        eta_minutes = int(round(float(data.get("eta_minutes", 0))))
    except (ValueError, TypeError):
        eta_minutes = 0

    try:
        distance_km = float(data.get("distance_km", 0))
    except (ValueError, TypeError):
        distance_km = 0.0

    urgency_color, urgency_label = get_urgency(eta_minutes)
    state_color = get_state_color(commute_state)
    prep_color = get_prep_color(home_prep_status)

    # ORANGE remaps to YELLOW on the 6-colour panel, so it needs dark text too.
    urgency_fg = BLACK if urgency_color in (YELLOW, GREEN, WHITE, ORANGE) else WHITE
    state_fg = BLACK if state_color in (YELLOW, GREEN, WHITE, ORANGE) else WHITE

    img = Image.new("RGB", (WIDTH, HEIGHT), WHITE)
    draw = ImageDraw.Draw(img)

    # ==================== LEFT 60%: Bold geometric ETA ====================
    LEFT_W = 480

    # Thick vertical color strip on far left (urgency color)
    draw.rectangle([0, 0, 14, HEIGHT], fill=urgency_color)

    # Headline at top — BLACK text on WHITE, the accent is the colored strip
    draw.text((30, 20), headline.upper(), fill=BLACK, font=font(26, bold=True))
    pointing_home = heading_home.lower() == "yes"
    draw_arrow(draw, LEFT_W - 30, 36, 18, 14, pointing_home, BLACK)

    # === GIANT URGENCY CIRCLE ===
    cx, cy, cr = 250, 230, 135
    # Outer ring (urgency color)
    draw.ellipse((cx - cr - 8, cy - cr - 8, cx + cr + 8, cy + cr + 8), fill=urgency_color)
    # Inner WHITE circle
    draw.ellipse((cx - cr + 12, cy - cr + 12, cx + cr - 12, cy + cr - 12), fill=WHITE)

    # ETA number inside the ring — BLACK text on WHITE for maximum readability
    eta_str = str(eta_minutes) if eta_minutes > 0 else "?"
    eta_font_size = 100 if len(eta_str) <= 2 else 80
    draw.text((cx, cy - 15), eta_str, fill=BLACK, font=font(eta_font_size, bold=True), anchor="mm")
    draw.text((cx, cy + 50), "MINUTES", fill=BLACK, font=font(18, bold=True), anchor="mm")

    # Urgency label — BLACK text on a colored pill (not colored text on white)
    ulabel_font = font(14, bold=True)
    ulabel_w = int(draw.textlength(urgency_label, font=ulabel_font)) + 24
    ux = cx - ulabel_w // 2
    uy = cy + cr + 16
    draw.rounded_rectangle([(ux, uy), (ux + ulabel_w, uy + 30)], radius=6, fill=urgency_color)
    ulabel_fg = BLACK if urgency_color in (YELLOW, GREEN) else WHITE
    draw.text((ux + ulabel_w // 2, uy + 15), urgency_label, fill=ulabel_fg, font=ulabel_font, anchor="mm")

    # === ROUTE DIAGRAM at bottom of left pane ===
    route_y = HEIGHT - 52
    rx0 = 30
    rx1 = LEFT_W - 30
    # Route line — traveled portion GREEN, remaining portion urgency color
    if eta_minutes > 0:
        progress = max(0.05, min(0.95, 1.0 - (eta_minutes / 60.0)))
    else:
        progress = 0.5
    car_x = rx0 + int((rx1 - rx0) * progress)
    # Traveled (behind car) — GREEN
    draw.line([(rx0 + 10, route_y), (car_x, route_y)], fill=GREEN, width=3)
    # Remaining (ahead of car) — urgency color
    draw.line([(car_x, route_y), (rx1 - 10, route_y)], fill=urgency_color, width=3)
    # Work endpoint (RED dot)
    draw.ellipse((rx0 - 8, route_y - 8, rx0 + 8, route_y + 8), fill=RED, outline=BLACK, width=1)
    draw.text((rx0, route_y - 22), "WORK", fill=BLACK, font=font(10, bold=True), anchor="ma")
    # Home endpoint (GREEN dot)
    draw.ellipse((rx1 - 8, route_y - 8, rx1 + 8, route_y + 8), fill=GREEN, outline=BLACK, width=1)
    draw.text((rx1, route_y - 22), "HOME", fill=BLACK, font=font(10, bold=True), anchor="ma")
    # Car body — BLACK with urgency-colored outline
    draw.rounded_rectangle([(car_x - 12, route_y - 5), (car_x + 12, route_y + 4)], radius=2, fill=BLACK, outline=urgency_color, width=2)
    # Wheels
    draw.ellipse((car_x - 9, route_y + 3, car_x - 4, route_y + 8), fill=BLACK)
    draw.ellipse((car_x + 4, route_y + 3, car_x + 9, route_y + 8), fill=BLACK)
    # Cabin
    draw.rounded_rectangle([(car_x - 6, route_y - 9), (car_x + 6, route_y - 3)], radius=1, fill=BLACK, outline=urgency_color, width=1)

    # ==================== DIVIDER ====================
    draw.rectangle([LEFT_W, 0, LEFT_W + 3, HEIGHT], fill=BLACK)

    # ==================== RIGHT 40%: Colored status bands ====================
    rx = LEFT_W + 5
    rw = WIDTH - LEFT_W - 10

    # --- Band 1: Route info (RED band — transport/road colour) ---
    b1_h = 120
    draw.rectangle([rx, 0, WIDTH, b1_h], fill=RED)
    draw.text((rx + 16, 14), "ROUTE", fill=WHITE, font=font(12, bold=True))
    route_lines = wrap_text(route_label, font(17, bold=True), rw - 32, draw)
    ry = 36
    for line in route_lines[:3]:
        draw.text((rx + 16, ry), line, fill=WHITE, font=font(17, bold=True))
        ry += 22
    if distance_km > 0:
        draw.text((rx + 16, b1_h - 24), f"{distance_km:.1f} km remaining", fill=WHITE, font=font(14, bold=True))

    # --- Band 2: Journey state (GREEN for near home, ORANGE for clean bean, BLUE for started, RED for delayed) ---
    b2_y = b1_h
    b2_h = 110
    if commute_state == "near_home":
        journey_bg = GREEN
    elif commute_state == "via_clean_bean":
        journey_bg = ORANGE
    elif commute_state == "journey_started":
        journey_bg = BLUE
    elif commute_state == "completed":
        journey_bg = GREEN
    else:
        journey_bg = ORANGE
    journey_fg = BLACK if journey_bg in (YELLOW, GREEN, WHITE, ORANGE) else WHITE

    draw.rectangle([rx, b2_y, WIDTH, b2_y + b2_h], fill=journey_bg)
    draw.text((rx + 16, b2_y + 14), "JOURNEY", fill=journey_fg, font=font(12, bold=True))
    state_display = commute_state.replace("_", " ").upper()
    state_fs = 18 if len(state_display) < 14 else 14
    draw.text((rx + 16, b2_y + 36), state_display, fill=journey_fg, font=font(state_fs, bold=True))
    sub = "Heading Home" if heading_home.lower() == "yes" else "Standby"
    draw.text((rx + 16, b2_y + 64), sub.upper(), fill=journey_fg, font=font(14, bold=True))
    draw_arrow(draw, WIDTH - 32, b2_y + 55, 22, 22, pointing_home, journey_fg)

    # --- Band 3: Home prep (GREEN=active, RED=needed, WHITE=not needed) ---
    if show_prep:
        b3_y = b2_y + b2_h
        b3_h = 110
        if "active" in home_prep_status.lower():
            prep_bg = GREEN
            prep_text_fg = BLACK
        elif home_prep_status.lower().strip() == "needed":
            prep_bg = RED
            prep_text_fg = WHITE
        else:
            prep_bg = WHITE
            prep_text_fg = BLACK

        draw.rectangle([rx, b3_y, WIDTH, b3_y + b3_h], fill=prep_bg, outline=BLACK, width=1)
        draw.text((rx + 16, b3_y + 14), "HOME PREP", fill=prep_text_fg, font=font(12, bold=True))
        draw.text((rx + 16, b3_y + 36), home_prep_status.upper(), fill=prep_text_fg, font=font(18, bold=True))

        # Coloured status dot / icon
        if prep_bg == WHITE:
            draw.ellipse((WIDTH - 36, b3_y + 16, WIDTH - 16, b3_y + 36), fill=GREEN)
        else:
            draw.ellipse((WIDTH - 36, b3_y + 16, WIDTH - 16, b3_y + 36), fill=prep_text_fg)

    # --- Band 4: Footer (WHITE) ---
    b4_y = b2_y + b2_h + (110 if show_prep else 0)
    draw.rectangle([rx, b4_y, WIDTH, HEIGHT], fill=WHITE)
    draw.text((rx + 16, b4_y + 12), f"Updated {updated_at}", fill=BLACK, font=font(11, bold=True))
    if distance_km > 0:
        draw.text((rx + 16, b4_y + 30), f"Distance: {distance_km:.1f} km", fill=BLACK, font=font(11))
    # Small colored urgency dot in footer
    draw.ellipse((WIDTH - 30, b4_y + 16, WIDTH - 18, b4_y + 28), fill=urgency_color)
    draw.text((WIDTH - 16, HEIGHT - 16), "JEN COMMUTE", fill=DIM, font=font(10, bold=True), anchor="ra")

    return img


def remap_to_panel_palette(img: Image.Image) -> Image.Image:
    palette = Image.new("P", (1, 1))
    flat: list[int] = []
    for rgb in PANEL_PALETTE:
        flat.extend(rgb)
    flat.extend([0, 0, 0] * (256 - len(PANEL_PALETTE)))
    palette.putpalette(flat)
    return img.quantize(palette=palette, dither=0)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Render Jen Commute sidecar to a seven-colour indexed PNG.")
    parser.add_argument("--payload", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=OUT_PATH)
    parser.add_argument("--source-output", type=Path, default=SOURCE_PATH)
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.source_output.parent.mkdir(parents=True, exist_ok=True)

    if args.payload:
        data = load_payload(args.payload)
        config = {}
        dark_mode = 0
    else:
        data, config, dark_mode = load_data_from_db()

    source = render(data, config, dark_mode)
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
