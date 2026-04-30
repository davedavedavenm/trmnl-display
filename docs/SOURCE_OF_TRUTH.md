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
| `/home/dave/trmnl-calendar/main.py` | `scripts/trmnl_calendar_multi.py` |
| `/home/dave/trmnl_ha_dashboard.py` | `scripts/trmnl_ha_dashboard.py` |
| `/home/dave/trmnl-sonos-local.py` | `scripts/trmnl_sonos_local.py` |
| `/home/dave/run_trmnl_sonos.sh` | `scripts/run_trmnl_sonos.sh` |
| `/home/dave/bin/trmnl-display-shell.sh` on `trmnl-pi` | `scripts/trmnl-display-shell.sh` |
| `/home/dave/.config/trmnl/show_img.json` on `trmnl-pi` | `config/trmnl/show_img.json` |
| `/etc/systemd/system/trmnl-mode-bridge.service` | `deploy/systemd/trmnl-mode-bridge.service` |
| `/etc/systemd/system/trmnl-display.service` | `deploy/systemd/trmnl-display.service` |
| `/config/packages/trmnl_*.yaml` | `config/packages/` |
| TRMNL-specific `khpi5` cron entries | `deploy/khpi5/trmnl-crontab.txt` |

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
