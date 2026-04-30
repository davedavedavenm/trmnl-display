# AGENTS.md - TRMNL Display

This repo is the source of truth for the live TRMNL/LaraPaper BYOS display stack. Agents working here must preserve that contract.

## Mission

Maintain a Home Assistant-orchestrated e-paper display system that uses:

- LaraPaper as the local TRMNL BYOS server and renderer on `khpi5`
- a Pi Zero as a thin TRMNL display client on `trmnl-pi`
- Home Assistant as the orchestration layer
- GitHub `main` as the durable source of truth

## Current Live Hosts

| Role | Host | Notes |
|---|---|---|
| LaraPaper server | `khpi5` / `192.168.1.143` | Docker Compose, mode bridge, companion scripts |
| Display client | `trmnl-pi` / `192.168.1.74` | Polls LaraPaper and runs `show_img.bin` |
| Orchestrator | `home-assistant` / `192.168.1.89` | HA packages, helpers, automations, REST commands |

## Non-Negotiable Architecture Rules

1. LaraPaper renders. Do not move rendering responsibility to Home Assistant or the Pi.
2. The Pi is a thin client. It polls `/api/display`, downloads the returned image, and writes it to the panel.
3. Home Assistant orchestrates. It chooses modes and pushes payloads, but should not contain display layout logic.
4. GitHub is source of truth. Any live edit must be copied back, reviewed, committed, and pushed.
5. Secrets stay out of git. Use examples and placeholders only.
6. ACeP colour output is required. Treat accidental grayscale output as a regression.

## Managed Surfaces

Use `docs/SOURCE_OF_TRUTH.md` as the canonical mapping. Common paths:

- `plugins/` - shareable LaraPaper/TRMNL recipes
- `scripts/` - companion scripts and Pi display shell
- `config/packages/` - Home Assistant packages
- `config/trmnl/` - Pi display config examples
- `deploy/` - Docker Compose, systemd units, cron entries, host environment examples
- `docs/` - operating model, deployment workflow, and plans

## Correct Change Flow

For normal work:

1. Start in this repo.
2. Edit the repo copy.
3. Run local checks.
4. Deploy the changed files to the relevant host.
5. Reload/restart only the affected service.
6. Verify the generated LaraPaper image and Pi display logs.
7. Commit and push to GitHub.

For urgent live fixes:

1. Patch the live host.
2. Verify the fix.
3. Immediately sync the changed live file back into this repo.
4. Commit and push.

Never leave live-only drift undocumented.

## Validation Commands

Python syntax:

```bash
python -m py_compile scripts/trmnl_calendar_multi.py scripts/trmnl_ha_dashboard.py scripts/trmnl_mode_bridge.py scripts/trmnl_sonos_local.py
```

Home Assistant package check:

```bash
ssh home-assistant "ha core check"
```

LaraPaper and mode bridge:

```bash
ssh khpi5 "docker ps --filter name=larapaper-app-1"
ssh khpi5 "/home/dave/bin/trmnl-set-display-mode status"
ssh khpi5 "systemctl status trmnl-mode-bridge.service --no-pager"
```

Pi display:

```bash
ssh trmnl-pi "journalctl -u trmnl-display.service --no-pager -n 80"
```

Expected successful Pi render signs:

- `image specs: 800 x 480, 4-bpp`
- `Writing data to EPD...`
- `Refresh complete`
- `Cycle complete, sleeping 600s...`

## Deployment Caution

- Do not blindly deploy `deploy/larapaper/docker-compose.yml` unless `/home/dave/larapaper/.env` contains `LARAPAPER_APP_KEY`.
- Do not commit `/home/dave/.config/trmnl/config.json`; it contains the device API key.
- Do not commit Home Assistant `secrets.yaml`.
- Do not update unrelated Docker containers on `khpi5` as part of this repo unless the user explicitly asks for broader homelab maintenance.

## BYOS Contract

The display client uses the TRMNL BYOS polling pattern:

- request: `GET /api/display`
- headers: `ID`, `access-token`, battery/RSSI metadata
- response: `image_url`, `filename`, `refresh_rate`, firmware flags, `special_function`

The repo must preserve compatibility with LaraPaper's implementation of that contract.

## Documentation Expectations

Any non-trivial change should update the relevant docs:

- architecture or workflow: `README.md`, `docs/SOURCE_OF_TRUTH.md`, `docs/ROBUST_BYOS_FLOW.md`
- deployment paths or commands: `docs/DEPLOYMENT.md`
- live operations or incident response: `docs/OPERATIONS.md`
- historical/project notes: `docs/TRMNL_PROGRESS_REPORT.md` or `docs/TRMNL_PROJECT_PLAN.md`

## Git Rules

- Stage only intentional files.
- Run `git diff --check` before committing.
- Scan for secrets before committing.
- Push to `origin/main` when the user asks to update GitHub.

Useful secret scan:

```bash
git diff --cached | grep -Ei 'jwt|bearer|app_key|api_key|token|secret|private'
```

Review hits manually; examples and placeholders are allowed, live keys are not.
