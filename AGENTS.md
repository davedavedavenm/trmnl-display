# AGENTS.md - TRMNL Display

This repo is the source of truth for the live TRMNL/LaraPaper BYOS display stack. Agents working here must preserve that contract.

## Mission

Maintain a Home Assistant-orchestrated e-paper display system that uses:

- LaraPaper as the local TRMNL BYOS management server on `khpi5`
- a repo-owned indexed colour renderer for colour-critical dashboards
- a Pi Zero as a thin TRMNL display client on `trmnl-pi`
- Home Assistant as the orchestration layer (mode selection, state pushing, payload generation)
- official TRMNL and LaraPaper documentation as the reference for plugin contracts, BYOS API, and playlist management
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
6. ACeP colour output is required. Treat accidental grayscale, 1-bit output, or regression back to LaraPaper's limited colour buckets as a bug. Whenever possible, design layouts to make full use of the 6-color Spectra screen (Black, White, Red, Green, Blue, Yellow) and dithered Orange (using Red and Yellow pixels) for rich status indications, color-coded categories, and vibrant iconography.
7. The physical screen is a Pimoroni Inky Impression 7.3 / Spectra-class colour panel driven as `EP73_SPECTRA_800x480`, not a standard black-and-white TRMNL panel.
8. Plugin/recipe portability is mandatory. Sidecar rendering must not turn a shareable plugin into a private hardcoded screen unless a documented exception explains why.
9. Home Assistant decides *what* to show (mode selection, state pushing). LaraPaper playlists decide *when* and *how* to cycle content on the display. Do not bypass LaraPaper's playlist system for routine content rotation. Official TRMNL and LaraPaper documentation (plugin/recipe format, BYOS API contract, settings schema) is authoritative; custom integration patterns must preserve compatibility or document exceptions in the relevant plugin README.

## Managed Surfaces

Use `docs/SOURCE_OF_TRUTH.md` as the canonical mapping. Common paths:

- `plugins/` - shareable LaraPaper/TRMNL recipes
- `scripts/` - companion scripts and Pi display shell
- `config/packages/` - Home Assistant packages
- `config/trmnl/` - Pi display config examples
- `deploy/` - Docker Compose, systemd units, cron entries, host environment examples
- `docs/` - operating model, deployment workflow, and plans
- `config/lovelace/` - optional HA helper views and dashboard card sources
- `plugins/trmnl-ha-dashboard/` - HA colour dashboard plugin contract (settings, schema, payload, README)
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
python -m py_compile scripts/trmnl_calendar_multi.py scripts/trmnl_ha_dashboard.py scripts/trmnl-mode-bridge.py scripts/trmnl_sonos_local.py scripts/render_colour_dashboard.py scripts/nango_calendar_fetch.py scripts/render_calendar_dayview.py scripts/render_jen_coming_home.py scripts/fire_calendar_fetch.py
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

Every user-facing screen must remain installable/configurable like a normal TRMNL/LaraPaper plugin or recipe. The colour sidecar is an implementation detail for better panel output; it must not be the only place where user configuration lives.

CRITICAL: Every single plugin/recipe MUST be fully configurable and editable via the TRMNL/LaraPaper Web UI. Sidecar renderers and sync scripts must read settings (like themes, layouts, layout variants, preferences, entity mappings, credentials) from the plugin's payload or database configurations, NOT from hardcoded values or private `.env` files. This ensures that any plugin or recipe is immediately shareable with the community.

Official format reference (verified 2026-07-22 against current TRMNL/LaraPaper/trmnlp sources):

