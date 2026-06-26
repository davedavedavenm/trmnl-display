# Source Of Truth

GitHub `main` is the desired state for this TRMNL/LaraPaper deployment.

Live hosts are allowed to run the system, but they are not allowed to become the long-term source of undocumented changes. Any change made directly on `khpi5`, `trmnl-pi`, or Home Assistant must be reconciled into this repository.

## Managed Surfaces

| Live surface | Repo path | Related docs / units |
|---|---|---|
| `/home/dave/larapaper/docker-compose.yml` | `deploy/larapaper/docker-compose.yml` | `docs/DEPLOYMENT.md` |
| `/home/dave/larapaper/nginx/*` | `deploy/larapaper/nginx/` | `docs/DEPLOYMENT.md` |
| `/home/dave/bin/trmnl-mode-bridge.py` | `scripts/trmnl_mode_bridge.py` | `docs/HA_DISPLAY_ORCHESTRATION_PLAN.md`; systemd: `deploy/systemd/trmnl-mode-bridge.service` |
| `/home/dave/bin/trmnl-set-display-mode` | `scripts/trmnl_set_display_mode.sh` | `docs/TRMNL_ORCHESTRATION_AUDIT_2026-06-26.md` (SSH restart line); `docs/HA_DISPLAY_ORCHESTRATION_PLAN.md` |
| `/home/dave/bin/trmnl-refresh-ha-sidecar` | `scripts/trmnl_refresh_ha_sidecar.sh` | `docs/HA_COLOUR_DASHBOARD_PLAN.md`, `docs/COLOUR_SIDECAR_PATH.md` |
| `/home/dave/bin/trmnl-update-ha-sidecar-image` | `scripts/trmnl_update_ha_sidecar_image.sh` | `docs/HA_COLOUR_DASHBOARD_PLAN.md`, `docs/COLOUR_SIDECAR_PATH.md` |
| `/home/dave/trmnl-calendar/main.py` | `scripts/trmnl_calendar_multi.py` | `docs/OPERATIONS.md` (calendar mode) |
| `/home/dave/trmnl_ha_dashboard.py` | `scripts/trmnl_ha_dashboard.py` | `plugins/trmnl-ha-dashboard/`; `docs/HA_COLOUR_DASHBOARD_PLAN.md` |
| colour dashboard sidecar renderer | `scripts/render_colour_dashboard.py` | `docs/COLOUR_SIDECAR_PATH.md`, `docs/BYOS_COLOUR_AUDIT.md` |
| manual LaraPaper mode activation | `scripts/trmnl_set_display_mode.sh` | `docs/TRMNL_ORCHESTRATION_AUDIT_2026-06-26.md`, `docs/HA_DISPLAY_ORCHESTRATION_PLAN.md` |
| playlist-safe LaraPaper HA sidecar plugin-image update | `scripts/trmnl_update_ha_sidecar_image.sh` | `docs/COLOUR_SIDECAR_PATH.md` |
| accepted colour dashboard proof reference | `scripts/tmp/sidecar_colour_dashboard_proof_2026-05-01.png` | `docs/COLOUR_SIDECAR_PATH.md` |
| accepted colour dashboard source reference | `scripts/tmp/sidecar_colour_dashboard_source_proof_2026-05-01.png` | `docs/COLOUR_SIDECAR_PATH.md` |
| `/home/dave/bin/trmnl-refresh-bus-sidecar` | `scripts/trmnl_refresh_bus_sidecar.sh` | `docs/OPERATIONS.md` (bus mode, 600 s refresh) |
| `/home/dave/bin/trmnl-update-bus-sidecar-image` | `scripts/trmnl_update_bus_sidecar_image.sh` | `docs/OPERATIONS.md` (bus mode) |
| bus colour sidecar renderer | `scripts/render_bus_departures.py` | `plugins/trmnl-bus-departures/`; `docs/HA_DISPLAY_ORCHESTRATION_PLAN.md` (bus window) |
| bus departure plugin contract | `plugins/trmnl-bus-departures/` | `docs/PLUGIN_RECIPE_CONTRACT.md` |
| `/home/dave/.env.trmnl-ha-dashboard` shape | `deploy/khpi5/trmnl-ha-dashboard.env.example` | `docs/HA_COLOUR_DASHBOARD_PLAN.md` |
| optional HA dashboard helper view | `config/lovelace/trmnl_ha_dashboard_control.yaml` | `config/packages/trmnl_ha_dashboard.yaml` |
| generated sidecar iteration image on `trmnl-pi` | generated from `scripts/render_colour_dashboard.py`; do not hand-edit | `docs/COLOUR_SIDECAR_PATH.md` |
| `/home/dave/trmnl-sonos-local.py` | `scripts/trmnl_sonos_local.py` | `docs/OPERATIONS.md` (sonos mode, 60 s refresh) |
| `/home/dave/run_trmnl_sonos.sh` | `scripts/run_trmnl_sonos.sh` | `deploy/khpi5/trmnl-crontab.txt` |
| `/home/dave/bin/trmnl-display-shell.sh` on `trmnl-pi` | `scripts/trmnl-display-shell.sh` | `docs/OPERATIONS.md`; systemd: `deploy/systemd/trmnl-display.service` |
| `/home/dave/.config/trmnl/show_img.json` on `trmnl-pi` | `config/trmnl/show_img.json` | `docs/HARDWARE.md` (panel config) |
| `/etc/environment` on `trmnl-pi` | `deploy/trmnl-pi/environment` | `docs/DEPLOYMENT.md` |
| `/etc/systemd/system/trmnl-mode-bridge.service` | `deploy/systemd/trmnl-mode-bridge.service` | `docs/HA_DISPLAY_ORCHESTRATION_PLAN.md` |
| `/etc/systemd/system/trmnl-display.service` | `deploy/systemd/trmnl-display.service` | `docs/OPERATIONS.md`; restart behaviour: `docs/TRMNL_ORCHESTRATION_AUDIT_2026-06-26.md` |
| `/etc/systemd/system/trmnl-display-morning-start.{timer,service}` | `deploy/trmnl-display-morning-start.{timer,service}` | `docs/OPERATIONS.md`; redundancy analysis: `docs/TRMNL_ORCHESTRATION_AUDIT_2026-06-26.md` |
| `/etc/systemd/system/trmnl-display-night-stop.{timer,service}` | `deploy/trmnl-display-night-stop.{timer,service}` | `docs/OPERATIONS.md` |
| `/config/packages/trmnl_*.yaml` | `config/packages/` | `docs/HA_DISPLAY_ORCHESTRATION_PLAN.md` (resolver + mode apply); `docs/HA_COLOUR_DASHBOARD_PLAN.md` (HA dashboard sidecar); per-package READMEs in each package |
| TRMNL-specific `khpi5` cron entries | `deploy/khpi5/trmnl-crontab.txt` | `docs/OPERATIONS.md` |
| Live hardware identity and scan results | `docs/HARDWARE.md` | `docs/SOURCE_OF_TRUTH.md` (this file) |
| `input_datetime.trmnl_jen_morning_{start,end}` + `input_boolean.trmnl_jen_morning_enabled` + `input_select.trmnl_display_mode` + mode toggles (HA helpers, not in repo) | (live on HA only) | `config/packages/trmnl_display_orchestration.yaml` (consumer); `config/packages/trmnl_jen_morning.yaml` (jen_morning); `docs/TRMNL_ORCHESTRATION_AUDIT_2026-06-26.md` (current live values) |

