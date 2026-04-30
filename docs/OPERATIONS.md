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
