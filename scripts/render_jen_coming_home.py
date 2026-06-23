#!/usr/bin/env python3
"""
Jen Coming Home — colour sidecar renderer.

Bold, glanceable "she's on her way back from work" screen for the 6-colour
Spectra panel (800x480). Makes the Work -> Home journey the hero: where Jen is,
how far, when she's home, and whether the house needs prep.

Data source: the "Jen Coming Home" LaraPaper webhook plugin (data_strategy=webhook),
populated with real Waze/location data pushed from Home Assistant. Falls back to a
--payload JSON file for offline testing.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

PLUGIN_NAME = "Jen Coming Home"
OUT_DIR = Path(__file__).resolve().parent / "tmp"
OUT_PATH = OUT_DIR / "sidecar_jen_coming_home_next.png"
SOURCE_PATH = OUT_DIR / "sidecar_jen_coming_home_source_next.png"

WIDTH, HEIGHT = 800, 480

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
PANEL_PALETTE = [BLACK, WHITE, RED, YELLOW, BLUE, GREEN]

# Jen's work (Radstock) — the start of the homeward journey. Anchors the
# Work->Home progress from her real GPS instead of the noisy ETA. The payload's
# map_url destination is HOME; this is the opposite (work) end. Editable.
WORK_ANCHOR = (0.0000000, -0.0000000)


def _haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    import math

    R = 6371.0
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def _latlon(s: str) -> tuple[float, float] | None:
    import urllib.parse

    try:
        lat, lon = urllib.parse.unquote(s).split(",")
        return float(lat), float(lon)
    except Exception:
        return None


def coords_from_map_url(url: str) -> tuple[tuple[float, float] | None, tuple[float, float] | None]:
    """Return (current_position, home) parsed from the Google Maps directions URL."""
    import urllib.parse

    try:
        q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        return _latlon(q.get("origin", [""])[0]), _latlon(q.get("destination", [""])[0])
    except Exception:
        return None, None


def data_age_minutes(updated_at: str) -> int | None:
    """Minutes since the payload's updated_at stamp ('DD Mon HH:MM'), or None."""
    from datetime import datetime

    raw = updated_at.split("(")[0].strip()
    for fmt in ("%d %b %Y %H:%M", "%d %b %H:%M"):
        try:
            dt = datetime.strptime(raw, fmt)
            if dt.year == 1900:
                dt = dt.replace(year=datetime.now().year)
            return max(0, int((datetime.now() - dt).total_seconds() // 60))
        except Exception:
            continue
    return None


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    base = Path(__file__).resolve().parent
    local = base / "fonts" / ("Outfit-Bold.ttf" if bold else "Outfit-Regular.ttf")
    for c in [
        str(local),
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]:
        try:
            return ImageFont.truetype(c, size)
        except OSError:
            continue
    return ImageFont.load_default()


def load_payload(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and isinstance(raw.get("merge_variables"), dict):
        return raw["merge_variables"]
    return raw if isinstance(raw, dict) else {}


def load_data_from_db() -> dict[str, Any]:
    """Read the Jen Coming Home plugin webhook payload from the LaraPaper DB."""
    db_paths = [
        "/var/www/html/database/storage/database.sqlite",
        str(Path.home() / "tmp" / "larapaper.sqlite"),
    ]
    for p in db_paths:
        if not Path(p).exists():
            continue
        try:
            db = sqlite3.connect(p)
            row = db.execute(
                "SELECT data_payload FROM plugins WHERE name = ?", (PLUGIN_NAME,)
            ).fetchone()
            db.close()
            if row and row[0]:
                payload = json.loads(row[0])
                return payload.get("merge_variables", payload)
        except Exception as e:  # pragma: no cover - diagnostic only
            print(f"DB load error {p}: {e}")
    return {}


def rounded(draw, box, radius, **kw):
    draw.rounded_rectangle(box, radius=radius, **kw)


def draw_car(draw, x, y, body, accent):
    """A chunky little car centred on (x, y)."""
    rounded(draw, [x - 22, y - 10, x + 22, y + 8], radius=5, fill=body)
    rounded(draw, [x - 13, y - 19, x + 11, y - 7], radius=4, fill=body)
    rounded(draw, [x - 9, y - 16, x - 1, y - 9], radius=2, fill=accent)
    rounded(draw, [x + 1, y - 16, x + 8, y - 9], radius=2, fill=accent)
    draw.ellipse([x - 16, y + 4, x - 6, y + 14], fill=BLACK)
    draw.ellipse([x + 6, y + 4, x + 16, y + 14], fill=BLACK)
    draw.ellipse([x - 14, y + 6, x - 8, y + 12], fill=WHITE)
    draw.ellipse([x + 8, y + 6, x + 14, y + 12], fill=WHITE)


def render(data: dict[str, Any]) -> Image.Image:
    headline = str(data.get("headline", "Heading Home"))
    route_label = str(data.get("route_label", "Direct")).strip()
    commute_state = str(data.get("commute_state", "journey_started"))
    home_prep = str(data.get("home_prep_status", "Not Needed")).strip()
    heading_home = str(data.get("heading_home", "Yes")).lower() == "yes"
    updated_at = str(data.get("updated_at", ""))

    try:
        eta = int(round(float(data.get("eta_minutes", 0))))
    except (ValueError, TypeError):
        eta = 0
    try:
        dist = float(data.get("distance_km", 0))
    except (ValueError, TypeError):
        dist = 0.0

    arrival = (datetime.now() + timedelta(minutes=max(eta, 0))).strftime("%H:%M")
    # Position the car from her REAL GPS (origin) along Work->Home, falling back
    # to the ETA proxy only if the coordinates can't be read.
    cur, home_pt = coords_from_map_url(str(data.get("map_url", "")))
    if cur and home_pt:
        done = _haversine_km(WORK_ANCHOR, cur)
        remaining = _haversine_km(cur, home_pt)
        progress = max(0.04, min(0.96, done / (done + remaining))) if (done + remaining) > 0 else 0.5
    else:
        progress = max(0.06, min(0.94, 1.0 - (eta / 60.0))) if eta > 0 else 0.5
    age_min = data_age_minutes(updated_at)

    img = Image.new("RGB", (WIDTH, HEIGHT), WHITE)
    d = ImageDraw.Draw(img)

    # ---------------- HEADER (blue) ----------------
    HEAD_H = 86
    d.rectangle([0, 0, WIDTH, HEAD_H], fill=BLUE)
    d.text((28, 16), headline.upper(), fill=WHITE, font=font(34, bold=True))
    d.text((28, 56), ("HOMEWARD BOUND" if heading_home else "STANDBY"),
           fill=YELLOW, font=font(16, bold=True))
    pill = [566, 14, 782, 72]
    rounded(d, pill, radius=12, fill=WHITE)
    d.text((582, 22), "ARRIVES HOME", fill=BLACK, font=font(13, bold=True))
    d.text((582, 36), arrival, fill=RED, font=font(34, bold=True))
    d.rectangle([0, HEAD_H, WIDTH, HEAD_H + 6], fill=YELLOW)

    # ---------------- HERO: Work -> Home journey ----------------
    base_y = 250
    x0, x1 = 92, 708
    car_x = int(x0 + (x1 - x0) * progress)

    d.line([(x0, base_y), (car_x, base_y)], fill=GREEN, width=16)
    d.line([(car_x, base_y), (x1, base_y)], fill=BLACK, width=6)

    if commute_state == "via_clean_bean":
        wx = int(x0 + (x1 - x0) * 0.42)
        d.ellipse([wx - 9, base_y - 9, wx + 9, base_y + 9], fill=YELLOW, outline=BLACK, width=2)
        d.text((wx, base_y + 16), "CLEAN BEAN", fill=BLACK, font=font(12, bold=True), anchor="ma")

    d.ellipse([x0 - 18, base_y - 18, x0 + 18, base_y + 18], fill=RED, outline=BLACK, width=2)
    d.rectangle([x0 - 7, base_y - 6, x0 + 7, base_y + 6], fill=WHITE)
    d.text((x0, base_y + 30), "WORK", fill=BLACK, font=font(15, bold=True), anchor="ma")
    d.ellipse([x1 - 20, base_y - 20, x1 + 20, base_y + 20], fill=GREEN, outline=BLACK, width=2)
    d.polygon([(x1 - 9, base_y + 2), (x1, base_y - 9), (x1 + 9, base_y + 2)], fill=WHITE)
    d.rectangle([x1 - 6, base_y + 1, x1 + 6, base_y + 8], fill=WHITE)
    d.text((x1, base_y + 32), "HOME", fill=BLACK, font=font(15, bold=True), anchor="ma")

    bw, bh = 156, 86
    bx = max(x0, min(car_x - bw // 2, x1 - bw))
    by = base_y - 150
    rounded(d, [bx, by, bx + bw, by + bh], radius=14, fill=RED)
    d.polygon([(car_x - 12, by + bh), (car_x + 12, by + bh), (car_x, by + bh + 18)], fill=RED)
    d.text((bx + bw // 2, by + 12), str(eta) if eta > 0 else "?",
           fill=WHITE, font=font(54, bold=True), anchor="ma")
    d.text((bx + bw // 2, by + 64), "MIN AWAY", fill=WHITE, font=font(15, bold=True), anchor="ma")

    draw_car(d, car_x, base_y, BLACK, YELLOW)

    # Route + distance subtitle (no double "via": show the label as given).
    sub = route_label
    if dist > 0:
        sub = f"{sub}   ·   {dist:.1f} km to go" if sub else f"{dist:.1f} km to go"
    if sub:
        d.text((WIDTH // 2, base_y + 58), sub, fill=BLACK, font=font(18, bold=True), anchor="ma")

    # Freshness stamp — makes a stale reading obvious rather than looking live.
    if age_min is not None:
        stamp = f"updated {updated_at}  ·  live" if age_min <= 8 else f"updated {updated_at}  ·  {age_min}m old"
        scol = BLACK if age_min <= 8 else RED
    else:
        stamp, scol = (f"updated {updated_at}" if updated_at else ""), BLACK
    if stamp:
        d.text((WIDTH // 2, base_y + 84), stamp, fill=scol, font=font(13, bold=True), anchor="ma")

    # ---------------- PREP CARD (footer) ----------------
    cy0, cy1 = 360, 462
    m = 26
    prep_l = home_prep.lower()
    if "active" in prep_l:
        bg, fg, big, small = GREEN, BLACK, "HOME PREP RUNNING", "Heating's already on for her."
        dot = GREEN
    elif "not" in prep_l:
        # "Not Needed" — must be checked before the "need" match below, since
        # the substring "need" also appears inside "not needed".
        bg, fg, big, small = WHITE, BLACK, "ALL SET AT HOME", "Nothing to do — sit tight."
        dot = GREEN
    elif "need" in prep_l:
        bg, fg, big, small = YELLOW, BLACK, "PREP THE HOUSE", f"Heating on before she's back — ~{eta} min."
        dot = RED
    else:
        bg, fg, big, small = WHITE, BLACK, "ALL SET AT HOME", "Nothing to do — sit tight."
        dot = GREEN
    rounded(d, [m, cy0, WIDTH - m, cy1], radius=16, fill=bg, outline=BLACK, width=3)
    d.ellipse([WIDTH - m - 64, cy0 + 26, WIDTH - m - 16, cy0 + 74], fill=dot, outline=BLACK, width=2)
    d.text((m + 28, cy0 + 18), big, fill=fg, font=font(30, bold=True))
    d.text((m + 28, cy0 + 58), small, fill=fg, font=font(17, bold=True))

    return img


def remap(img: Image.Image) -> Image.Image:
    pal = Image.new("P", (1, 1))
    flat: list[int] = []
    for rgb in PANEL_PALETTE:
        flat += list(rgb)
    flat += [0, 0, 0] * (256 - len(PANEL_PALETTE))
    pal.putpalette(flat)
    return img.quantize(palette=pal, dither=0)


def main() -> None:
    p = argparse.ArgumentParser(description="Render the Jen Coming Home colour sidecar.")
    p.add_argument("--payload", type=Path, default=None)
    p.add_argument("--output", type=Path, default=OUT_PATH)
    p.add_argument("--source-output", type=Path, default=SOURCE_PATH)
    a = p.parse_args()
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.source_output.parent.mkdir(parents=True, exist_ok=True)
    data = load_payload(a.payload) if a.payload else load_data_from_db()
    src = render(data)
    src.save(a.source_output)
    remap(src).save(a.output, optimize=True)
    print(f"Wrote {a.output}")
    print(f"Source {a.source_output}")


if __name__ == "__main__":
    main()
