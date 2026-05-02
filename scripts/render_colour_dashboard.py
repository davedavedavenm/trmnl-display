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
OUT_PATH = OUT_DIR / "sidecar_colour_dashboard_next.png"
SOURCE_PATH = OUT_DIR / "sidecar_colour_dashboard_source_next.png"
WIDTH = 800
HEIGHT = 480

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
ORANGE = (255, 128, 0)

SOURCE_BG = (250, 248, 239)
SOFT_YELLOW = (255, 245, 180)
SOFT_BLUE = (210, 230, 255)
SOFT_GREEN = (220, 255, 220)
SOFT_ORANGE = (255, 220, 205)
SOFT_GREY = (235, 235, 235)

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
    if isinstance(raw, dict) and isinstance(raw.get("merge_variables"), dict):
        return raw["merge_variables"]
    if isinstance(raw, dict):
        return raw
    return {}


def as_text(value: Any, fallback: str = "--") -> str:
    if value is None:
        return fallback
    if isinstance(value, str):
        stripped = value.strip()
        return stripped if stripped else fallback
    return str(value)


def as_float(value: Any) -> float | None:
    try:
        if value in (None, "", "unknown", "unavailable"):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def as_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "yes", "on", "open", "home", "locked", "running", "playing"}:
            return True
        if lowered in {"false", "no", "off", "closed", "away", "unlocked", "idle", "paused"}:
            return False
    if value is None:
        return None
    return bool(value)


def fit_text(value: Any, max_chars: int, fallback: str = "--") -> str:
    text_value = as_text(value, fallback)
    if len(text_value) <= max_chars:
        return text_value
    return text_value[: max(1, max_chars - 1)].rstrip() + "."


def text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    value: Any,
    size: int,
    fill: tuple[int, int, int] = BLACK,
    bold: bool = False,
    fallback: str = "--",
) -> None:
    draw.text(xy, as_text(value, fallback), font=font(size, bold), fill=fill)


def right_text(
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
    x = box[2] - (bb[2] - bb[0])
    y = box[1]
    draw.text((x, y), text_value, font=f, fill=fill)


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


def card(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], fill: tuple[int, int, int], width: int = 2) -> None:
    draw.rounded_rectangle(box, radius=8, fill=fill, outline=BLACK, width=width)


def icon_home(draw: ImageDraw.ImageDraw, x: int, y: int, fill: tuple[int, int, int] = BLACK) -> None:
    draw.polygon([(x, y + 18), (x + 18, y), (x + 36, y + 18)], fill=fill)
    draw.rectangle((x + 6, y + 18, x + 30, y + 38), fill=fill)
    draw.rectangle((x + 16, y + 25, x + 24, y + 38), fill=WHITE)


def icon_sun_cloud(draw: ImageDraw.ImageDraw, x: int, y: int, condition: str = "") -> None:
    sun_fill = ORANGE if any(token in condition.lower() for token in ("sun", "clear")) else YELLOW
    draw.ellipse((x + 20, y, x + 58, y + 38), fill=sun_fill, outline=BLACK, width=2)
    for dx, dy in [(39, -10), (39, 48), (5, 19), (73, 19), (14, -4), (64, -4)]:
        draw.line((x + 39, y + 19, x + dx, y + dy), fill=BLACK, width=2)
    draw.ellipse((x + 5, y + 28, x + 45, y + 65), fill=WHITE, outline=BLACK, width=2)
    draw.ellipse((x + 35, y + 22, x + 82, y + 66), fill=WHITE, outline=BLACK, width=2)
    draw.rectangle((x + 16, y + 44, x + 76, y + 67), fill=WHITE)
    draw.arc((x + 5, y + 28, x + 45, y + 65), 180, 360, fill=BLACK, width=2)
    draw.arc((x + 35, y + 22, x + 82, y + 66), 180, 360, fill=BLACK, width=2)
    draw.line((x + 15, y + 66, x + 75, y + 66), fill=BLACK, width=2)
    if any(token in condition.lower() for token in ("rain", "drizzle", "shower")):
        for offset in (24, 48, 72):
            draw.line((x + offset, y + 72, x + offset - 5, y + 84), fill=BLUE, width=3)


