# HA Dashboard Plugin

A shareable Home Assistant dashboard plugin for TRMNL / LaraPaper.

This plugin has two render paths:

- `full.liquid` for normal TRMNL/LaraPaper plugin compatibility
- `scripts/render_colour_dashboard.py` as the current colour sidecar proof for Pimoroni Inky Impression 7.3 / Spectra-class panels

The sidecar exists only to improve colour reproduction. The plugin must still remain configurable and shareable like a normal TRMNL recipe.

## Features

- Shareable plugin metadata in `settings.yml`
- User-editable fields for Home Assistant URL, entity IDs, labels, layout, and colour profile
- Webhook payloads using TRMNL `merge_variables`
- Liquid compatibility template in `full.liquid`
- Optional indexed seven-colour sidecar renderer for colour e-paper output
- Sample payload in `payload.example.json`
- Field contract in `fields.schema.json`

## Setup

1. Import the `settings.yml` and `full.liquid` into your TRMNL / LaraPaper instance as a new custom plugin.
2. Note your newly generated Webhook URL.
3. Configure the Python sync script (`trmnl_ha_dashboard.py`) with your `HA_URL`, `HA_TOKEN`, and `TRMNL_WEBHOOK_URL`.
4. Run the script via cron or a Home Assistant automation to push state updates to the display.

## Configuration Fields

| Field | Required | Purpose |
|---|---:|---|
| `dashboard_title` | No | Header title, default `Home Assistant` |
| `instance_label` | No | Short instance label, default `Home` |
| `layout_variant` | No | Preferred layout, default `compact_grid` |
| `colour_profile` | No | Renderer profile, default `inky_spectra_7` |
| `ha_url` | Yes | Home Assistant base URL |
| `ha_token` | Yes | Home Assistant long-lived token; do not commit live values |
| `weather_entity` | No | Weather entity |
| `person_entities` | No | Comma-separated person entities |
| `sonos_entities` | No | Comma-separated media players |
| `door_entity` | No | Door or lock entity |
| `washer_entity` | No | Laundry status entity |
| `blind_entity` | No | Blind/cover entity |
| `thermostat_entity` | No | Climate or temperature entity |

Keep `settings.yml` and `fields.schema.json` aligned when adding or renaming fields.

## Payload Contract

Webhook updates must use TRMNL's `merge_variables` wrapper. See `payload.example.json`.

Top-level merge variables:

- `dashboard_title`
- `instance_label`
- `updated_at`
- `weather`
- `home`
- `people`
- `sonos`

Missing optional values should render as unavailable, blank, or hidden rather than failing the screen.

## Sidecar Compatibility

The sidecar renderer must follow the same field and payload contract as the plugin. It may use a stronger colour pipeline, but it must not become a private hardcoded dashboard that other users cannot configure.

The current proof renderer is intentionally static while the colour pipeline is being validated. Before making it the live path, wire it to the field contract and `merge_variables` payload described here.

## Compatibility

The Liquid template is intended to remain broadly TRMNL/LaraPaper compatible.

The sidecar colour path is designed for the Pimoroni Inky Impression 7.3" / Spectra-class `800x480` colour panel. Other panels should use a different `colour_profile`.
