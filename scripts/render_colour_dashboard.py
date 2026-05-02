#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
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


def format_temp(value: float | None, with_unit: bool = False) -> str:
    if value is None:
        return "--C" if with_unit else "--"
    rendered = f"{value:.0f}" if abs(value - round(value)) < 0.05 else f"{value:.1f}"
    return f"{rendered}C" if with_unit else rendered


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


def icon_sun_cloud_compact(draw: ImageDraw.ImageDraw, x: int, y: int, condition: str = "") -> None:
    sun_fill = ORANGE if any(token in condition.lower() for token in ("sun", "clear")) else YELLOW
    draw.ellipse((x + 16, y + 1, x + 48, y + 33), fill=sun_fill, outline=BLACK, width=2)
    for dx, dy in [(32, -6), (32, 40), (5, 18), (58, 18), (12, 0), (52, 0)]:
        draw.line((x + 32, y + 17, x + dx, y + dy), fill=BLACK, width=2)
    draw.ellipse((x + 4, y + 26, x + 38, y + 56), fill=WHITE, outline=BLACK, width=2)
    draw.ellipse((x + 29, y + 21, x + 68, y + 57), fill=WHITE, outline=BLACK, width=2)
    draw.rectangle((x + 13, y + 39, x + 63, y + 58), fill=WHITE)
    draw.arc((x + 4, y + 26, x + 38, y + 56), 180, 360, fill=BLACK, width=2)
    draw.arc((x + 29, y + 21, x + 68, y + 57), 180, 360, fill=BLACK, width=2)
    draw.line((x + 13, y + 57, x + 63, y + 57), fill=BLACK, width=2)
    if any(token in condition.lower() for token in ("rain", "drizzle", "shower")):
        for offset in (20, 40, 60):
            draw.line((x + offset, y + 63, x + offset - 4, y + 73), fill=BLUE, width=3)


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
    draw.rounded_rectangle((x + 9, y + 2, x + 43, y + 46), radius=4, fill=WHITE, outline=BLACK, width=3)
    if running:
        draw.ellipse((x + 15, y + 20, x + 37, y + 42), fill=SOFT_BLUE, outline=BLACK, width=2)