def icon_bulb(draw: ImageDraw.ImageDraw, x: int, y: int, on: bool | None = True) -> None:
    fill = YELLOW if on else WHITE
    draw.ellipse((x + 8, y, x + 42, y + 34), fill=fill, outline=BLACK, width=2)
    draw.rectangle((x + 18, y + 33, x + 32, y + 47), fill=WHITE, outline=BLACK, width=2)
    draw.line((x + 14, y + 50, x + 36, y + 50), fill=BLACK, width=2)
    if on:
        for x1, y1, x2, y2 in [
            (x + 25, y - 8, x + 25, y - 18),
            (x + 2, y + 14, x - 8, y + 10),
            (x + 48, y + 14, x + 58, y + 10),
        ]:
            draw.line((x1, y1, x2, y2), fill=BLACK, width=2)


def icon_drop(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    draw.ellipse((x + 9, y + 24, x + 39, y + 54), fill=BLUE, outline=BLACK, width=2)
    draw.polygon([(x + 24, y), (x + 9, y + 34), (x + 39, y + 34)], fill=BLUE, outline=BLACK)


def icon_lock(draw: ImageDraw.ImageDraw, x: int, y: int, locked: bool | None = True) -> None:
    if locked:
        draw.arc((x + 8, y, x + 42, y + 36), 180, 360, fill=BLACK, width=5)
    else:
        draw.arc((x + 17, y, x + 51, y + 36), 180, 330, fill=BLACK, width=5)
    draw.rectangle((x + 5, y + 25, x + 45, y + 58), fill=BLACK)
    draw.ellipse((x + 22, y + 36, x + 30, y + 44), fill=WHITE)


def icon_thermo(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    draw.rounded_rectangle((x + 18, y, x + 32, y + 42), radius=7, fill=WHITE, outline=BLACK, width=2)
    draw.ellipse((x + 10, y + 34, x + 40, y + 64), fill=RED, outline=BLACK, width=2)
    draw.rectangle((x + 21, y + 14, x + 29, y + 48), fill=RED)


def icon_blinds(draw: ImageDraw.ImageDraw, x: int, y: int, open_: bool | None = True) -> None:
    if open_:
        centered_text(draw, (x - 2, y + 4, x + 52, y + 54), "|||", 34, bold=True)
    else:
        for row in (8, 20, 32, 44):
            draw.rectangle((x + 2, y + row, x + 50, y + row + 5), fill=WHITE, outline=BLACK)


def icon_washer(draw: ImageDraw.ImageDraw, x: int, y: int, running: bool | None = False) -> None:
    draw.rounded_rectangle((x + 6, y + 4, x + 46, y + 58), radius=4, fill=WHITE, outline=BLACK, width=3)
    if running:
        draw.ellipse((x + 14, y + 24, x + 38, y + 48), fill=SOFT_BLUE, outline=BLACK, width=2)


def icon_music(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    draw.line((x + 32, y + 8, x + 32, y + 48), fill=BLACK, width=4)
    draw.line((x + 32, y + 8, x + 58, y + 2), fill=BLACK, width=4)
    draw.line((x + 58, y + 2, x + 58, y + 42), fill=BLACK, width=4)
    draw.ellipse((x + 10, y + 45, x + 34, y + 66), fill=YELLOW, outline=BLACK, width=2)
    draw.ellipse((x + 38, y + 37, x + 62, y + 58), fill=YELLOW, outline=BLACK, width=2)


def metric(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    title: str,
    value: str,
    detail: str,
    fill: tuple[int, int, int],
    icon_fn: Callable[[ImageDraw.ImageDraw, int, int], None],
) -> None:
    card(draw, box, fill=fill)
    icon_fn(draw, box[0] + 14, box[1] + 18)
    text(draw, (box[0] + 90, box[1] + 16), fit_text(title, 10), 15, bold=True)
    text(draw, (box[0] + 90, box[1] + 43), fit_text(value, 9), 27, bold=True)
    text(draw, (box[0] + 90, box[1] + 78), fit_text(detail, 18, ""), 13, fallback="")


def control(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    title: str,
    value: str,
    fill: tuple[int, int, int],
    icon_fn: Callable[[ImageDraw.ImageDraw, int, int], None],
) -> None:
    card(draw, box, fill=fill)
    centered_text(draw, (box[0], box[1] + 8, box[2], box[1] + 32), fit_text(title, 10), 15, bold=True)
    icon_fn(draw, (box[0] + box[2]) // 2 - 26, box[1] + 40)
    centered_text(draw, (box[0], box[3] - 30, box[2], box[3] - 8), fit_text(value, 10), 15)


def first_dict(items: Any, index: int = 0) -> dict[str, Any]:
    if isinstance(items, list) and len(items) > index and isinstance(items[index], dict):
        return items[index]
    return {}


def active_sonos(sonos: Any) -> dict[str, Any]:
    if not isinstance(sonos, list):
        return {}
    for state in ("playing", "paused"):
        for item in sonos:
            if isinstance(item, dict) and item.get("state") == state:
                return item
    return first_dict(sonos)


def render_dashboard(data: dict[str, Any]) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT), SOURCE_BG)
    draw = ImageDraw.Draw(img)

    weather = data.get("weather") if isinstance(data.get("weather"), dict) else {}
    home = data.get("home") if isinstance(data.get("home"), dict) else {}
    people = data.get("people") if isinstance(data.get("people"), list) else []
    sonos = data.get("sonos") if isinstance(data.get("sonos"), list) else []
    lights = data.get("lights") if isinstance(data.get("lights"), list) else []
    energy = data.get("energy") if isinstance(data.get("energy"), dict) else {}
    labels = data.get("labels") if isinstance(data.get("labels"), dict) else {}
    nav_labels = data.get("nav") if isinstance(data.get("nav"), list) else []

    updated_at = as_text(data.get("updated_at"), datetime.now().strftime("%d %b %H:%M"))
    updated_time = updated_at[-5:] if len(updated_at) >= 5 else updated_at
    title = fit_text(data.get("dashboard_title"), 24, "Home Assistant")
    instance_label = fit_text(data.get("instance_label"), 18, "Home")
    door_label = fit_text(labels.get("door"), 10, "Front door")
    washer_label = fit_text(labels.get("washer"), 10, "Washer")
    blind_label = fit_text(labels.get("blinds"), 10, "Blinds")
    thermostat_label = fit_text(labels.get("thermostat"), 10, "Climate")
    thermostat_detail = fit_text(labels.get("thermostat_detail"), 16, "Indoor")
    door_detail = fit_text(labels.get("door_detail"), 18, "Security")
    washer_detail = fit_text(labels.get("washer_detail"), 12, "Utility")
    blind_detail = fit_text(labels.get("blinds_detail"), 12, "Position")
    sonos_label = fit_text(labels.get("sonos"), 10, "Sonos")
    people_label = fit_text(labels.get("people"), 12, "People")
    media_label = fit_text(labels.get("media"), 12, "Media")
    energy_label = fit_text(labels.get("energy") or energy.get("label"), 12, "Energy")

    temp = as_float(weather.get("temperature"))
    humidity = as_float(weather.get("humidity"))
    condition = as_text(weather.get("condition"), "")
    condition_label = fit_text(weather.get("condition_label") or condition.replace("-", " ").title(), 18, "Weather")
    thermostat = as_float(home.get("thermostat_temp"))
    locked = as_bool(home.get("door_locked"))
    washer_running = as_bool(home.get("washer_running"))
    blind_pos = as_float(home.get("blind_position"))
    blinds_open = as_bool(home.get("blinds_open"))
    if blinds_open is None and blind_pos is not None:
        blinds_open = blind_pos > 0

    draw.rectangle((0, 0, WIDTH, 54), fill=WHITE)
    icon_home(draw, 24, 10)
    text(draw, (74, 16), title, 24, bold=True)
    right_text(draw, (604, 6, 778, 46), updated_time, 40, bold=True)
    right_text(draw, (604, 40, 778, 54), fit_text(updated_at, 18), 13)
    draw.line((22, 56, 778, 56), fill=BLACK, width=2)

    metric(
        draw,
        (24, 76, 212, 174),
        "Weather",
        f"{temp:.1f}" if temp is not None else "--",
        condition_label,
        SOFT_YELLOW,
        lambda d, x, y: icon_sun_cloud(d, x, y, condition),
    )
    metric(
        draw,
        (226, 76, 384, 174),
        "Humidity",
        f"{humidity:.0f}%" if humidity is not None else "--%",
        instance_label,
        SOFT_BLUE,
        icon_drop,
    )
    metric(
        draw,
        (398, 76, 556, 174),
        thermostat_label,
        f"{thermostat:.1f} C" if thermostat is not None else "-- C",
        thermostat_detail,
        SOFT_ORANGE,
        icon_thermo,
    )
    metric(
        draw,
        (570, 76, 776, 174),
        door_label,
        "Locked" if locked else "Open" if locked is False else "--",
        "Secure" if locked else door_detail if locked is False else "Unavailable",
        SOFT_GREEN if locked else SOFT_ORANGE,
        lambda d, x, y: icon_lock(d, x, y, locked),
    )

    light_cards = []
    for i in range(3):
        light = first_dict(lights, i)
        on = as_bool(light.get("on", light.get("state")))
        label = light.get("label") or light.get("name") or ["Living", "Bedroom", "Kitchen"][i]
        light_cards.append((fit_text(label, 10), "On" if on else "Off", SOFT_YELLOW if on else SOFT_GREY, on))

    controls = [
        ((24, 192, 144, 306), light_cards[0][0], light_cards[0][1], light_cards[0][2], lambda d, x, y: icon_bulb(d, x, y + 4, light_cards[0][3])),
        ((158, 192, 278, 306), light_cards[1][0], light_cards[1][1], light_cards[1][2], lambda d, x, y: icon_bulb(d, x, y + 4, light_cards[1][3])),
        ((292, 192, 412, 306), light_cards[2][0], light_cards[2][1], light_cards[2][2], lambda d, x, y: icon_bulb(d, x, y + 4, light_cards[2][3])),
        ((426, 192, 546, 306), blind_label, "Open" if blinds_open else "Closed" if blinds_open is False else "--", SOFT_GREEN if blinds_open else SOFT_GREY, lambda d, x, y: icon_blinds(d, x, y, blinds_open)),
        ((560, 192, 680, 306), washer_label, "Running" if washer_running else "Idle" if washer_running is False else "--", SOFT_BLUE if washer_running else SOFT_GREY, lambda d, x, y: icon_washer(d, x, y, washer_running)),
        ((694, 192, 776, 306), sonos_label, as_text(active_sonos(sonos).get("state"), "Idle").title(), SOFT_ORANGE, icon_music),
    ]
    for args in controls:
        control(draw, *args)

    card(draw, (24, 328, 244, 424), SOFT_GREEN)
    text(draw, (44, 344), people_label, 18, bold=True)
    person_1 = first_dict(people, 0)
    person_2 = first_dict(people, 1)
    text(draw, (44, 374), f"{fit_text(person_1.get('name'), 10, 'Person')}: {as_text(person_1.get('state'), 'unknown').title()}", 22, bold=True)
    text(draw, (44, 400), f"{fit_text(person_2.get('name'), 10, 'Person')}: {as_text(person_2.get('state'), 'unknown').title()}", 18)

    card(draw, (264, 328, 536, 424), SOFT_BLUE)
    media = active_sonos(sonos)
    media_room = fit_text(media.get("room"), 18, "No active room")
    media_title = fit_text(media.get("title") or media.get("artist") or "No active playback", 24)
    media_state = as_text(media.get("state"), "Idle").title()
    text(draw, (284, 344), media_label, 18, bold=True)
    text(draw, (284, 374), media_room, 22, bold=True)
    text(draw, (284, 400), fit_text(f"{media_state} - {media_title}", 28), 17)

    card(draw, (556, 328, 776, 424), SOFT_YELLOW)
    text(draw, (576, 344), energy_label, 18, bold=True)
    energy_value = as_text(energy.get("value"), "")
    bars = energy.get("bars") if isinstance(energy.get("bars"), list) else []
    numeric_bars = [as_float(v) for v in bars]
    numeric_bars = [v for v in numeric_bars if v is not None]
    if energy_value:
        if numeric_bars:
            max_bar = max(numeric_bars) or 1
            for i, value in enumerate(numeric_bars[:6]):
                x = 590 + i * 26
                h = int(74 * value / max_bar)
                draw.rectangle((x, 408 - h, x + 16, 408), fill=BLUE, outline=BLACK)
        text(draw, (682, 374), fit_text(energy_value, 9), 22, bold=True)
    else:
        text(draw, (576, 374), "No sensor", 24, bold=True)
        text(draw, (578, 402), "Configure entity", 13)

    draw.rectangle((0, 442, WIDTH, 480), fill=(120, 168, 150))
    labels_for_nav = [as_text(v) for v in nav_labels[:6]] or ["Home", "Rooms", "Lights", "Climate", "Security", "More"]
    while len(labels_for_nav) < 6:
        labels_for_nav.append("")
    for i, label in enumerate(labels_for_nav[:6]):
        x = 54 + i * 126
        fill = WHITE
        centered_text(draw, (x - 44, 448, x + 44, 474), label, 15, fill=fill, bold=True)

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
    return render_dashboard(load_payload(payload_path))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render the HA dashboard plugin payload to a seven-colour indexed PNG.")
    parser.add_argument("--payload", type=Path, default=DEFAULT_PAYLOAD, help="TRMNL merge_variables payload or unwrapped merge variables object.")
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
