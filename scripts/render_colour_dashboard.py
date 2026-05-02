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
    size = 13 if (box[3] - box[1]) <= 22 else 15
    centered_text(draw, (box[0] + 6, box[1] + 1, box[2] - 6, box[3] - 1), fit_text(label, 12), size, bold=True)


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


def status_column(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    title: str,
    value: str,
    detail: str,
    fill: tuple[int, int, int],
    icon_fn: Callable[[ImageDraw.ImageDraw, int, int], None],
) -> None:
    draw.rounded_rectangle(box, radius=7, fill=fill, outline=BLACK, width=2)
    icon_fn(draw, box[0] + 14, box[1] + 6)
    text(draw, (box[0] + 86, box[1] + 8), fit_text(title, 14), 17, bold=True)
    text(draw, (box[0] + 86, box[1] + 38), fit_text(value, 12), 28, bold=True)


def indoor_card(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    thermostat_label: str,
    thermostat_value: str,
    thermostat_detail: str,
    humidity_value: str,
    humidity_detail: str,
) -> None:
    card(draw, box, SOFT_ORANGE)
    text(draw, (box[0] + 22, box[1] + 16), "Indoor", 22, bold=True)
    draw.line((box[0] + 188, box[1] + 18, box[0] + 188, box[3] - 18), fill=BLACK, width=2)
    icon_thermo(draw, box[0] + 22, box[1] + 46)
    text(draw, (box[0] + 84, box[1] + 45), fit_text(thermostat_label, 12), 16, bold=True)
    text(draw, (box[0] + 84, box[1] + 72), thermostat_value, 30, bold=True)
    icon_drop(draw, box[0] + 212, box[1] + 45)
    text(draw, (box[0] + 274, box[1] + 45), "Humidity", 16, bold=True)
    text(draw, (box[0] + 274, box[1] + 72), humidity_value, 30, bold=True)


def person_row(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], person: dict[str, Any]) -> None:
    name = fit_text(person.get("name"), 16, "Person")
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
    text(draw, (box[0] + 74, box[1] + 4), name, 24, bold=True)
    status_band(draw, (box[0] + 74, box[1] + 31, box[2] - 14, box[1] + 53), state_label, accent)


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


def slot(data: dict[str, Any], name: str, default_type: str) -> dict[str, Any]:
    slots = data.get("slots") if isinstance(data.get("slots"), dict) else {}
    item = slots.get(name) if isinstance(slots.get(name), dict) else {}
    return {"type": default_type, **item}


def slot_text(item: dict[str, Any], key: str, fallback: str) -> str:
    return as_text(item.get(key), fallback)


def status_colour(value: Any, fallback: tuple[int, int, int] = SOFT_GREY) -> tuple[int, int, int]:
    key = as_text(value, "").lower().replace(" ", "_")
    return {
        "green": SOFT_GREEN,
        "yellow": SOFT_YELLOW,
        "orange": SOFT_ORANGE,
        "red": (255, 220, 220),
        "blue": SOFT_BLUE,
        "white": WHITE,
        "grey": SOFT_GREY,
        "gray": SOFT_GREY,
    }.get(key, fallback)


def generic_entity(data: dict[str, Any], entity_id: str = "") -> dict[str, Any]:
    entities = data.get("generic_entities") if isinstance(data.get("generic_entities"), list) else []
    for item in entities:
        if isinstance(item, dict) and entity_id and item.get("id") == entity_id:
            return item
    for item in entities:
        if isinstance(item, dict):
            return item
    return {}


def icon_generic(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    draw.rounded_rectangle((x + 8, y + 8, x + 50, y + 50), radius=5, fill=WHITE, outline=BLACK, width=3)
    draw.line((x + 16, y + 22, x + 42, y + 22), fill=BLACK, width=3)
    draw.line((x + 16, y + 36, x + 42, y + 36), fill=BLACK, width=3)
    draw.ellipse((x + 18, y + 42, x + 26, y + 50), fill=GREEN, outline=BLACK, width=1)


def icon_light_group(draw: ImageDraw.ImageDraw, x: int, y: int, active: bool | None = None) -> None:
    fill = YELLOW if active else WHITE if active is False else SOFT_GREY
    draw.ellipse((x + 14, y + 4, x + 46, y + 36), fill=fill, outline=BLACK, width=3)
    draw.rectangle((x + 22, y + 35, x + 38, y + 52), fill=WHITE, outline=BLACK, width=2)
    draw.line((x + 18, y + 56, x + 42, y + 56), fill=BLACK, width=3)


def render_generic_metric(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], item: dict[str, Any], title: str = "") -> None:
    label = fit_text(title or item.get("label"), 14, "Status")
    state = fit_text(as_text(item.get("state"), "--") + as_text(item.get("unit"), ""), 10)
    detail = fit_text(item.get("detail"), 18, "")
    metric(draw, box, label, state, detail, status_colour(item.get("status_colour"), WHITE), icon_generic)


