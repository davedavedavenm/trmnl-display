#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_DIR = ROOT / "plugins" / "trmnl-ha-dashboard"
DEFAULT_PAYLOAD = PLUGIN_DIR / "payload.example.json"
OUT_DIR = Path(__file__).resolve().parent / "tmp"
OUT_PATH = OUT_DIR / "sidecar_colour_dashboard.png"
SOURCE_PATH = OUT_DIR / "sidecar_colour_dashboard_source.png"
WIDTH = 800
HEIGHT = 480


BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
ORANGE = (255, 128, 0)

PANEL_PALETTE = [BLACK, WHITE, RED, YELLOW, BLUE, GREEN, ORANGE]


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            pass
    return ImageFont.load_default()


def load_payload(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    if "merge_variables" in raw and isinstance(raw["merge_variables"], dict):
        return raw["merge_variables"]
    return raw


def as_text(value: Any, fallback: str = "--") -> str:
    if value is None:
        return fallback
    if isinstance(value, str):
        value = value.strip()
        return value if value else fallback
    return str(value)


def as_float(value: Any) -> float | None:
    try:
        if value in (None, "", "unavailable", "unknown"):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def as_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "yes", "on", "open", "home", "locked"}:
            return True
        if lowered in {"false", "no", "off", "closed", "away", "unlocked"}:
            return False
    if value is None:
        return None
    return bool(value)


def fit_text(value: Any, max_chars: int, fallback: str = "--") -> str:
    text_value = as_text(value, fallback)
    if len(text_value) <= max_chars:
        return text_value
    return text_value[: max(1, max_chars - 1)].rstrip() + "."


def draw_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    value: Any,
    size: int,
    fill: tuple[int, int, int] = BLACK,
    bold: bool = False,
    fallback: str = "--",
) -> None:
    draw.text(xy, as_text(value, fallback), font=font(size, bold), fill=fill)


def centered_text(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    value: Any,
    size: int,
    fill: tuple[int, int, int] = BLACK,
    bold: bool = False,
    fallback: str = "--",
) -> None:
    f = font(size, bold)
    text_value = as_text(value, fallback)
    bb = draw.textbbox((0, 0), text_value, font=f)
    x = box[0] + (box[2] - box[0] - (bb[2] - bb[0])) // 2
    y = box[1] + (box[3] - box[1] - (bb[3] - bb[1])) // 2
    draw.text((x, y), text_value, font=f, fill=fill)


def card(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], fill: tuple[int, int, int] = WHITE, outline: tuple[int, int, int] = BLACK, width: int = 2) -> None:
    draw.rounded_rectangle(box, radius=7, fill=fill, outline=outline, width=width)


def icon_home(draw: ImageDraw.ImageDraw, x: int, y: int, fill: tuple[int, int, int] = BLACK) -> None:
    draw.polygon([(x, y + 16), (x + 18, y), (x + 36, y + 16)], fill=fill)
    draw.rectangle((x + 6, y + 16, x + 30, y + 38), fill=fill)
    draw.rectangle((x + 16, y + 26, x + 24, y + 38), fill=WHITE)


def icon_person(draw: ImageDraw.ImageDraw, x: int, y: int, fill: tuple[int, int, int] = BLACK) -> None:
    draw.ellipse((x + 12, y, x + 38, y + 26), fill=WHITE, outline=fill, width=3)
    draw.arc((x + 4, y + 28, x + 46, y + 72), 200, 340, fill=fill, width=4)


def icon_weather(draw: ImageDraw.ImageDraw, x: int, y: int, condition: str) -> None:
    c = condition.lower()
    sun_fill = ORANGE if "sun" in c or "clear" in c else YELLOW
    draw.ellipse((x + 26, y + 2, x + 66, y + 42), fill=sun_fill, outline=BLACK, width=2)
    for dx, dy in [(46, -8), (46, 54), (10, 22), (82, 22), (19, 0), (73, 0)]:
        draw.line((x + 46, y + 22, x + dx, y + dy), fill=BLACK, width=2)
    if any(token in c for token in ("rain", "drizzle", "shower", "cloud", "partly")):
        draw.ellipse((x + 6, y + 30, x + 48, y + 66), fill=WHITE, outline=BLACK, width=2)
        draw.ellipse((x + 38, y + 24, x + 86, y + 68), fill=WHITE, outline=BLACK, width=2)
        draw.rectangle((x + 18, y + 46, x + 80, y + 69), fill=WHITE)
        draw.arc((x + 6, y + 30, x + 48, y + 66), 180, 360, fill=BLACK, width=2)
        draw.arc((x + 38, y + 24, x + 86, y + 68), 180, 360, fill=BLACK, width=2)
        draw.line((x + 16, y + 68, x + 80, y + 68), fill=BLACK, width=2)
    if "rain" in c or "drizzle" in c or "shower" in c:
        for offset in (24, 48, 72):
            draw.line((x + offset, y + 74, x + offset - 5, y + 86), fill=BLUE, width=3)


