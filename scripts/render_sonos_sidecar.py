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
    """Read the latest Sonos payload + plugin config from LaraPaper's DB."""
    php = (
        "require '/var/www/html/vendor/autoload.php';"
        "$app = require '/var/www/html/bootstrap/app.php';"
        "$app->make(Illuminate\\Contracts\\Console\\Kernel::class)->bootstrap();"
        f"$p = DB::table('plugins')->where('name', '{PLUGIN_NAME}')->first();"
        "echo json_encode(['payload' => $p ? ($p->data_payload ?? '{}') : '{}',"
        "                 'config'  => $p ? ($p->configuration ?? '{}') : '{}']);"
    )
    result = subprocess.run(
        ["docker", "exec", LARAPAPER_CONTAINER, "php", "-r", php],
        capture_output=True, text=True, timeout=15,
    )
    raw = (result.stdout or "").strip()
    if not raw:
        return {}
    bundle = json.loads(raw)
    data = json.loads(bundle.get("payload", "{}"))
    data = data.get("merge_variables", data)
    config = json.loads(bundle.get("config", "{}"))
    for k in ("show_album", "show_album_art", "show_next_tracks",
              "preferred_room", "album_art_mode"):
        if k in config:
            data.setdefault(k, config[k])
    return data


def load_payload_from_file(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("merge_variables", data)

# ---------------------------------------------------------------------------
# Album art processing
# ---------------------------------------------------------------------------

def _load_album_art(payload: dict) -> Image.Image | None:
    """Try to load album art from the base64 data URI in the payload.

    Uses the album_art_mode config value (default 'raw') to select the variant:
      raw → album_art_data_uri
      vivid → album_art_vivid_data_uri
      balanced → album_art_balanced_data_uri
      mono → album_art_mono_data_uri
    If the preferred variant is unavailable, falls back through the full list.
    """
    mode = str(payload.get("album_art_mode", "raw")).strip().lower()
    variant_keys = {
        "raw":      "album_art_data_uri",
        "vivid":    "album_art_vivid_data_uri",
        "balanced": "album_art_balanced_data_uri",
        "mono":     "album_art_mono_data_uri",
    }
    preferred_key = variant_keys.get(mode, "album_art_data_uri")
    all_keys = [preferred_key] + [k for k in variant_keys.values() if k != preferred_key]

    for key in all_keys:
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

    # Load album art (gated by show_album_art from plugin config; default true)
    show_album_art = str(payload.get("show_album_art", True)).lower() not in ("false", "0", "")
    art = _load_album_art(payload) if show_album_art else None

    show_album = str(payload.get("show_album", True)).lower() not in ("false", "0", "")
    show_next_tracks = str(payload.get("show_next_tracks", True)).lower() not in ("false", "0", "")

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
    # Info column — right side, premium Swiss-style light theme
    # ---------------------------------------------------------------------------
    # Right panel background — clean solid white for maximum contrast & paper feel
    draw.rectangle([(ART_W + 3, ART_Y), (W, H)], fill=WHITE)

    iy = ART_Y + 24

    # ── Title ──
    title_display = shorten(title, width=26, placeholder="…")
    title_lines = []
    line = ""
    for word in title_display.split():
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

    for tl in title_lines[:2]:
        draw.text((INFO_X, iy), tl, fill=BLACK, font=font_large)
        iy += 44

    iy += 6

    # ── Artist ──
    artist_display = shorten(artist, width=32, placeholder="…")
    draw.text((INFO_X, iy), artist_display, fill=RED, font=font_medium)
    iy += 30

    # ── Album ──
    if show_album and album:
        album_display = shorten(album, width=40, placeholder="…")
        draw.text((INFO_X, iy), album_display, fill=(100, 100, 100), font=font_small)
        iy += 24

    iy += 14

    # Divider line
    draw.rectangle([(INFO_X, iy), (W - PADDING, iy + 1)], fill=(220, 220, 220))
    iy += 18

    # ── Widgets (Source & Rooms) ──
    # Stacked vertically, using light grey cards with thick color accent bars
    CARD_W = INFO_W
    CARD_H = 68

    def draw_light_card(cy, label, value, accent_col):
        # Card body (very light grey)
        draw.rectangle([(INFO_X, cy), (INFO_X + CARD_W, cy + CARD_H)], fill=(245, 245, 245))
        # Thin outer border
        draw.rectangle([(INFO_X, cy), (INFO_X + CARD_W, cy + CARD_H)], outline=(220, 220, 220), width=1)
        # Thick left accent bar
        draw.rectangle([(INFO_X, cy), (INFO_X + 6, cy + CARD_H)], fill=accent_col)
        # Label
        draw.text((INFO_X + 16, cy + 8), label.upper(), fill=(120, 120, 120), font=font_tiny)
        # Value (Black text, highly legible)
        val_display = shorten(str(value), width=28, placeholder="…")
        draw.text((INFO_X + 16, cy + 28), val_display, fill=BLACK, font=font_medium)

    # Source widget
    draw_light_card(iy, "Source", source or "Unknown", GREEN)
    iy += CARD_H + 12

    # Rooms widget
    if group_rooms:
        draw_light_card(iy, "Playing In", rooms_str, BLUE)
        iy += CARD_H + 12

    # ── Next Tracks ──
    next_tracks = payload.get("next_tracks", [])
    if show_next_tracks and next_tracks:
        next_y = iy
        num_tracks = min(len(next_tracks), 3)
        for idx in range(num_tracks):
            track = next_tracks[idx]
            track_title = shorten(track.get("title", ""), width=32, placeholder="…")
            track_artist = shorten(track.get("artist", ""), width=28, placeholder="…")
            draw.text((INFO_X, next_y), f"{idx + 1}. {track_title}", fill=BLACK, font=font_reg_sm)
            next_y += 20
            if track_artist:
                draw.text((INFO_X + 16, next_y), track_artist, fill=(120, 120, 120), font=font_tiny)
                next_y += 16
            next_y += 4

    # ── Footer strip ──
    bottom_y = H - 28
    draw.rectangle([(ART_W + 3, bottom_y), (W, H)], fill=(240, 240, 240))
    if updated:
        draw.text((INFO_X, bottom_y + 6), f"Updated {updated}", fill=(120, 120, 120), font=font_tiny)

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
