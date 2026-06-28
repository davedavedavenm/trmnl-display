#!/usr/bin/env python3
"""
render_sonos_sidecar.py — ACeP 7-colour sidecar renderer for the Sonos Now Playing screen.

Reads the current Sonos payload from LaraPaper's plugin database (or a --payload JSON file),
fetches album art from the base64 data URI already embedded in the payload, and renders a
rich 800x480 indexed/paletted PNG using the Spectra ACeP palette.

Output: sidecar_sonos_local_next.png  (800×480, mode=P, 7-colour palette)

Usage:
    python3 render_sonos_sidecar.py                        # reads from LaraPaper DB
    python3 render_sonos_sidecar.py --payload payload.json # reads from JSON file
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
from io import BytesIO
from pathlib import Path
from textwrap import shorten

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

# ---------------------------------------------------------------------------
# ACeP Spectra palette  (7 colours + dithered orange = 8 entries)
# ---------------------------------------------------------------------------
BLACK   = (0,   0,   0)
WHITE   = (255, 255, 255)
RED     = (255, 0,   0)
GREEN   = (0,   255, 0)
BLUE    = (0,   0,   255)
YELLOW  = (255, 255, 0)
ORANGE  = (255, 140, 0)   # dithered R+Y on panel; used as accent

PALETTE_COLORS = [BLACK, WHITE, RED, GREEN, BLUE, YELLOW, ORANGE,
                  (128, 0, 0), (0, 128, 0), (0, 0, 128)]

def _build_palette_image() -> Image.Image:
    """Build a small P-mode reference image carrying our palette."""
    p = Image.new("P", (1, 1))
    flat = []
    for c in PALETTE_COLORS:
        flat.extend(c)
    flat += [0] * (768 - len(flat))
    p.putpalette(flat)
    return p

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
W, H = 800, 480
SCRIPT_DIR = Path(__file__).resolve().parent
OUT_DIR    = SCRIPT_DIR / "tmp"
OUT_NAME   = "sidecar_sonos_local_next.png"
SOURCE_NAME = "sidecar_sonos_local_source_next.png"

LARAPAPER_CONTAINER = os.getenv("TRMNL_LARAPAPER_CONTAINER", "larapaper-app-1")
PLUGIN_NAME         = os.getenv("TRMNL_SONOS_PLUGIN_NAME", "Sonos Local")

# Font paths (Pillow default if not found)
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
]
FONT_REGULAR_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
]

def _find_font(candidates: list[str], size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()

# ---------------------------------------------------------------------------
# Payload loading
# ---------------------------------------------------------------------------

def load_payload_from_db() -> dict:
    """Read the latest Sonos payload from LaraPaper's SQLite DB via docker exec."""
    php = (
        "require '/var/www/html/vendor/autoload.php';"
        "$app = require '/var/www/html/bootstrap/app.php';"
        "$app->make(Illuminate\\Contracts\\Console\\Kernel::class)->bootstrap();"
        f"$p = DB::table('plugins')->where('name', '{PLUGIN_NAME}')->first();"
        "echo $p ? ($p->data_payload ?? '{}') : '{}';"
    )
    result = subprocess.run(
        ["docker", "exec", LARAPAPER_CONTAINER, "php", "-r", php],
        capture_output=True, text=True, timeout=15,
    )
    raw = (result.stdout or "").strip()
    if not raw:
        return {}
    data = json.loads(raw)
    # Unwrap merge_variables wrapper if present
    return data.get("merge_variables", data)


