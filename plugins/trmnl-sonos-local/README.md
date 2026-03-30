# TRMNL Sonos Local

Local-network Sonos now-playing plugin for LaraPaper/TRMNL BYOS.

This plugin avoids TRMNL cloud OAuth entirely. A companion Python script uses the Sonos LAN API via `soco` to discover speakers, detect the active room or group, and POST now-playing data to a LaraPaper webhook plugin.

Current capabilities:
- local Sonos discovery
- active room selection
- grouped-room awareness
- multiple active room awareness
- current title / artist / album
- album art with selectable render modes
- queue preview (`Up Next`)
- shareable recipe structure (`settings.yml` + `full.liquid`)

Companion script:
- `scripts/trmnl_sonos_local.py`

Recipe files:
- `plugins/trmnl-sonos-local/settings.yml`
- `plugins/trmnl-sonos-local/full.liquid`

Suggested runtime env:

```env
TRMNL_WEBHOOK_URL=http://localhost:4567/api/custom_plugins/YOUR-UUID
TRMNL_SONOS_ROOM=
TRMNL_UPDATED_AT_FORMAT="%d %b %H:%M"
TRMNL_ALBUM_ART_SATURATION=0.65
TRMNL_ALBUM_ART_CONTRAST=1.1
TRMNL_ALBUM_ART_BALANCED_SATURATION=0.9
TRMNL_ALBUM_ART_BALANCED_CONTRAST=1.05
TRMNL_ALBUM_ART_VIVID_SATURATION=1.2
TRMNL_ALBUM_ART_VIVID_CONTRAST=1.0
TRMNL_ALBUM_ART_MONO_SATURATION=0.0
TRMNL_ALBUM_ART_MONO_CONTRAST=1.1
```

Notes:
- If `TRMNL_SONOS_ROOM` is blank, the script picks the first actively playing group, then falls back to the first room with track metadata.
- The plugin can be driven either by the local Sonos script or by Home Assistant automations pushing webhook payloads.
- For the current 7-colour ACeP display, colour output is a requirement. If preprocessing is adjusted for readability, keep a colour-capable path available rather than silently drifting into grayscale-like output.
- If the Sonos screen suddenly becomes grayscale, check the LaraPaper preview/current PNG and the live `inky_impression_7_3` device model on `khpi5` before changing recipe code.

## Configuration Reference

The recipe exposes these user-facing options:

- `Theme`
  - `dark` or `light`
- `Album Art Mode`
  - `vivid`, `balanced`, `raw`, or `mono`
- `Preferred Room`
  - optional room name to pin instead of auto-selection
- `Show Album`
  - show/hide album name
- `Show Album Art`
  - show/hide cover art block
- `Show Up Next`
  - show/hide queue preview when available

The local script provides these payload features:

- room name
- playback state
- track / artist / album
- album art URL
- preprocessed album-art variants for shareable recipe modes
- grouped-room context
- multiple active room context
- next tracks from queue

If you share this plugin, note that the recipe alone is not enough: it requires a companion local process to discover Sonos speakers and POST webhook data.

To keep the recipe shareable, the user-facing render choice lives in `settings.yml` and the script sends all artwork variants needed by the template. That keeps the recipe exportable while still allowing local tuning on the server.

## Automatic Refresh

On the current homelab setup, the Sonos script is run every minute on `khpi5` via cron using a small wrapper script:

- `/home/dave/run_trmnl_sonos.sh`
- `/home/dave/.env.sonos-trmnl`

That keeps the LaraPaper webhook plugin updated without any cloud dependency.

This also means a repo-only change is not enough. Update the live script/template on `khpi5`, trigger a fresh run, and verify the physical display after each Sonos change.

## Home Assistant Integration Options

If you already have Sonos entities in Home Assistant, there are two good local integration patterns:

1. **Automation -> webhook payload**
   - Trigger on `media_player` state/title changes.
   - Use a `rest_command` or `command_line`/`shell_command` to POST directly to the LaraPaper webhook.
   - Best if Home Assistant is already your source of truth for Sonos state.

2. **Automation -> run local script**
   - Trigger on `media_player` changes.
   - Use a local trigger path on `khpi5` to run `trmnl_sonos_local.py`.
   - Best if you want to keep the Sonos LAN logic in one place.

The first option may be simpler if you want HA-driven automations such as:
- only show Sonos screen while music is playing
- switch playlist on playback start/stop
- pick a preferred room automatically by context
