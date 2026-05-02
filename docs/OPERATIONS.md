# Operations

This document is the quick operational runbook for the live TRMNL display stack.

## Health Checks

LaraPaper on `khpi5`:

```bash
ssh khpi5 "docker ps --filter name=larapaper-app-1"
ssh khpi5 "curl -fsS http://127.0.0.1:4567/up || true"
ssh khpi5 "/home/dave/bin/trmnl-set-display-mode status"
```

Mode bridge on `khpi5`:

```bash
ssh khpi5 "systemctl status trmnl-mode-bridge.service --no-pager"
ssh khpi5 "journalctl -u trmnl-mode-bridge.service --no-pager -n 80"
```

Display client on `trmnl-pi`:

```bash
ssh trmnl-pi "systemctl status trmnl-display.service --no-pager"
ssh trmnl-pi "journalctl -u trmnl-display.service --no-pager -n 80"
```

Home Assistant:

```bash
ssh home-assistant "ha core info"
ssh home-assistant "grep -RIn 'trmnl' /config/packages | head -120"
```

## Normal Refresh Flow

1. Companion scripts push plugin payloads into LaraPaper.
2. Home Assistant selects a display mode.
3. Home Assistant calls the `khpi5` mode bridge.
4. The bridge activates the matching LaraPaper playlist.
5. `trmnl-pi` polls `http://192.168.1.143:4567/api/display`.
6. The Pi downloads the generated PNG and displays it with `show_img.bin`.

For colour-critical dashboard work, use the sidecar path in `docs/COLOUR_SIDECAR_PATH.md`. LaraPaper remains the BYOS management layer; the accepted HA colour-dashboard renderer is repo-owned, emits an indexed/paletted `800x480` PNG, and is handed off through LaraPaper's generated-image storage.

Routine HA sidecar refreshes must be playlist-safe: update the Home Assistant plugin's `current_image`, but do not activate playlists or update the device's `current_screen_image`. Manual mode activation remains available through `trmnl-set-display-mode ha_dashboard` when testing or intentionally switching to the HA-only playlist.

## Cron Jobs

The TRMNL-specific `khpi5` cron entries are recorded in `deploy/khpi5/trmnl-crontab.txt`.

Current jobs:

- LaraPaper image update daily at `04:00`
- Multi-calendar payload every `5` minutes
- Sonos payload every minute
- Home Assistant dashboard payload every `10` minutes

## Common Incidents

### LaraPaper dashboard works through proxy but not local IP

The proxied UI and LAN UI are different browser origins:

- proxy: `https://trmnl.magnusfamily.co.uk`
- LAN: `http://192.168.1.143:4567`

If `/dashboard` on the LAN IP redirects to `/login`, that is expected for an unauthenticated LAN session. Sign in separately on the LAN origin, or use the proxied URL for routine web UI work.

If the LaraPaper UI loads on the LAN IP but the device screen preview is broken, check the generated image URL. With `APP_URL=https://trmnl.magnusfamily.co.uk`, LaraPaper's default `Storage::disk('public')->url(...)` can emit an absolute proxied image URL. The LAN page then tries to load the preview through Pangolin, which can redirect the image request to auth and leave only the image alt text visible.

The live deployment carries a local LaraPaper view patch to use relative generated-image URLs for device previews. See `deploy/larapaper/patches/relative-preview-image-urls.md`.

Quick checks:

```bash
curl -I -L http://192.168.1.143:4567/dashboard
curl -I http://192.168.1.143:4567/storage/images/generated/<current_screen_image>.png
curl -I http://192.168.1.143:4567/build/assets/app-D97lLgKN.css
ssh khpi5 "cd /home/dave/larapaper && docker compose exec -T app printenv | grep -E '^(APP_URL|ASSET_URL|APP_TRUSTED_PROXIES)='"
```

The live deployment intentionally keeps `APP_URL=https://trmnl.magnusfamily.co.uk` for canonical external links while the Pi still polls the LAN API.

