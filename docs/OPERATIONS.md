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
- `Writing data to EPD...`
- `Refresh complete`
- `Cycle complete, sleeping 600s...`

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