def load_payload_from_file(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("merge_variables", data)

# ---------------------------------------------------------------------------
# Album art processing
# ---------------------------------------------------------------------------

def _load_album_art(payload: dict) -> Image.Image | None:
    """Try to load album art from the base64 data URI variants in the payload."""
    for key in ("album_art_balanced_data_uri", "album_art_data_uri",
                "album_art_vivid_data_uri", "album_art_mono_data_uri"):
        uri = payload.get(key, "")
        if uri and uri.startswith("data:image"):
            try:
                _, b64 = uri.split(",", 1)
                img = Image.open(BytesIO(base64.b64decode(b64))).convert("RGB")
                return img
            except Exception as e:
                print(f"Warning: could not decode {key}: {e}", file=sys.stderr)
    return None


def _dominant_color(img: Image.Image) -> tuple[int, int, int]:
    """Return the dominant colour from a small sample of the image."""
    small = img.copy().convert("RGB")
    small.thumbnail((50, 50))
    pixels = list(small.getdata())
    # Simple average — good enough for accent colour selection
    r = sum(p[0] for p in pixels) // len(pixels)
    g = sum(p[1] for p in pixels) // len(pixels)
    b = sum(p[2] for p in pixels) // len(pixels)
    return (r, g, b)


def _snap_to_palette(color: tuple[int, int, int]) -> tuple[int, int, int]:
    """Snap an RGB colour to the nearest ACeP palette entry."""
    def dist(a, b):
        return sum((a[i] - b[i]) ** 2 for i in range(3))
    return min(PALETTE_COLORS, key=lambda c: dist(c, color))

# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

def _draw_text_fitted(draw: ImageDraw.Draw, text: str, x: int, y: int,
                      max_width: int, font_bold, color: tuple) -> int:
    """Draw text, truncating with ellipsis if too wide. Returns height used."""
    while text:
        bbox = draw.textbbox((0, 0), text, font=font_bold)
        tw = bbox[2] - bbox[0]
        if tw <= max_width:
            break
        text = text[:-2] + "…"
    draw.text((x, y), text, fill=color, font=font_bold)
    bbox = draw.textbbox((x, y), text, font=font_bold)
    return bbox[3] - bbox[1]

# ---------------------------------------------------------------------------
# Main renderer
# ---------------------------------------------------------------------------

def render(payload: dict, out_path: Path, source_path: Path) -> None:
    title  = payload.get("title", "Nothing Playing")
    artist = payload.get("artist", "Unknown Artist")
    album  = payload.get("album", "")
    state  = payload.get("state", "STOPPED")
    room   = payload.get("room_name", "Sonos")
    source = payload.get("source", "")
    updated = payload.get("updated_at", "")
    group_rooms = payload.get("group_rooms", [])
    same_content_rooms = payload.get("same_content_rooms", [])

    # Rooms display string
    other_rooms = [r for r in group_rooms if r.lower() != room.lower()]
    if same_content_rooms:
        rooms_str = " · ".join(same_content_rooms)
    elif other_rooms:
        rooms_str = " · ".join(other_rooms)
    else:
        rooms_str = room

    # Load album art
    art = _load_album_art(payload)

    # Choose accent colours based on dominant art colour if available
    if art:
        dom = _dominant_color(art)
        art_accent = _snap_to_palette(dom)
        # Ensure it's not black (too dark to be useful as accent)
        if art_accent == BLACK:
            art_accent = YELLOW
    else:
        art_accent = YELLOW

    # ---------------------------------------------------------------------------
    # Build canvas (RGB first for quality, convert to palette at end)
    # ---------------------------------------------------------------------------
    canvas = Image.new("RGB", (W, H), BLACK)
    draw   = ImageDraw.Draw(canvas)

    # Fonts
    font_huge   = _find_font(FONT_CANDIDATES, 52)
    font_large  = _find_font(FONT_CANDIDATES, 38)
    font_medium = _find_font(FONT_CANDIDATES, 24)
    font_small  = _find_font(FONT_CANDIDATES, 17)
    font_tiny   = _find_font(FONT_CANDIDATES, 14)
    font_reg_sm = _find_font(FONT_REGULAR_CANDIDATES, 16)

    # ---------------------------------------------------------------------------
    # Layout constants
    # ---------------------------------------------------------------------------
    HEADER_H   = 44
    PADDING    = 18
    ART_W      = 340
    ART_H      = H - HEADER_H - PADDING        # fills rest of left column
    INFO_X     = ART_W + PADDING * 2
    INFO_W     = W - INFO_X - PADDING

    # ---------------------------------------------------------------------------
    # Header bar
    # ---------------------------------------------------------------------------
    draw.rectangle([(0, 0), (W, HEADER_H)], fill=BLACK)

    # Sonos logo area (simple text badge)
    badge_x = PADDING
    draw.rectangle([(badge_x, 8), (badge_x + 66, 36)], fill=RED)
    draw.text((badge_x + 8, 10), "SONOS", fill=WHITE, font=font_small)

    # Room name
    draw.text((badge_x + 78, 10), room.upper(), fill=WHITE, font=font_medium)

    # State badge (right side)
    state_color = GREEN if state == "PLAYING" else ORANGE if state == "PAUSED" else RED
    state_text  = state
    sb = draw.textbbox((0, 0), state_text, font=font_small)
    sw = sb[2] - sb[0]
    state_x = W - PADDING - sw - 16
    draw.rectangle([(state_x - 8, 8), (state_x + sw + 8, 36)], fill=state_color)
    draw.text((state_x, 10), state_text, fill=BLACK if state_color == YELLOW else WHITE, font=font_small)

    # Updated at (left of state)
    if updated:
        draw.text((state_x - 120, 14), f"Updated {updated}", fill=(160, 160, 160), font=font_tiny)

    # Divider
    draw.rectangle([(0, HEADER_H), (W, HEADER_H + 2)], fill=art_accent)

    # ---------------------------------------------------------------------------
    # Album art — left column
    # ---------------------------------------------------------------------------
    ART_Y = HEADER_H + 2
    art_rect = [(0, ART_Y), (ART_W, ART_Y + ART_H)]

    if art:
        # Resize to fill the left column
        art_fit = art.copy()
        art_fit = art_fit.resize((ART_W, ART_H), Image.LANCZOS)
        # Subtle vignette: slightly darken edges so text area separates cleanly
        vignette = Image.new("RGB", (ART_W, ART_H), BLACK)
        canvas.paste(art_fit, (0, ART_Y))
        # Thin gradient overlay on right edge of art for visual separation
        for i in range(40):
            alpha = int(180 * (i / 40))
            draw.line([(ART_W - 40 + i, ART_Y), (ART_W - 40 + i, ART_Y + ART_H)],
                      fill=(0, 0, 0, alpha) if hasattr(draw, 'alpha') else BLACK)
    else:
        # No art: coloured placeholder
        draw.rectangle(art_rect, fill=(30, 30, 30))
        draw.text((ART_W // 2 - 40, ART_Y + ART_H // 2 - 20), "♪", fill=art_accent, font=font_huge)

    # Vertical divider
    draw.rectangle([(ART_W, ART_Y), (ART_W + 3, ART_Y + ART_H)], fill=art_accent)

    # ---------------------------------------------------------------------------
    # Info column — right side
    # ---------------------------------------------------------------------------
    iy = ART_Y + PADDING

    # Track title — big, dominant
    title_display = shorten(title, width=28, placeholder="…")
    title_lines = []
    words = title_display.split()
    line = ""
    for word in words:
        test = (line + " " + word).strip()
        bb = draw.textbbox((0, 0), test, font=font_large)
        if bb[2] - bb[0] > INFO_W:
            if line:
                title_lines.append(line)
            line = word
        else:
            line = test
    if line:
        title_lines.append(line)

    for tl in title_lines[:2]:  # max 2 lines
        draw.text((INFO_X, iy), tl, fill=WHITE, font=font_large)
        iy += 46

    iy += 6

    # Artist — yellow
    artist_display = shorten(artist, width=34, placeholder="…")
    draw.text((INFO_X, iy), artist_display, fill=YELLOW, font=font_medium)
    iy += 34

    # Album — orange/small
    if album:
        album_display = shorten(album.upper(), width=42, placeholder="…")
        draw.text((INFO_X, iy), album_display, fill=ORANGE, font=font_tiny)
        iy += 24

    iy += 20

    # Divider line
    draw.rectangle([(INFO_X, iy), (W - PADDING, iy + 1)], fill=(60, 60, 60))
    iy += 14

    # Info cards row
    CARD_W = (INFO_W - 12) // 2
    CARD_H = 80

    def draw_card(cx, cy, label, value, accent_col):
        draw.rectangle([(cx, cy), (cx + CARD_W, cy + CARD_H)], fill=(18, 18, 18))
        draw.rectangle([(cx, cy), (cx + 5, cy + CARD_H)], fill=accent_col)
        draw.text((cx + 14, cy + 10), label.upper(), fill=(140, 140, 140), font=font_tiny)
        # Value — may need wrapping
        val_display = shorten(str(value), width=22, placeholder="…")
        draw.text((cx + 14, cy + 32), val_display, fill=WHITE, font=font_reg_sm)

    # Source card
    draw_card(INFO_X, iy, "Source", source or "Unknown", GREEN)

    # Rooms card
    if len(other_rooms) > 0 or len(group_rooms) > 1:
        draw_card(INFO_X + CARD_W + 12, iy, "Rooms", rooms_str, BLUE)

    iy += CARD_H + 16

    # Divider
    draw.rectangle([(INFO_X, iy), (W - PADDING, iy + 1)], fill=(40, 40, 40))
    iy += 12

    # Music note decorative bar at bottom
    notes = "♪  ♫  ♪  ♫  ♪  ♫  ♪  ♫  ♪  ♫  ♪  ♫  ♪"
    draw.text((INFO_X, iy), notes, fill=(45, 45, 45), font=font_reg_sm)

    # ---------------------------------------------------------------------------
    # Save source (RGB) for reference, then quantize to ACeP palette
    # ---------------------------------------------------------------------------
    out_dir = out_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    canvas.save(str(source_path))
    print(f"Source: {source_path}")

    # Quantize to 7-colour ACeP palette
    palette_ref = _build_palette_image()
    panel = canvas.quantize(palette=palette_ref, dither=Image.Dither.FLOYDSTEINBERG)
    panel.save(str(out_path))

    size = out_path.stat().st_size
    print(f"Panel:  {out_path}")
    print(f"Size:   {W} x {H}, mode=P  ({size} bytes)")
    print(f"Track:  {title} — {artist}")
    print(f"State:  {state} in {room}")


# ---------------------------------------------------------------------------
# Sidecar upload to LaraPaper
# ---------------------------------------------------------------------------

def upload_sidecar(out_path: Path) -> None:
    update_script = os.getenv(
        "TRMNL_SONOS_SIDECAR_UPDATE_SCRIPT",
        str(SCRIPT_DIR / "trmnl_update_sonos_sidecar_image.sh"),
    )
    env = {
        **os.environ,
        "TRMNL_SONOS_SIDECAR_IMAGE_PATH": str(out_path),
        "TRMNL_SONOS_PLUGIN_NAME": PLUGIN_NAME,
    }
    result = subprocess.run(
        [update_script], env=env, capture_output=True, text=True, timeout=30,
    )
    if result.stdout:
        print(result.stdout.strip())
    if result.returncode != 0:
        print(f"Upload failed (rc={result.returncode}): {result.stderr.strip()}", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--payload", help="Path to JSON payload file (skips DB lookup)")
    parser.add_argument("--no-upload", action="store_true", help="Render only, do not upload")
    args = parser.parse_args()

    if args.payload:
        payload = load_payload_from_file(args.payload)
    else:
        payload = load_payload_from_db()

    if not payload:
        print("Warning: empty payload, rendering fallback screen", file=sys.stderr)

    out_path    = OUT_DIR / OUT_NAME
    source_path = OUT_DIR / SOURCE_NAME

    render(payload, out_path, source_path)

    if not args.no_upload:
        upload_sidecar(out_path)


if __name__ == "__main__":
    main()
