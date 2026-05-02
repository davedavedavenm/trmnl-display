# Source Of Truth

GitHub `main` is the desired state for this TRMNL/LaraPaper deployment.

Live hosts are allowed to run the system, but they are not allowed to become the long-term source of undocumented changes. Any change made directly on `khpi5`, `trmnl-pi`, or Home Assistant must be reconciled into this repository.

## Managed Surfaces

| Live surface | Repo path |
|---|---|
| `/home/dave/larapaper/docker-compose.yml` | `deploy/larapaper/docker-compose.yml` |
| `/home/dave/larapaper/nginx/*` | `deploy/larapaper/nginx/` |
| `/home/dave/bin/trmnl-mode-bridge.py` | `scripts/trmnl_mode_bridge.py` |
| `/home/dave/bin/trmnl-set-display-mode` | `scripts/trmnl_set_display_mode.sh` |
| `/home/dave/bin/trmnl-refresh-ha-sidecar` | `scripts/trmnl_refresh_ha_sidecar.sh` |
| `/home/dave/bin/trmnl-update-ha-sidecar-image` | `scripts/trmnl_update_ha_sidecar_image.sh` |
| `/home/dave/trmnl-calendar/main.py` | `scripts/trmnl_calendar_multi.py` |
| `/home/dave/trmnl_ha_dashboard.py` | `scripts/trmnl_ha_dashboard.py` |
| colour dashboard sidecar renderer | `scripts/render_colour_dashboard.py` |
| manual LaraPaper mode activation | `scripts/trmnl_set_display_mode.sh` |
| playlist-safe LaraPaper HA sidecar plugin-image update | `scripts/trmnl_update_ha_sidecar_image.sh` |
| accepted colour dashboard proof reference | `scripts/tmp/sidecar_colour_dashboard_proof_2026-05-01.png` |
| accepted colour dashboard source reference | `scripts/tmp/sidecar_colour_dashboard_source_proof_2026-05-01.png` |
| `/home/dave/.env.trmnl-ha-dashboard` shape | `deploy/khpi5/trmnl-ha-dashboard.env.example` |
| generated sidecar iteration image on `trmnl-pi` | generated from `scripts/render_colour_dashboard.py`; do not hand-edit |
| `/home/dave/trmnl-sonos-local.py` | `scripts/trmnl_sonos_local.py` |
| `/home/dave/run_trmnl_sonos.sh` | `scripts/run_trmnl_sonos.sh` |
| `/home/dave/bin/trmnl-display-shell.sh` on `trmnl-pi` | `scripts/trmnl-display-shell.sh` |
| `/home/dave/.config/trmnl/show_img.json` on `trmnl-pi` | `config/trmnl/show_img.json` |
| `/etc/environment` on `trmnl-pi` | `deploy/trmnl-pi/environment` |
| `/etc/systemd/system/trmnl-mode-bridge.service` | `deploy/systemd/trmnl-mode-bridge.service` |
| `/etc/systemd/system/trmnl-display.service` | `deploy/systemd/trmnl-display.service` |
| `/config/packages/trmnl_*.yaml` | `config/packages/` |
| TRMNL-specific `khpi5` cron entries | `deploy/khpi5/trmnl-crontab.txt` |
| Live hardware identity and scan results | `docs/HARDWARE.md` |

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