- The shareable/importable artifact is a **flat** set of files. Per the official TRMNL "Importing and exporting private plugins" guide, a plugin ZIP contains only `settings.yml` (required) plus any of `full.liquid`, `half_horizontal.liquid`, `half_vertical.liquid`, `quadrant.liquid`. There is **no** `payload.example.json`, **no** `fields.schema.json`, and **no** `src/` directory in the official interchange format. (`src/` is only the *dev-time* layout used by the official `trmnlp` tool, which zips it flat on `push`/`build`.)
- This repo stores the **flat interchange shape** as source of truth (templates and `settings.yml` at each plugin root) because the repo's sidecar renderers and `scripts/validate_trmnl_ha_plugin_contract.py` read those paths directly. Do not migrate plugins into `src/` without updating those consumers.
- `settings.yml` must follow the official schema (`name`, `strategy`, `refresh_interval`, `no_screen_padding`, `dark_mode`, optional `custom_fields`, and an `id` — `trmnlp push` requires the `id`). The official `custom_fields` shape (`keyname`/`name`/`field_type`/`options`, plus `default`/`optional`/`description`) is what this repo uses.
- Webhook payloads use the official `merge_variables` wrapper; incremental updates may use `merge_strategy: deep_merge` or `stream` (docs.trmnl.com private-plugins/webhooks).
- Liquid layout names (`full`, `half_vertical`, `half_horizontal`, `quadrant`) are official (docs.trmnl.com private-plugins/templates).
- For local preview data and plugin secrets, the official home is `.trmnlp.yml` (`variables:` / `custom_fields:` / env interpolation) per the `trmnlp` README — prefer that over committing live values anywhere.

Required files per plugin (official-aligned):

- `settings.yml` — required, official schema, with an `id`.
- `README.md` — required, install/config instructions and the documented `merge_variables` (required vs optional fields, fallback behaviour).
- `full.liquid` (and other view templates as needed) — required **only for plugins that render through Liquid**. A webhook plugin whose image is supplied by the repo's indexed-colour sidecar via LaraPaper's generated-image / image-webhook handoff is **exempt** from shipping a Liquid template; its README must state that rendering path explicitly (see the exception process below). This is an official LaraPaper screen-generation mechanism, not a gap.

Optional repo conventions (NOT official TRMNL/LaraPaper/trmnlp artifacts — keep only where they earn their place):

- `payload.example.json` — useful as human-readable example and as the default/fallback input some sidecar renderers read (e.g. `render_colour_dashboard.py`, `render_morning_mashup.py`). When present it **must** use the `merge_variables` wrapper. It is not required by any official tool.
- `fields.schema.json` — a repo-internal sidecar/automation contract document. No official tool reads it. Keep it aligned with `settings.yml` when present (if a field changes in one, update both in the same change), but do not mass-create it for plugins that have no sidecar consuming it.

`settings.yml` must expose user-editable fields rather than hardcoding this house. For Home Assistant dashboards, expected fields include:

- dashboard title and instance label
- layout variant
- colour profile or renderer profile
- Home Assistant URL
- Home Assistant token as a password field only
- weather, person, media player, door/lock, washer, blind/cover, and thermostat/temperature entity IDs
- refresh interval when the platform supports it

Do not hardcode local entity IDs, labels, URLs, room names, or private assumptions into reusable plugin logic or into the optional `payload.example.json` / `fields.schema.json` examples — use generic placeholders there.

Continuous integration: the official best practice is `trmnlp lint` (github.com/usetrmnl/trmnlp). Because this is a monorepo (GitHub only reads workflows from the repo-root `.github/workflows/`), the official per-plugin workflow is adapted into a single root workflow that lints every `plugins/*/` via a flat→`src/` shim. The official workflow's `trmnlp push` job targets trmnl.com cloud and is **omitted** here — this stack distributes through LaraPaper BYOS and this repo, not the TRMNL cloud marketplace.

Colour exception grounding: the official TRMNL Liquid/CSS design system targets the 800x480 2-bit grayscale panel (docs.trmnl.com private-plugins/templates). The live device is a 6/7-colour ACeP Spectra panel, and the repo's indexed-colour sidecar uses LaraPaper's generated-image handoff to supply panel-correct colour output. That is a legitimate BYOS extension; document it per the exception process rather than treating monochrome as the target.

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