def icon_music(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    draw.line((x + 32, y + 8, x + 32, y + 48), fill=BLACK, width=4)
    draw.line((x + 32, y + 8, x + 58, y + 2), fill=BLACK, width=4)
    draw.line((x + 58, y + 2, x + 58, y + 42), fill=BLACK, width=4)
    draw.ellipse((x + 10, y + 45, x + 34, y + 66), fill=YELLOW, outline=BLACK, width=2)
    draw.ellipse((x + 38, y + 37, x + 62, y + 58), fill=YELLOW, outline=BLACK, width=2)


def icon_music_compact(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    draw.line((x + 26, y + 4, x + 26, y + 34), fill=BLACK, width=3)
    draw.line((x + 26, y + 4, x + 48, y), fill=BLACK, width=3)
    draw.line((x + 48, y, x + 48, y + 28), fill=BLACK, width=3)
    draw.ellipse((x + 8, y + 30, x + 28, y + 46), fill=YELLOW, outline=BLACK, width=2)
    draw.ellipse((x + 34, y + 24, x + 54, y + 40), fill=YELLOW, outline=BLACK, width=2)


def icon_person(draw: ImageDraw.ImageDraw, x: int, y: int, home: bool | None = None) -> None:
    badge = GREEN if home else ORANGE if home is False else WHITE
    draw.ellipse((x + 12, y + 4, x + 38, y + 30), fill=WHITE, outline=BLACK, width=2)
    draw.rounded_rectangle((x + 4, y + 32, x + 46, y + 62), radius=10, fill=WHITE, outline=BLACK, width=2)
    draw.ellipse((x + 33, y + 42, x + 49, y + 58), fill=badge, outline=BLACK, width=2)


def status_band(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], label: str, fill: tuple[int, int, int]) -> None:
    draw.rounded_rectangle(box, radius=5, fill=fill, outline=BLACK, width=2)
    centered_text(draw, (box[0] + 6, box[1] + 2, box[2] - 6, box[3] - 2), fit_text(label, 12), 15, bold=True)


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
    icon_fn(draw, box[0] + 14, box[1] + 17)
    text_x = box[0] + (98 if (box[2] - box[0]) >= 180 else 88)
    title_chars = 10 if (box[2] - box[0]) >= 180 else 8
    detail_chars = 15 if (box[2] - box[0]) >= 180 else 12
    text(draw, (text_x, box[1] + 15), fit_text(title, title_chars), 15, bold=True)
    text(draw, (text_x, box[1] + 42), fit_text(value, 8), 27, bold=True)
    text(draw, (text_x, box[1] + 77), fit_text(detail, detail_chars, ""), 13, fallback="")


def control(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    title: str,
    value: str,
    fill: tuple[int, int, int],
    icon_fn: Callable[[ImageDraw.ImageDraw, int, int], None],
) -> None:
    card(draw, box, fill=fill)
    centered_text(draw, (box[0] + 4, box[1] + 8, box[2] - 4, box[1] + 30), fit_text(title, 10), 15, bold=True)
    icon_fn(draw, (box[0] + box[2]) // 2 - 26, box[1] + 36)
    centered_text(draw, (box[0] + 4, box[3] - 28, box[2] - 4, box[3] - 8), fit_text(value, 10), 15)


def person_row(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], person: dict[str, Any]) -> None:
    name = fit_text(person.get("name"), 14, "Person")
    state = as_text(person.get("state"), "unknown").strip().lower()
    at_home = True if state == "home" else False if state not in {"unknown", "unavailable", "--"} else None
    state_label = "Home" if at_home else "Away" if at_home is False else "Unknown"
    accent = GREEN if at_home else ORANGE if at_home is False else WHITE
    draw.rounded_rectangle(box, radius=7, fill=WHITE, outline=BLACK, width=2)
    icon_x = box[0] + 12
    icon_y = box[1] + 8
    draw.ellipse((icon_x + 8, icon_y, icon_x + 32, icon_y + 24), fill=WHITE, outline=BLACK, width=2)
    draw.arc((icon_x, icon_y + 24, icon_x + 40, icon_y + 58), 200, 340, fill=BLACK, width=2)
    draw.ellipse((icon_x + 30, icon_y + 26, icon_x + 44, icon_y + 40), fill=accent, outline=BLACK, width=2)
    text(draw, (box[0] + 74, box[1] + 13), name, 24, bold=True)
    status_band(draw, (box[2] - 92, box[1] + 12, box[2] - 14, box[1] + 40), state_label, accent)


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
    labels = data.get("labels") if isinstance(data.get("labels"), dict) else {}

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

    metric(
        draw,
        (22, 18, 212, 124),
        "Weather",
        format_temp(temp),
        condition_label,
        SOFT_YELLOW,
        lambda d, x, y: icon_sun_cloud_compact(d, x, y, condition),
    )
    metric(
        draw,
        (226, 18, 386, 124),
        "Humidity",
        f"{humidity:.0f}%" if humidity is not None else "--%",
        instance_label,
        SOFT_BLUE,
        icon_drop,
    )
    metric(
        draw,
        (400, 18, 558, 124),
        thermostat_label,
        format_temp(thermostat, with_unit=True),
        thermostat_detail,
        SOFT_ORANGE,
        icon_thermo,
    )
    metric(
        draw,
        (572, 18, 778, 124),
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
        ((22, 144, 166, 262), light_cards[0][0], light_cards[0][1], light_cards[0][2], lambda d, x, y: icon_bulb(d, x, y + 4, light_cards[0][3])),
        ((180, 144, 324, 262), light_cards[1][0], light_cards[1][1], light_cards[1][2], lambda d, x, y: icon_bulb(d, x, y + 4, light_cards[1][3])),
        ((338, 144, 482, 262), light_cards[2][0], light_cards[2][1], light_cards[2][2], lambda d, x, y: icon_bulb(d, x, y + 4, light_cards[2][3])),
        ((496, 144, 640, 262), blind_label, "Open" if blinds_open else "Closed" if blinds_open is False else "--", SOFT_GREEN if blinds_open else SOFT_GREY, lambda d, x, y: icon_blinds(d, x, y, blinds_open)),
        ((654, 144, 778, 262), washer_label, "Running" if washer_running else "Idle" if washer_running is False else "--", SOFT_BLUE if washer_running else SOFT_GREY, lambda d, x, y: icon_washer(d, x, y, washer_running)),
    ]
    for args in controls:
        control(draw, *args)

    card(draw, (22, 284, 332, 462), SOFT_GREEN)
    text(draw, (44, 306), people_label, 24, bold=True)
    visible_people = [p for p in people[:2] if isinstance(p, dict)]
    if visible_people:
        for index, person in enumerate(visible_people):
            person_row(draw, (44, 346 + index * 52, 286, 391 + index * 52), person)
    else:
        icon_person(draw, 54, 356, None)
        text(draw, (126, 360), "No people", 24, bold=True)
        text(draw, (128, 400), "configured", 18)

    card(draw, (354, 284, 778, 462), SOFT_BLUE)
    media = active_sonos(sonos)
    media_room = fit_text(media.get("room"), 24, "No active room")
    media_title = fit_text(media.get("title") or media.get("artist") or "No active playback", 30)
    media_state = as_text(media.get("state"), "Idle").title()
    icon_music(draw, 382, 332)
    text(draw, (382, 306), media_label, 24, bold=True)
    text(draw, (466, 338), media_room, 33, bold=True)
    text(draw, (468, 386), media_title, 22)
    status_band(draw, (466, 420, 570, 450), media_state, ORANGE if media_state == "Playing" else YELLOW)
    text(draw, (590, 425), sonos_label, 18, bold=True)

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