def icon_drop(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    draw.ellipse((x + 10, y + 28, x + 42, y + 60), fill=BLUE, outline=BLACK, width=2)
    draw.polygon([(x + 26, y + 2), (x + 10, y + 40), (x + 42, y + 40)], fill=BLUE, outline=BLACK)


def icon_lock(draw: ImageDraw.ImageDraw, x: int, y: int, locked: bool | None) -> None:
    fill = BLUE if locked else RED
    if locked:
        draw.arc((x + 9, y + 2, x + 47, y + 42), 180, 360, fill=BLACK, width=5)
    else:
        draw.arc((x + 18, y + 2, x + 56, y + 42), 180, 330, fill=BLACK, width=5)
    draw.rounded_rectangle((x + 6, y + 30, x + 50, y + 66), radius=4, fill=fill, outline=BLACK, width=2)
    draw.ellipse((x + 25, y + 43, x + 33, y + 51), fill=WHITE)


def icon_thermo(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    draw.rounded_rectangle((x + 18, y + 4, x + 34, y + 48), radius=8, fill=WHITE, outline=BLACK, width=2)
    draw.ellipse((x + 10, y + 40, x + 42, y + 72), fill=RED, outline=BLACK, width=2)
    draw.rectangle((x + 22, y + 18, x + 30, y + 54), fill=RED)


def icon_washer(draw: ImageDraw.ImageDraw, x: int, y: int, running: bool | None) -> None:
    fill = ORANGE if running else WHITE
    draw.rounded_rectangle((x + 8, y + 2, x + 54, y + 68), radius=5, fill=fill, outline=BLACK, width=3)
    draw.ellipse((x + 17, y + 27, x + 45, y + 55), fill=WHITE, outline=BLACK, width=3)
    draw.arc((x + 22, y + 33, x + 42, y + 49), 20, 210, fill=BLUE, width=2)
    draw.ellipse((x + 16, y + 10, x + 22, y + 16), fill=BLACK)
    draw.line((x + 29, y + 13, x + 46, y + 13), fill=BLACK, width=2)


def icon_blinds(draw: ImageDraw.ImageDraw, x: int, y: int, open_: bool | None) -> None:
    draw.line((x + 4, y + 8, x + 58, y + 8), fill=BLACK, width=4)
    for row in (20, 32, 44):
        draw.rectangle((x + 10, y + row, x + 52, y + row + 5), fill=GREEN if open_ else WHITE, outline=BLACK)
    draw.line((x + 32, y + 8, x + 32, y + 64), fill=BLACK, width=2)
    if open_:
        draw.polygon([(x + 22, y + 58), (x + 32, y + 68), (x + 42, y + 58)], fill=GREEN, outline=BLACK)
    else:
        draw.polygon([(x + 22, y + 64), (x + 32, y + 54), (x + 42, y + 64)], fill=WHITE, outline=BLACK)


def icon_music(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    draw.line((x + 32, y + 8, x + 32, y + 52), fill=BLACK, width=4)
    draw.line((x + 32, y + 8, x + 58, y + 2), fill=BLACK, width=4)
    draw.line((x + 58, y + 2, x + 58, y + 44), fill=BLACK, width=4)
    draw.ellipse((x + 10, y + 48, x + 34, y + 70), fill=YELLOW, outline=BLACK, width=2)
    draw.ellipse((x + 38, y + 40, x + 62, y + 62), fill=YELLOW, outline=BLACK, width=2)


def status_card(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    title: str,
    value: str,
    detail: str,
    fill: tuple[int, int, int],
    icon_fn: Callable[[ImageDraw.ImageDraw, int, int], None],
    dark: bool = False,
) -> None:
    card(draw, box, fill=fill)
    fg = WHITE if dark else BLACK
    icon_fn(draw, box[0] + 14, box[1] + 18)
    draw_text(draw, (box[0] + 86, box[1] + 14), title.upper(), 12, fill=fg, bold=True)
    draw_text(draw, (box[0] + 86, box[1] + 38), fit_text(value, 13), 25, fill=fg, bold=True)
    draw_text(draw, (box[0] + 86, box[1] + 70), fit_text(detail, 20, ""), 13, fill=fg, bold=False, fallback="")


def small_card(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    title: str,
    value: str,
    detail: str,
    fill: tuple[int, int, int],
    icon_fn: Callable[[ImageDraw.ImageDraw, int, int], None],
) -> None:
    card(draw, box, fill=fill)
    draw.rectangle((box[0] + 1, box[1] + 1, box[2] - 1, box[1] + 10), fill=fill)
    draw_text(draw, (box[0] + 12, box[1] + 18), title.upper(), 11, bold=True)
    icon_fn(draw, box[2] - 66, box[1] + 22)
    draw_text(draw, (box[0] + 12, box[1] + 48), fit_text(value, 10), 23, bold=True)
    draw_text(draw, (box[0] + 12, box[1] + 78), fit_text(detail, 16, ""), 12, fallback="")


def render_dashboard(data: dict[str, Any]) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT), WHITE)
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, WIDTH, HEIGHT), fill=WHITE)

    title = fit_text(data.get("dashboard_title"), 22, "Home Assistant")
    instance = fit_text(data.get("instance_label"), 18, "Home")
    updated_at = as_text(data.get("updated_at"), datetime.now().strftime("%d %b %H:%M"))
    weather = data.get("weather") if isinstance(data.get("weather"), dict) else {}
    home = data.get("home") if isinstance(data.get("home"), dict) else {}
    people = data.get("people") if isinstance(data.get("people"), list) else []
    sonos = data.get("sonos") if isinstance(data.get("sonos"), list) else []

    draw.rectangle((0, 0, WIDTH, 56), fill=BLACK)
    icon_home(draw, 24, 10, WHITE)
    draw_text(draw, (74, 11), title, 24, fill=WHITE, bold=True)
    draw_text(draw, (76, 38), instance, 12, fill=YELLOW, bold=True)
    draw_text(draw, (626, 5), updated_at[-5:], 37, fill=WHITE, bold=True)
    draw_text(draw, (616, 40), fit_text(updated_at, 20), 12, fill=YELLOW, bold=True)

    temp = as_float(weather.get("temperature"))
    humidity = as_float(weather.get("humidity"))
    wind = as_float(weather.get("wind_speed"))
    condition = as_text(weather.get("condition"), "")
    condition_label = fit_text(weather.get("condition_label") or condition.replace("-", " ").title(), 20, "Weather")

    card(draw, (22, 74, 330, 184), fill=YELLOW)
    icon_weather(draw, 42, 91, condition)
    temp_text = f"{temp:.1f} C" if temp is not None else "-- C"
    draw_text(draw, (146, 91), "WEATHER", 13, bold=True)
    draw_text(draw, (146, 116), temp_text, 36, bold=True)
    draw_text(draw, (148, 158), condition_label, 14, bold=True)

    status_card(
        draw,
        (344, 74, 558, 184),
        "Humidity",
        f"{humidity:.0f}%" if humidity is not None else "--%",
        f"Wind {wind:.0f} km/h" if wind is not None else "Wind unavailable",
        BLUE,
        icon_drop,
        dark=True,
    )

    thermostat = as_float(home.get("thermostat_temp"))
    status_card(
        draw,
        (572, 74, 778, 184),
        "Climate",
        f"{thermostat:.1f} C" if thermostat is not None else "-- C",
        "Indoor temperature",
        ORANGE,
        icon_thermo,
    )

    locked = as_bool(home.get("door_locked"))
    washer_running = as_bool(home.get("washer_running"))
    blinds_open = as_bool(home.get("blinds_open"))
    blind_pos = as_float(home.get("blind_position"))
    if blinds_open is None and blind_pos is not None:
        blinds_open = blind_pos == 0

    small_card(
        draw,
        (22, 202, 174, 322),
        "Door",
        "Locked" if locked else "Check",
        "Secure" if locked else "Unlocked/open",
        BLUE if locked else RED,
        lambda d, x, y: icon_lock(d, x, y, locked),
    )
    small_card(
        draw,
        (190, 202, 342, 322),
        "Washer",
        "Running" if washer_running else "Idle",
        "Laundry",
        ORANGE if washer_running else WHITE,
        lambda d, x, y: icon_washer(d, x, y, washer_running),
    )
    small_card(
        draw,
        (358, 202, 510, 322),
        "Blinds",
        "Open" if blinds_open else "Closed",
        f"{blind_pos:.0f}%" if blind_pos is not None else "Position",
        GREEN if blinds_open else WHITE,
        lambda d, x, y: icon_blinds(d, x, y, blinds_open),
    )

    card(draw, (526, 202, 778, 322), fill=WHITE)
    draw_text(draw, (542, 218), "PRESENCE", 12, bold=True)
    for i in range(3):
        person = people[i] if i < len(people) and isinstance(people[i], dict) else None
        y = 244 + i * 24
        if person:
            state = as_text(person.get("state"), "unknown").lower()
            fill = GREEN if state == "home" else RED if state in {"away", "not_home"} else ORANGE
            draw.ellipse((544, y + 4, 556, y + 16), fill=fill, outline=BLACK)
            draw_text(draw, (566, y), fit_text(person.get("name"), 12, "Person"), 17, bold=True)
            label = "Home" if state == "home" else "Away" if state in {"away", "not_home"} else fit_text(state.title(), 8)
            draw_text(draw, (702, y + 2), label, 14, bold=True)
        else:
            draw.ellipse((544, y + 4, 556, y + 16), fill=WHITE, outline=BLACK)
            draw_text(draw, (566, y), "Unassigned", 15)

    active_sonos = next((s for s in sonos if isinstance(s, dict) and s.get("state") == "playing"), None)
    if active_sonos is None:
        active_sonos = next((s for s in sonos if isinstance(s, dict) and s.get("state") == "paused"), None)
    idle_count = sum(1 for s in sonos if isinstance(s, dict) and s.get("state") == "idle")

    card(draw, (22, 340, 500, 432), fill=YELLOW)
    icon_music(draw, 42, 352)
    draw_text(draw, (122, 356), "SONOS", 12, bold=True)
    if active_sonos:
        state = as_text(active_sonos.get("state"), "idle").title()
        title_text = fit_text(active_sonos.get("title"), 26, "No title")
        room = fit_text(active_sonos.get("room"), 14, "Room")
        artist = fit_text(active_sonos.get("artist"), 18, "")
        draw_text(draw, (122, 379), title_text, 25, bold=True)
        draw_text(draw, (124, 410), f"{state} - {room}" if artist == "" else f"{artist} - {room}", 13, bold=True)
    else:
        draw_text(draw, (122, 381), "No active music", 26, bold=True)
        draw_text(draw, (124, 411), f"{idle_count} rooms idle" if idle_count else "No rooms reporting", 13, bold=True)

    card(draw, (516, 340, 778, 432), fill=BLACK)
    draw_text(draw, (538, 356), "HOME SUMMARY", 12, fill=YELLOW, bold=True)
    home_people = sum(1 for p in people if isinstance(p, dict) and as_text(p.get("state"), "").lower() == "home")
    draw_text(draw, (538, 378), f"{home_people}/{len(people)} home" if people else "Presence unknown", 24, fill=WHITE, bold=True)
    summary = [
        ("Door", "OK" if locked else "Check", BLUE if locked else RED),
        ("Wash", "On" if washer_running else "Idle", ORANGE if washer_running else WHITE),
        ("Blinds", "Open" if blinds_open else "Closed", GREEN if blinds_open else WHITE),
    ]
    for i, (label, value, fill) in enumerate(summary):
        x0 = 538 + i * 76
        draw.rounded_rectangle((x0, 411, x0 + 66, 429), radius=4, fill=fill, outline=WHITE, width=1)
        draw_text(draw, (x0 + 5, 414), f"{label} {value}", 9, fill=BLACK if fill != BLACK else WHITE, bold=True)

    draw.rectangle((0, 448, WIDTH, 480), fill=GREEN)
    nav = [("Home", BLACK), ("Climate", ORANGE), ("Security", BLUE), ("Media", YELLOW), ("People", WHITE)]
    for i, (label, fill) in enumerate(nav):
        x0 = i * 160
        if i == 0:
            draw.rectangle((x0, 448, x0 + 160, 480), fill=BLACK)
            fill = WHITE
        centered_text(draw, (x0, 451, x0 + 160, 477), label, 15, fill=fill, bold=True)

    return img


def remap_to_panel_palette(img: Image.Image) -> Image.Image:
    palette = Image.new("P", (1, 1))
    flat: list[int] = []
    for rgb in PANEL_PALETTE:
        flat.extend(rgb)
    flat.extend([0, 0, 0] * (256 - len(PANEL_PALETTE)))
    palette.putpalette(flat)
    return img.quantize(palette=palette, dither=Image.Dither.NONE)


def build(payload_path: Path = DEFAULT_PAYLOAD) -> Image.Image:
    return render_dashboard(load_payload(payload_path))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render the HA dashboard plugin payload to an indexed seven-colour PNG.")
    parser.add_argument("--payload", type=Path, default=DEFAULT_PAYLOAD, help="JSON payload using TRMNL merge_variables, or the unwrapped merge variables object.")
    parser.add_argument("--output", type=Path, default=OUT_PATH, help="Panel-ready indexed PNG output path.")
    parser.add_argument("--source-output", type=Path, default=SOURCE_PATH, help="RGB source PNG output path for visual debugging.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.source_output.parent.mkdir(parents=True, exist_ok=True)

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