def render_generic_status(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], item: dict[str, Any], title: str = "") -> None:
    label = fit_text(title or item.get("label"), 14, "Status")
    state = fit_text(as_text(item.get("state"), "--") + as_text(item.get("unit"), ""), 12)
    detail = fit_text(item.get("detail"), 12, "")
    status_column(draw, box, label, state, detail, status_colour(item.get("status_colour"), WHITE), icon_generic)


def light_summary(lights: list[Any]) -> tuple[str, str, bool | None]:
    valid = [item for item in lights if isinstance(item, dict)]
    if not valid:
        return "Lights", "--", None
    on_count = sum(1 for item in valid if item.get("on") is True)
    return "Lights", f"{on_count}/{len(valid)} on", on_count > 0


def render_dashboard(data: dict[str, Any]) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT), SOURCE_BG)
    draw = ImageDraw.Draw(img)

    weather = data.get("weather") if isinstance(data.get("weather"), dict) else {}
    home = data.get("home") if isinstance(data.get("home"), dict) else {}
    people = data.get("people") if isinstance(data.get("people"), list) else []
    sonos = data.get("sonos") if isinstance(data.get("sonos"), list) else []
    lights = data.get("lights") if isinstance(data.get("lights"), list) else []
    labels = data.get("labels") if isinstance(data.get("labels"), dict) else {}
    top_left_slot = slot(data, "top_left", "weather")
    top_right_slot = slot(data, "top_right", "indoor")
    status_1_slot = slot(data, "status_1", "door_lock")
    status_2_slot = slot(data, "status_2", "cover")
    status_3_slot = slot(data, "status_3", "washer")
    bottom_left_slot = slot(data, "bottom_left", "person_group")
    bottom_right_slot = slot(data, "bottom_right", "media")

    instance_label = fit_text(data.get("instance_label"), 18, "Home")
    thermostat_label = fit_text(labels.get("thermostat"), 10, "Climate")
    thermostat_detail = fit_text(labels.get("thermostat_detail"), 16, "Indoor")
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

    top_left_type = as_text(top_left_slot.get("type"), "weather")
    if top_left_type == "weather":
        metric(
            draw,
            (22, 18, 354, 136),
            slot_text(top_left_slot, "label", "Weather"),
            format_temp(temp),
            condition_label,
            SOFT_YELLOW,
            lambda d, x, y: icon_sun_cloud_compact(d, x, y, condition),
        )
    elif top_left_type == "generic_entity":
        render_generic_metric(draw, (22, 18, 354, 136), generic_entity(data, as_text(top_left_slot.get("entity"), "")), slot_text(top_left_slot, "label", ""))
    elif top_left_type != "hidden":
        render_generic_metric(draw, (22, 18, 354, 136), {}, slot_text(top_left_slot, "label", top_left_type.replace("_", " ").title()))

    top_right_type = as_text(top_right_slot.get("type"), "indoor")
    if top_right_type == "indoor":
        indoor_card(
            draw,
            (376, 18, 778, 136),
            thermostat_label,
            format_temp(thermostat, with_unit=True),
            thermostat_detail,
            f"{humidity:.0f}%" if humidity is not None else "--%",
            instance_label,
        )
    elif top_right_type == "weather":
        metric(
            draw,
            (376, 18, 778, 136),
            slot_text(top_right_slot, "label", "Weather"),
            format_temp(temp),
            condition_label,
            SOFT_YELLOW,
            lambda d, x, y: icon_sun_cloud_compact(d, x, y, condition),
        )
    elif top_right_type == "generic_entity":
        render_generic_metric(draw, (376, 18, 778, 136), generic_entity(data, as_text(top_right_slot.get("entity"), "")), slot_text(top_right_slot, "label", ""))
    elif top_right_type != "hidden":
        render_generic_metric(draw, (376, 18, 778, 136), {}, slot_text(top_right_slot, "label", top_right_type.replace("_", " ").title()))

    card(draw, (22, 154, 778, 286), WHITE)
    text(draw, (44, 174), "Home status", 22, bold=True)
    for item, box in (
        (status_1_slot, (44, 206, 276, 278)),
        (status_2_slot, (294, 206, 526, 278)),
        (status_3_slot, (544, 206, 756, 278)),
    ):
        card_type = as_text(item.get("type"), "generic_entity")
        if card_type == "door_lock":
            status_column(
                draw,
                box,
                fit_text(slot_text(item, "label", labels.get("door") or "Front door"), 10, "Front door"),
                "Locked" if locked else "Open" if locked is False else "--",
                "Secure" if locked else fit_text(slot_text(item, "detail_label", labels.get("door_detail") or "Security"), 18, "Security") if locked is False else "Unavailable",
                SOFT_GREEN if locked else SOFT_ORANGE,
                lambda d, x, y: icon_lock(d, x, y, locked),
            )
        elif card_type == "cover":
            status_column(
                draw,
                box,
                fit_text(slot_text(item, "label", labels.get("blinds") or "Blinds"), 10, "Blinds"),
                "Open" if blinds_open else "Closed" if blinds_open is False else "--",
                fit_text(slot_text(item, "detail_label", labels.get("blinds_detail") or "Position"), 12, "Position"),
                SOFT_GREEN if blinds_open else SOFT_GREY,
                lambda d, x, y: icon_blinds(d, x, y, blinds_open),
            )
        elif card_type == "washer":
            status_column(
                draw,
                box,
                fit_text(slot_text(item, "label", labels.get("washer") or "Washer"), 10, "Washer"),
                "Running" if washer_running else "Idle" if washer_running is False else "--",
                fit_text(slot_text(item, "detail_label", labels.get("washer_detail") or "Utility"), 12, "Utility"),
                SOFT_BLUE if washer_running else SOFT_GREY,
                lambda d, x, y: icon_washer(d, x, y, washer_running),
            )
        elif card_type == "light_group":
            light_title, light_value, light_active = light_summary(lights)
            status_column(
                draw,
                box,
                slot_text(item, "label", light_title),
                light_value,
                slot_text(item, "detail_label", "Lights"),
                SOFT_YELLOW if light_active else SOFT_GREY,
                lambda d, x, y: icon_light_group(d, x, y, light_active),
            )
        elif card_type == "generic_entity":
            render_generic_status(draw, box, generic_entity(data, as_text(item.get("entity"), "")), slot_text(item, "label", ""))
        elif card_type != "hidden":
            render_generic_status(draw, box, {}, slot_text(item, "label", card_type.replace("_", " ").title()))

    bottom_left_type = as_text(bottom_left_slot.get("type"), "person_group")
    if bottom_left_type == "person_group":
        card(draw, (22, 302, 332, 462), SOFT_GREEN)
        text(draw, (44, 320), slot_text(bottom_left_slot, "label", people_label), 24, bold=True)
        visible_people = [p for p in people[:2] if isinstance(p, dict)]
        if visible_people:
            for index, person in enumerate(visible_people):
                person_row(draw, (44, 350 + index * 54, 310, 404 + index * 54), person)
        else:
            icon_person(draw, 54, 366, None)
            text(draw, (126, 370), "No people", 24, bold=True)
            text(draw, (128, 410), "configured", 18)
    elif bottom_left_type == "media":
        card(draw, (22, 302, 332, 462), SOFT_BLUE)
        media = active_sonos(sonos)
        media_room = fit_text(media.get("room"), 18, "No active room")
        media_title = fit_text(media.get("title") or media.get("artist") or "No active playback", 20)
        media_state = as_text(media.get("state"), "Idle").title()
        icon_music_compact(draw, 44, 344)
        text(draw, (44, 320), slot_text(bottom_left_slot, "label", media_label), 24, bold=True)
        text(draw, (126, 350), media_room, 23, bold=True)
        text(draw, (128, 390), media_title, 18)
        status_band(draw, (128, 420, 230, 450), media_state, ORANGE if media_state == "Playing" else YELLOW)
    elif bottom_left_type == "generic_entity":
        render_generic_metric(draw, (22, 302, 332, 462), generic_entity(data, as_text(bottom_left_slot.get("entity"), "")), slot_text(bottom_left_slot, "label", ""))
    elif bottom_left_type != "hidden":
        render_generic_metric(draw, (22, 302, 332, 462), {}, slot_text(bottom_left_slot, "label", bottom_left_type.replace("_", " ").title()))

    bottom_right_type = as_text(bottom_right_slot.get("type"), "media")
    if bottom_right_type == "media":
        card(draw, (354, 302, 778, 462), SOFT_BLUE)
        media = active_sonos(sonos)
        media_room = fit_text(media.get("room"), 24, "No active room")
        media_title = fit_text(media.get("title") or media.get("artist") or "No active playback", 30)
        media_state = as_text(media.get("state"), "Idle").title()
        icon_music(draw, 382, 344)
        text(draw, (382, 320), slot_text(bottom_right_slot, "label", media_label), 24, bold=True)
        text(draw, (466, 350), media_room, 33, bold=True)
        text(draw, (468, 396), media_title, 22)
        status_band(draw, (466, 422, 570, 452), media_state, ORANGE if media_state == "Playing" else YELLOW)
        text(draw, (590, 427), slot_text(bottom_right_slot, "detail_label", sonos_label), 18, bold=True)
    elif bottom_right_type == "person_group":
        card(draw, (354, 302, 778, 462), SOFT_GREEN)
        text(draw, (382, 320), slot_text(bottom_right_slot, "label", people_label), 24, bold=True)
        visible_people = [p for p in people[:3] if isinstance(p, dict)]
        if visible_people:
            for index, person in enumerate(visible_people[:2]):
                person_row(draw, (382, 350 + index * 54, 734, 404 + index * 54), person)
        else:
            icon_person(draw, 382, 366, None)
            text(draw, (466, 370), "No people configured", 24, bold=True)
    elif bottom_right_type == "generic_entity":
        render_generic_metric(draw, (354, 302, 778, 462), generic_entity(data, as_text(bottom_right_slot.get("entity"), "")), slot_text(bottom_right_slot, "label", ""))
    elif bottom_right_type != "hidden":
        render_generic_metric(draw, (354, 302, 778, 462), {}, slot_text(bottom_right_slot, "label", bottom_right_type.replace("_", " ").title()))

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
