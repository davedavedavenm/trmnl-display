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

`scripts/trmnl_refresh_ha_sidecar.sh` is the routine refresh wrapper. It pulls Home Assistant state, renders the seven-colour PNG, then calls `scripts/trmnl_update_ha_sidecar_image.sh`.

`scripts/trmnl_update_ha_sidecar_image.sh` remains the final LaraPaper handoff script. It updates the plugin image only.

The `khpi5` cron should call:

```sh
/home/dave/bin/trmnl-refresh-ha-sidecar
```

## Configurable Card Slots

The current `compact_grid` renderer is dynamic by data, labels, and fixed card slot intent. LaraPaper/plugin configuration chooses the card type and optional entity/labels for each slot; the sidecar renderer still owns safe pixel placement.

Implemented slot fields:

- `top_left_card_type`, `top_left_entity`, `top_left_label`, `top_left_detail_label`
- `top_right_card_type`, `top_right_entity`, `top_right_label`, `top_right_detail_label`
- `status_1_card_type`, `status_1_entity`, `status_1_label`, `status_1_detail_label`
- `status_2_card_type`, `status_2_entity`, `status_2_label`, `status_2_detail_label`
- `status_3_card_type`, `status_3_entity`, `status_3_label`, `status_3_detail_label`
- `bottom_left_card_type`, `bottom_left_entity`, `bottom_left_label`, `bottom_left_detail_label`
- `bottom_right_card_type`, `bottom_right_entity`, `bottom_right_label`, `bottom_right_detail_label`

Implemented card types:

- `weather`
- `indoor`
- `door_lock`
- `cover`
- `washer`
- `light_group`
- `person_group`
- `media`
- `generic_entity`
- `hidden`

Default slots preserve the current visual design: weather, indoor climate/humidity, door, blinds, washer, people, and media.

## Generic Entity Contract

To support useful non-HA or homelab data, the payload includes a `generic_entities` array.

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

Implemented improvement:

- `scripts/trmnl_mode_bridge.py` exposes authenticated `POST /ha-dashboard/refresh`
- the endpoint runs `/home/dave/bin/trmnl-refresh-ha-sidecar`
- Home Assistant can call the endpoint when configured `media_player.*` entities change state, title, or artist
- the endpoint rate-limits successful refreshes with a default 120-second cooldown unless `{"force": true}` is posted

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
