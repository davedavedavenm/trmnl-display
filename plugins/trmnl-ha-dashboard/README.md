# HA Dashboard Plugin

A shareable Home Assistant dashboard plugin for TRMNL / LaraPaper.

This plugin has two render paths:

- `full.liquid` for normal TRMNL/LaraPaper plugin compatibility
- `scripts/render_colour_dashboard.py` as the indexed colour sidecar renderer for Pimoroni Inky Impression 7.3 / Spectra-class panels

The sidecar exists to preserve the accepted colour proof style on the live Spectra-class panel: icon-led cards, black outlines, readable text, and the seven-colour panel palette. Do not replace this path with the muted LaraPaper-style green/olive render. The plugin must still remain configurable and shareable like a normal TRMNL recipe.

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
| `light_entities` | No | Comma-separated lights for the three room control cards |
| `door_entity` | No | Door or lock entity |
| `washer_entity` | No | Laundry status entity |
| `blind_entity` | No | Blind/cover entity |
| `blind_open_position` | No | Position value that means fully open; default `100`, use `0` for inverted controllers |
| `thermostat_entity` | No | Climate or temperature entity |
| `energy_entity` | No | Energy sensor for the bottom-right summary card |

Keep `settings.yml` and `fields.schema.json` aligned when adding or renaming fields.

## Payload Contract

Webhook updates must use TRMNL's `merge_variables` wrapper. See `payload.example.json`.

Top-level merge variables:

- `dashboard_title`
- `instance_label`
- `layout_variant`
- `colour_profile`
- `updated_at`
- `weather`
- `home`
- `people`
- `lights`
- `sonos`
- `energy`

Missing optional values should render as unavailable, blank, or hidden rather than failing the screen.

Nested merge variables:

- `weather`: `condition`, `condition_label`, `temperature`, `humidity`, `wind_speed`
- `home`: `door_locked`, `washer_running`, `blind_position`, `blinds_open`, `thermostat_temp`
- `people[]`: `name`, `state`
- `lights[]`: `label`, `state`, `on`
- `sonos[]`: `room`, `state`, `title`, `artist`, `picture`
- `energy`: `label`, `value`, `bars`

## Sidecar Compatibility

The canonical accepted sidecar reference is:

```text
scripts/tmp/sidecar_colour_dashboard_proof_2026-05-01.png
```

That file is intentionally tracked as a reference and must not be overwritten by normal renderer runs. The current renderer writes the next iteration to:

```text
scripts/tmp/sidecar_colour_dashboard_source_next.png
scripts/tmp/sidecar_colour_dashboard_next.png
```

The sidecar renderer follows the same field and payload contract as the plugin. It may use a stronger colour pipeline, but it must not become a private hardcoded dashboard that other users cannot configure.

Render a payload locally:

```bash
python scripts/render_colour_dashboard.py --payload plugins/trmnl-ha-dashboard/payload.example.json
```

The companion script can also write the exact live webhook payload for sidecar rendering when `TRMNL_SIDECAR_PAYLOAD_PATH` is set.

## Compatibility

The Liquid template is intended to remain broadly TRMNL/LaraPaper compatible.

The sidecar colour path is designed for the Pimoroni Inky Impression 7.3" / Spectra-class `800x480` colour panel. Other panels should use a different `colour_profile`.
