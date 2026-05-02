#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_DIR = ROOT / "plugins" / "trmnl-ha-dashboard"
REQUIRED_FILES = [
    "settings.yml",
    "fields.schema.json",
    "payload.example.json",
    "README.md",
    "full.liquid",
]
SLOT_NAMES = [
    "top_left",
    "top_right",
    "status_1",
    "status_2",
    "status_3",
    "bottom_left",
    "bottom_right",
]
SLOT_SUFFIXES = ["card_type", "entity", "label", "detail_label"]
CARD_TYPES = [
    "weather",
    "indoor",
    "door_lock",
    "cover",
    "washer",
    "light_group",
    "person_group",
    "media",
    "generic_entity",
    "hidden",
]
GENERIC_ENTITY_KEYS = {"id", "label", "state", "detail", "unit", "icon", "status_colour"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def load_settings() -> dict[str, Any]:
    with (PLUGIN_DIR / "settings.yml").open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_schema() -> dict[str, Any]:
    with (PLUGIN_DIR / "fields.schema.json").open("r", encoding="utf-8") as f:
        return json.load(f)


def load_payload() -> dict[str, Any]:
    with (PLUGIN_DIR / "payload.example.json").open("r", encoding="utf-8") as f:
        payload = json.load(f)
    merge_variables = payload.get("merge_variables")
    require(isinstance(merge_variables, dict), "payload.example.json must contain merge_variables object")
    return merge_variables


def validate_required_files() -> None:
    for name in REQUIRED_FILES:
        require((PLUGIN_DIR / name).exists(), f"Missing required plugin file: {name}")
    print("OK required plugin files")


def validate_fields(settings: dict[str, Any], schema: dict[str, Any]) -> None:
    require(settings.get("version") == schema.get("version"), "settings.yml and fields.schema.json versions differ")
    settings_fields = settings.get("custom_fields")
    schema_fields = schema.get("fields")
    require(isinstance(settings_fields, list), "settings.yml custom_fields must be a list")
    require(isinstance(schema_fields, list), "fields.schema.json fields must be a list")

    settings_keys = [field.get("keyname") for field in settings_fields]
    schema_keys = [field.get("key") for field in schema_fields]
    require(len(settings_keys) == len(set(settings_keys)), "settings.yml contains duplicate keyname values")
    require(len(schema_keys) == len(set(schema_keys)), "fields.schema.json contains duplicate key values")
    require(set(settings_keys) == set(schema_keys), "settings.yml and fields.schema.json field keys differ")

    schema_by_key = {field["key"]: field for field in schema_fields}
    for slot in SLOT_NAMES:
        for suffix in SLOT_SUFFIXES:
            key = f"{slot}_{suffix}"
            require(key in schema_by_key, f"Missing slot field in schema/settings: {key}")
        card_field = schema_by_key[f"{slot}_card_type"]
        require(card_field.get("allowed_values") == CARD_TYPES, f"{slot}_card_type allowed_values are not canonical")

    for key in ("generic_entities", "generic_labels", "generic_icons", "generic_status_colours"):
        require(key in schema_by_key, f"Missing generic field: {key}")

    print(f"OK field contract: {len(settings_keys)} fields")


def validate_payload(data: dict[str, Any]) -> None:
    for key in ("dashboard_title", "instance_label", "layout_variant", "colour_profile", "labels", "weather", "home", "people", "sonos", "slots", "generic_entities"):
        require(key in data, f"payload missing merge variable: {key}")

    slots = data["slots"]
    require(isinstance(slots, dict), "payload slots must be an object")
    require(set(slots) == set(SLOT_NAMES), "payload slots must contain exactly the canonical fixed slots")
    for slot in SLOT_NAMES:
        item = slots[slot]
        require(isinstance(item, dict), f"payload slot {slot} must be an object")
        require(item.get("type") in CARD_TYPES, f"payload slot {slot} has unsupported type {item.get('type')}")
        for key in ("entity", "label", "detail_label"):
            require(key in item, f"payload slot {slot} missing {key}")

    generic_entities = data["generic_entities"]
    require(isinstance(generic_entities, list), "payload generic_entities must be a list")
    for index, item in enumerate(generic_entities):
        require(isinstance(item, dict), f"generic_entities[{index}] must be an object")
        require(GENERIC_ENTITY_KEYS <= set(item), f"generic_entities[{index}] missing required keys")

    print("OK payload contract")


def main() -> None:
    validate_required_files()
    settings = load_settings()
    schema = load_schema()
    payload = load_payload()
    validate_fields(settings, schema)
    validate_payload(payload)


if __name__ == "__main__":
    main()