### Display does not update

Check the Pi service first:

```bash
ssh trmnl-pi "journalctl -u trmnl-display.service --no-pager -n 120"
```

Expected success lines include:

- `image specs: 800 x 480, 4-bpp`
- for indexed sidecar proofs: `image specs: 800 x 480, 8-bpp` followed by `Preparing image for EPD as 4-bpp`
- `Writing data to EPD...`
- `Refresh complete`
- `Cycle complete, sleeping 600s...`

### Direct colour sidecar proof

Use this only while iterating on colour output. It bypasses LaraPaper for one physical refresh and stops the polling service so the test image is not immediately overwritten.

```bash
python scripts/render_colour_dashboard.py
scp scripts/tmp/sidecar_colour_dashboard_next.png trmnl-pi:/tmp/sidecar_colour_dashboard_next.png
ssh trmnl-pi "sudo systemctl stop trmnl-display.service && /usr/local/bin/show_img.bin file=/tmp/sidecar_colour_dashboard_next.png invert=false mode=full"
```

To render the same payload contract used by the LaraPaper plugin:

```bash
python scripts/render_colour_dashboard.py --payload plugins/trmnl-ha-dashboard/payload.example.json
```

To validate the default render, supported card types, and fixed slot behavior:

```bash
python scripts/validate_colour_dashboard.py --write-images
```

The validator writes optional proof images under `scripts/tmp/colour_dashboard_validation/` and fails if any generated panel PNG is not `800x480`, paletted mode `P`, constrained to the seven panel colours, and using all seven colours.

On `khpi5`, set `TRMNL_SIDECAR_PAYLOAD_PATH=/home/dave/trmnl-ha-dashboard-payload.json` in `/home/dave/.env.trmnl-ha-dashboard` to have the HA companion script write the live `merge_variables` payload for sidecar rendering.

Expected success lines:

- `image specs: 800 x 480, 8-bpp`
- `Preparing image for EPD as 4-bpp`
- `Refresh complete`

Restart the normal polling client when ready to return to LaraPaper/BYOS polling:

```bash
ssh trmnl-pi "sudo systemctl start trmnl-display.service"
```

### LaraPaper sidecar handoff

The HA dashboard sidecar is served through LaraPaper, not a separate Pi endpoint.

Routine playlist-safe update:

```bash
ssh khpi5 "/home/dave/bin/trmnl-refresh-ha-sidecar"
```

That command updates the `Home Assistant` plugin image in LaraPaper and leaves the active playlist untouched. If the plugin is part of any LaraPaper playlist, normal playlist rotation can serve the refreshed image.

Media-triggered refreshes can call the mode bridge endpoint instead:

```bash
ssh khpi5 "curl -fsS -X POST http://127.0.0.1:8787/ha-dashboard/refresh -H 'Authorization: Bearer $TRMNL_MODE_BRIDGE_TOKEN' -H 'Content-Type: application/json' -d '{\"reason\":\"manual\",\"force\":true}'"
```

The endpoint runs the same wrapper and rate-limits successful refreshes with a default 120-second cooldown unless `force` is set.

### Home Assistant managed slot controls

The HA dashboard package can expose local helper entities for choosing sidecar slot intent without editing Python or the LaraPaper recipe:

- `input_select.trmnl_ha_dashboard_*_card_type`
- `input_text.trmnl_ha_dashboard_*_entity`
- `input_text.trmnl_ha_dashboard_*_label`
- `input_text.trmnl_ha_dashboard_generic_*`
- `input_button.trmnl_ha_dashboard_refresh`

Changes to these helper entities request the same playlist-safe refresh endpoint with `force: true`, because they are deliberate configuration edits. Routine sensor/media refreshes still use the endpoint cooldown to avoid excessive e-paper updates.

Enable helper-driven payload settings on `khpi5` with:

```bash
TRMNL_HA_MANAGED_CONFIG=1
```

