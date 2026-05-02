# HA Colour Dashboard Plan

Date: 2026-05-02

This document records the plan for turning the accepted Home Assistant colour sidecar into a playlist-safe, shareable LaraPaper/TRMNL plugin surface.

## Current Data Direction

The live dashboard is not rendered by the Pi and Home Assistant does not push an image directly to the Pi.

Current flow:

1. `scripts/trmnl_ha_dashboard.py` runs on `khpi5`.
2. It pulls selected state from Home Assistant through the HA REST API.
3. It builds a TRMNL `merge_variables` payload.
4. It posts that payload to the LaraPaper plugin webhook.
5. It writes the same payload to `/home/dave/trmnl-ha-dashboard-payload.json` when `TRMNL_SIDECAR_PAYLOAD_PATH` is set.
6. `scripts/render_colour_dashboard.py` renders the payload to an indexed seven-colour `800x480` PNG.
7. `scripts/trmnl_update_ha_sidecar_image.sh` copies that PNG into LaraPaper generated-image storage and updates the `Home Assistant` plugin image.
8. LaraPaper serves the image through the normal playlist and `/api/display` BYOS path.
9. `trmnl-pi` polls LaraPaper and displays the returned image.

## Playlist-Safe Requirement

The sidecar image must be usable as one plugin item in a normal LaraPaper playlist. Routine refreshes must not activate the HA dashboard playlist or override unrelated playlists.

Allowed routine update:

- update the `Home Assistant` plugin's `current_image`
- update plugin image metadata
- leave LaraPaper playlists untouched
- leave the device's `current_screen_image` untouched

Manual test mode:

- `trmnl-set-display-mode ha_dashboard` may still activate the HA-only playlist when deliberately testing or switching modes.

## Implemented Playlist-Safe Step

`scripts/trmnl_update_ha_sidecar_image.sh` is the routine handoff script. It updates the plugin image only.

The `khpi5` cron should call:

```sh
cd /home/dave
python3 /home/dave/trmnl_ha_dashboard.py
python3 /home/dave/render_colour_dashboard.py --payload /home/dave/trmnl-ha-dashboard-payload.json --output /home/dave/sidecar_colour_dashboard_next.png --source-output /home/dave/sidecar_colour_dashboard_source_next.png
/home/dave/bin/trmnl-update-ha-sidecar-image
```

## Dynamic Card Roadmap

The current `compact_grid` renderer is dynamic by data and labels, but not yet fully dynamic by card placement. The next step is a plugin slot contract.

Proposed slot fields:

- `slot_1_type`
- `slot_1_entity`
- `slot_1_label`
- `slot_1_detail_label`
- `slot_2_type`
- `slot_2_entity`
- `slot_2_label`
- `slot_2_detail_label`
- repeat for each supported visible slot

Proposed card types:

- `weather`
- `indoor`
- `person_group`
- `media`
- `door_lock`
- `washer`
- `cover`
- `light_group`
- `generic_entity`

The renderer should keep the current visual design as the default preset. Slot configuration should map onto fixed, readable card templates instead of allowing arbitrary pixel positioning.

## Generic Entity Contract

To support useful non-HA or homelab data, add a `generic_entities` payload array.

Proposed item shape:

```json
{
  "id": "sensor.example",
  "label": "Example",
  "state": "OK",
  "detail": "Updated recently",
  "unit": "",
  "icon": "server",
  "status_colour": "green"
}
```

`status_colour` should map to the seven-colour panel palette, not arbitrary RGB.

## Sonos Refresh Behavior

Sonos currently updates when the companion script next pulls Home Assistant media player state. With a 10-minute cron, the practical latency is up to about 10 minutes plus e-paper refresh time.

Future improvement:

- add a Home Assistant automation that triggers the companion update when configured `media_player.*` entities change state or media title
- keep the same playlist-safe sidecar update script
- optionally rate-limit updates to avoid excessive panel refreshes

## Validation Requirements

For each implementation step:

1. Run local syntax checks.
2. Render from `plugins/trmnl-ha-dashboard/payload.example.json`.
3. Visually inspect `scripts/tmp/sidecar_colour_dashboard_next.png`.
4. Confirm `800x480`, indexed `P`, seven colours.
5. Deploy only the changed scripts to `khpi5`.
6. Run the playlist-safe update command.
7. Verify LaraPaper plugin image metadata without changing active playlist unless explicitly testing mode activation.
8. If appropriate, restart the Pi display client and confirm `800 x 480, 8-bpp`, `Preparing image for EPD as 4-bpp`, and `Refresh complete`.
