# AGENTS.md - TRMNL Display

This repo is the source of truth for the live TRMNL/LaraPaper BYOS display stack. Agents working here must preserve that contract.

## Mission

Maintain a Home Assistant-orchestrated e-paper display system that uses:

- LaraPaper as the local TRMNL BYOS management server on `khpi5`
- a repo-owned indexed colour renderer for colour-critical dashboards
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

1. Colour-critical dashboards use the repo-owned indexed colour renderer path. LaraPaper remains the BYOS management layer unless explicitly replaced.
2. The Pi is a thin client. It polls `/api/display`, downloads the returned image, and writes it to the panel.
3. Home Assistant orchestrates. It chooses modes and pushes payloads, but should not contain display layout logic.
4. GitHub is source of truth. Any live edit must be copied back, reviewed, committed, and pushed.
5. Secrets stay out of git. Use examples and placeholders only.
6. ACeP colour output is required. Treat accidental grayscale, 1-bit output, or regression back to LaraPaper's limited colour buckets as a bug.
7. The physical screen is a Pimoroni Inky Impression 7.3 / Spectra-class colour panel driven as `EP73_SPECTRA_800x480`, not a standard black-and-white TRMNL panel.
8. Plugin/recipe portability is mandatory. Sidecar rendering must not turn a shareable plugin into a private hardcoded screen unless a documented exception explains why.

## Managed Surfaces

Use `docs/SOURCE_OF_TRUTH.md` as the canonical mapping. Common paths:

- `plugins/` - shareable LaraPaper/TRMNL recipes
- `scripts/` - companion scripts and Pi display shell
- `config/packages/` - Home Assistant packages
- `config/trmnl/` - Pi display config examples
- `deploy/` - Docker Compose, systemd units, cron entries, host environment examples
- `docs/` - operating model, deployment workflow, and plans
- `scripts/render_colour_dashboard.py` - first proven sidecar colour renderer

## Correct Change Flow

For normal work:

1. Start in this repo.
2. Edit the repo copy.
3. Run local checks.
4. Deploy the changed files to the relevant host.
5. Reload/restart only the affected service.
6. Verify the generated image and Pi display logs. For colour sidecar work, visually inspect the generated PNG and confirm direct hardware output before wiring into BYOS polling.
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
- or, for indexed sidecar PNG proofs, `image specs: 800 x 480, 8-bpp` followed by `Preparing image for EPD as 4-bpp`
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

For colour-critical screens, the image pointed to by the BYOS response may come from a sidecar renderer or LaraPaper handoff, as long as the Pi remains a thin BYOS client and the generated image is reproducible from this repo.

## Hardware Contract

The live hardware identity is documented in `docs/HARDWARE.md`. Key facts agents must preserve:

- Pi host: `trmnl-pi` / `192.168.1.74`
- Board: Raspberry Pi Zero 2 W Rev 1.0
- Display config: `adapter=pimoroni`, `panel_1bit=EP73_SPECTRA_800x480`
- LaraPaper model: `inky_impression_7_3`, `800x480`, palette ID `10`, bit depth `3`
- Expected Pi logs: `800 x 480, 4-bpp`, then `Refresh complete`
- Sidecar proof logs: `800 x 480, 8-bpp`, `Preparing image for EPD as 4-bpp`, then `Refresh complete`

Do not "fix" this stack toward the common monochrome TRMNL assumptions. The live device is colour-capable and must remain treated that way.

## Colour Sidecar Contract

The accepted path forward for the Home Assistant dashboard is documented in `docs/COLOUR_SIDECAR_PATH.md`.

Key rules:

- render exactly `800x480`
- output an indexed/paletted PNG for the panel
- use a deliberate seven-colour palette instead of incidental CSS quantization
- keep text and icon outlines black for legibility
- test direct hardware refreshes with `show_img.bin` before routing through BYOS
- do not move state orchestration or mode decisions into the Pi

## Plugin Packaging Contract

The mandatory plugin/recipe portability rules are documented in `docs/PLUGIN_RECIPE_CONTRACT.md`.

Every user-facing screen must remain installable/configurable like a normal TRMNL/LaraPaper plugin or recipe unless a README section documents why that is technically impossible. The colour sidecar is an implementation detail for better panel output; it must not be the only place where user configuration lives.

Every user-facing screen should include these files:

- `settings.yml`
- `README.md`
- `full.liquid` or a documented equivalent
- `payload.example.json`
- `fields.schema.json`

`settings.yml` must expose user-editable fields rather than hardcoding this house. For Home Assistant dashboards, expected fields include:

- dashboard title and instance label
- layout variant
- colour profile or renderer profile
- Home Assistant URL
- Home Assistant token as a password field only
- weather, person, media player, door/lock, washer, blind/cover, and thermostat/temperature entity IDs
- refresh interval when the platform supports it

`payload.example.json` must use TRMNL's `merge_variables` wrapper and show the shape consumed by both Liquid and sidecar renderers. Document required and optional merge variables in the plugin README.

`fields.schema.json` is the sidecar/automation contract. It must stay aligned with `settings.yml`; if a field is added, renamed, or removed in one, update the other in the same change.

When adding a sidecar-only capability, update the plugin fields, payload example, schema, and README at the same time. The sidecar must consume the plugin contract or a direct derivative of it. Do not hardcode local entity IDs, labels, URLs, room names, or private assumptions into reusable plugin logic.

If an official TRMNL/LaraPaper guideline cannot be followed, add an explicit exception section to that plugin README with:

- the guideline or expectation that cannot be met
- why it cannot be met
- what compatibility layer remains
- what would be needed to remove the exception

## Documentation Expectations

Any non-trivial change should update the relevant docs:

- architecture, hardware, or workflow: `README.md`, `docs/HARDWARE.md`, `docs/SOURCE_OF_TRUTH.md`, `docs/ROBUST_BYOS_FLOW.md`, `docs/COLOUR_SIDECAR_PATH.md`, `docs/PLUGIN_RECIPE_CONTRACT.md`
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
