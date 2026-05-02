#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

from PIL import Image

import render_colour_dashboard as renderer


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PAYLOAD = ROOT / "plugins" / "trmnl-ha-dashboard" / "payload.example.json"
DEFAULT_OUT_DIR = ROOT / "scripts" / "tmp" / "colour_dashboard_validation"
SLOT_DEFAULTS = {
    "top_left": "weather",
    "top_right": "indoor",
    "status_1": "door_lock",
    "status_2": "cover",
    "status_3": "washer",
    "bottom_left": "person_group",
    "bottom_right": "media",
}
CARD_TYPE_CASES = {
    "weather": ("top_left", "weather"),
    "indoor": ("top_right", "indoor"),
    "door_lock": ("status_1", "door_lock"),
    "cover": ("status_2", "cover"),
    "washer": ("status_3", "washer"),
    "light_group": ("status_1", "light_group"),
    "person_group": ("bottom_left", "person_group"),
    "media": ("bottom_right", "media"),
    "generic_entity": ("status_1", "generic_entity"),
    "hidden": ("status_1", "hidden"),
}
EXPECTED_RGB = {
    (0, 0, 0),
    (255, 255, 255),
    (255, 0, 0),
    (255, 255, 0),
    (0, 0, 255),
    (0, 255, 0),
    (255, 128, 0),
}


def load_payload(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    if isinstance(raw, dict) and isinstance(raw.get("merge_variables"), dict):
        return raw["merge_variables"]
    if isinstance(raw, dict):
        return raw
    raise ValueError(f"Unsupported payload shape: {path}")


def ensure_defaults(data: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(data)
    slots = result.setdefault("slots", {})
    for name, card_type in SLOT_DEFAULTS.items():
        slots.setdefault(name, {})
        slots[name].setdefault("type", card_type)
        slots[name].setdefault("entity", "")
        slots[name].setdefault("label", "")
        slots[name].setdefault("detail_label", "")
    result["generic_entities"] = [
        {
            "id": "sensor.validation_generic",
            "label": "Validation",
            "state": "OK",
            "detail": "Generic",
            "unit": "",
            "icon": "server",
            "status_colour": "green",
        }
    ]
    return result


def render_case(name: str, data: dict[str, Any], out_dir: Path | None) -> tuple[str, int]:
    source = renderer.render_dashboard(data)
    image = renderer.remap_to_panel_palette(source)
    colors = image.convert("RGB").getcolors(maxcolors=256) or []
    rgb = {colour for _, colour in colors}

    if image.mode != "P":
        raise AssertionError(f"{name}: expected paletted P image, got {image.mode}")
    if image.size != (renderer.WIDTH, renderer.HEIGHT):
        raise AssertionError(f"{name}: expected 800x480, got {image.size}")
    if rgb - EXPECTED_RGB:
        raise AssertionError(f"{name}: found colours outside panel palette: {sorted(rgb - EXPECTED_RGB)}")
    if len(rgb) != 7:
        raise AssertionError(f"{name}: expected all 7 panel colours in use, got {len(rgb)}")

    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)
        image.save(out_dir / f"{name}.png", optimize=True)
        source.save(out_dir / f"{name}_source.png")

    return name, len(rgb)


def build_cases(base: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    cases: list[tuple[str, dict[str, Any]]] = [("default", copy.deepcopy(base))]

    for card_type, (slot_name, slot_type) in CARD_TYPE_CASES.items():
        data = copy.deepcopy(base)
        data["slots"][slot_name]["type"] = slot_type
        if slot_type == "generic_entity":
            data["slots"][slot_name]["entity"] = "sensor.validation_generic"
            data["slots"][slot_name]["label"] = "Generic"
        cases.append((f"card_type_{card_type}", data))

    for slot_name in SLOT_DEFAULTS:
        data = copy.deepcopy(base)
        data["slots"][slot_name]["type"] = "generic_entity"
        data["slots"][slot_name]["entity"] = "sensor.validation_generic"
        data["slots"][slot_name]["label"] = "Generic"
        cases.append((f"slot_{slot_name}_generic", data))

    for slot_name in SLOT_DEFAULTS:
        data = copy.deepcopy(base)
        data["slots"][slot_name]["type"] = "hidden"
        cases.append((f"slot_{slot_name}_hidden", data))

    return cases


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate HA colour sidecar slot rendering.")
    parser.add_argument("--payload", type=Path, default=DEFAULT_PAYLOAD)
    parser.add_argument("--write-images", action="store_true", help="Write validation images under scripts/tmp.")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    base = ensure_defaults(load_payload(args.payload))
    out_dir = args.out_dir if args.write_images else None

    for name, data in build_cases(base):
        _, count = render_case(name, data, out_dir)
        print(f"OK {name}: {count} colours")


if __name__ == "__main__":
    main()