## Change Workflow

1. Start with the repo.
2. Make the change locally.
3. Validate syntax and obvious configuration errors.
4. Deploy the relevant files to the live host.
5. Restart or reload the relevant service.
6. Verify the live output.
7. Commit and push the repo change.

For urgent live fixes, reverse steps 1 and 2 only temporarily:

1. Patch the live host.
2. Verify the fix.
3. Immediately copy the changed live file back to the repo.
4. Commit and push.

## Drift Check Commands

Use these to compare live files against the repo.

```bash
scp khpi5:/home/dave/bin/trmnl-mode-bridge.py scripts/trmnl_mode_bridge.py
scp khpi5:/home/dave/bin/trmnl-set-display-mode scripts/trmnl_set_display_mode.sh
scp khpi5:/home/dave/bin/trmnl-refresh-ha-sidecar scripts/trmnl_refresh_ha_sidecar.sh
scp khpi5:/home/dave/bin/trmnl-update-ha-sidecar-image scripts/trmnl_update_ha_sidecar_image.sh
scp khpi5:/home/dave/trmnl-calendar/main.py scripts/trmnl_calendar_multi.py
scp khpi5:/home/dave/trmnl_ha_dashboard.py scripts/trmnl_ha_dashboard.py
scp khpi5:/home/dave/trmnl-sonos-local.py scripts/trmnl_sonos_local.py
scp trmnl-pi:/home/dave/bin/trmnl-display-shell.sh scripts/trmnl-display-shell.sh
scp home-assistant:/config/packages/trmnl_display_orchestration.yaml config/packages/trmnl_display_orchestration.yaml
```

After copying, review with:

```bash
git diff
git diff --check
```

## Secrets

Never commit live secrets.

Use placeholders in repo files and keep live secrets in:

- `/home/dave/.env.trmnl-mode-bridge`
- `/home/dave/.env.sonos-trmnl`
- `/home/dave/larapaper/.env`
- `/home/dave/.config/trmnl/config.json`
- Home Assistant `secrets.yaml`

## Commit Policy

Each operational change should say what changed and where it was deployed. Example:

```text
fix: support ha_dashboard display mode
```

Large live-sync commits are acceptable after an audit, but normal changes should be small and traceable.

## Hardware Identity

The live display hardware is part of the source-of-truth contract. `docs/HARDWARE.md` records the latest scan and should be updated when the Pi, panel, driver, LaraPaper model, or display config changes.

Current hardware identity:

- Raspberry Pi Zero 2 W Rev 1.0 at `trmnl-pi` / `192.168.1.74`
- Pimoroni Inky Impression 7.3 / Spectra-class colour panel
- Pi `show_img` panel config: `EP73_SPECTRA_800x480`
- LaraPaper model: `inky_impression_7_3`, `800x480`, palette ID `10`
- Colour dashboard path: repo-owned indexed seven-colour sidecar renderer, documented in `docs/COLOUR_SIDECAR_PATH.md`