in `/home/dave/.env.trmnl-ha-dashboard`, then run `/home/dave/bin/trmnl-refresh-ha-sidecar`. The optional Lovelace source is `config/lovelace/trmnl_ha_dashboard_control.yaml`; it can be copied into a HA dashboard view to expose the helpers.

Manual HA-only mode activation:

```bash
ssh khpi5 "/home/dave/bin/trmnl-set-display-mode ha_dashboard"
ssh khpi5 "curl -fsS http://127.0.0.1:4567/storage/images/generated/sidecar_colour_dashboard_next.png -o /tmp/sidecar_colour_dashboard_next.png"
ssh trmnl-pi "sudo systemctl restart trmnl-display.service"
ssh trmnl-pi "journalctl -u trmnl-display.service --no-pager -n 80"
```

Expected Pi signs for the sidecar handoff:

- `image specs: 800 x 480, 8-bpp`
- `Preparing image for EPD as 4-bpp`
- `Refresh complete`

Rollback from manual HA-only mode is mode-based:

```bash
ssh khpi5 "/home/dave/bin/trmnl-set-display-mode calendar"
ssh trmnl-pi "sudo systemctl restart trmnl-display.service"
```

### LaraPaper is generating black and white images

Check the live device model:

```bash
ssh khpi5 "docker exec -i larapaper-app-1 php /tmp/check_device_model.php"
```

If using an ad hoc query, verify:

- model `inky_impression_7_3`
- width `800`
- height `480`
- bit depth greater than `1`
- palette is the ACeP colour palette, not black/white

### Home Assistant mode changes are ignored

Check:

```bash
ssh khpi5 "systemctl status trmnl-mode-bridge.service --no-pager"
ssh home-assistant "grep -n 'trmnl_set_display_mode' -A12 /config/packages/trmnl_display_orchestration.yaml"
```

Then verify the bridge token in Home Assistant `secrets.yaml` matches `/home/dave/.env.trmnl-mode-bridge` on `khpi5`.

### Sonos screen stale

Check the cron wrapper and script logs:

```bash
ssh khpi5 "journalctl --since '30 minutes ago' -t trmnl-sonos-local --no-pager"
ssh khpi5 "cat /home/dave/run_trmnl_sonos.sh"
```

### Calendar screen stale

Check the calendar job:

```bash
ssh khpi5 "journalctl --since '30 minutes ago' -t trmnl-calendar --no-pager"
```

## Service Reloads

After changing the mode bridge:

```bash
ssh khpi5 "sudo systemctl daemon-reload && sudo systemctl restart trmnl-mode-bridge.service"
```

After changing the Pi display shell:

```bash
ssh trmnl-pi "sudo systemctl daemon-reload && sudo systemctl restart trmnl-display.service"
```

After changing `deploy/trmnl-pi/environment`, copy it to `/etc/environment` and open a fresh SSH session before validating locale-sensitive commands:

```bash
scp deploy/trmnl-pi/environment trmnl-pi:/tmp/trmnl-pi-environment
ssh trmnl-pi "sudo mv /tmp/trmnl-pi-environment /etc/environment"
ssh trmnl-pi "locale && apt list --upgradable >/tmp/apt-check.out 2>/tmp/apt-check.err; cat /tmp/apt-check.err"
```

After changing LaraPaper compose files:

```bash
ssh khpi5 "cd /home/dave/larapaper && docker compose up -d"
```

After changing Home Assistant packages:

```bash
ssh home-assistant "ha core check"
ssh home-assistant "ha core restart"
```

## Verification Gates

Use the gates from `docs/LIVE_DEPLOYMENT_WORKFLOW.md`:

- Gate A: data fetch or payload generation succeeds
- Gate B: LaraPaper render succeeds and a new image is generated
- Gate C: `trmnl-pi` pulls the new image
- Gate D: the physical panel updates correctly
- Gate E: unrelated recipes still render cleanly
