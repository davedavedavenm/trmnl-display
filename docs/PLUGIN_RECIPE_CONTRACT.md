# Plugin And Recipe Contract

Date: 2026-05-19
Last aligned to official TRMNL/LaraPaper/trmnlp format: 2026-07-22

This repo must preserve TRMNL/LaraPaper plugin and recipe portability.

The colour sidecar path is allowed because the live Inky/Spectra panel needs better indexed colour output than LaraPaper currently produces. It does not remove the requirement to package screens as normal shareable plugins or recipes wherever possible.

## Mandatory Rule

Every user-facing screen must have a shareable plugin/recipe contract.

CRITICAL: Every single plugin/recipe MUST be fully configurable and editable via the TRMNL/LaraPaper Web UI. Sidecar renderers and sync scripts must read settings (like themes, layouts, layout variants, preferences, entity mappings, credentials) from the plugin's payload or database configurations, NOT from hardcoded values or private `.env` files. This ensures that any plugin or recipe is immediately shareable with the community.

That contract must include:

- `settings.yml` with user-editable fields (official schema)
- `README.md` with install and configuration instructions
- `full.liquid` or equivalent TRMNL-compatible markup **when the plugin renders through Liquid** (see the sidecar-only exemption in "Required Files Per Plugin")
- documented `merge_variables` for webhook plugins
- no user-specific secrets or hardcoded credentials

The following are **optional repo conventions**, not official TRMNL/LaraPaper/trmnlp artifacts. Create them only when they earn their place:

- a sample payload (`payload.example.json`) — useful as a human example and as fallback input for some sidecar renderers; when present it must use the `merge_variables` wrapper. The official home for local preview data is `.trmnlp.yml`.
- a field/schema document (`fields.schema.json`) — only when a sidecar renderer or companion script actually consumes it. Keep it aligned with `settings.yml` when present.

Sidecar renderers must consume the same conceptual configuration exposed by the plugin. They may add renderer-only fields, but those fields must be documented and given safe defaults.

## Why This Matters

The target outcome is not just a working private dashboard. The target is a reusable TRMNL/LaraPaper plugin or recipe that another user can install, configure, and adapt without editing source code.

If a screen needs special rendering for colour fidelity, that renderer is an implementation detail. The user-facing interface should still look like a normal plugin:

- configure entities
- configure labels
- configure layout/profile
- provide webhook payloads or polling data
- install into LaraPaper/TRMNL using the documented plugin files

## Required Files Per Plugin

For each plugin directory under `plugins/`, the official minimum is:

```text
plugins/<plugin-id>/
  README.md
  settings.yml
  full.liquid            # only if the plugin renders through Liquid
  [half_vertical.liquid | half_horizontal.liquid | quadrant.liquid]   # as needed
```

`full.liquid` may be a compatibility renderer if the final colour path uses a sidecar. A webhook plugin whose image is supplied by the repo's indexed-colour sidecar through LaraPaper's **generated-image / image-webhook handoff** is **exempt** from shipping a Liquid template; its README must state that rendering path explicitly per the Exception Process below. That handoff is an official LaraPaper screen-generation mechanism (the LaraPaper README lists "Screenshot, Image Webhook, API" alongside recipe/Liquid rendering), so a liquid-less sidecar plugin is not incomplete.

Optional repo conventions (`payload.example.json`, `fields.schema.json`) may also live in the plugin directory but are not part of the official contract — see the "Mandatory Rule" list above.

## Official Format Reference (verified 2026-07-22)

- **Importable artifact is flat.** The official TRMNL "Importing and exporting private plugins" guide defines the plugin ZIP as a flat list: `settings.yml` (required) plus the four Liquid view files. No `payload.example.json`, no `fields.schema.json`, no `src/`. This repo stores that flat shape as source of truth because the sidecar renderers and `scripts/validate_trmnl_ha_plugin_contract.py` read those paths directly.
- **`src/` is dev-only.** The official `trmnlp` tool uses `src/settings.yml` + `src/*.liquid` as its dev layout and zips it flat on `push`/`build`. Do not migrate the repo into `src/` without updating the renderer and validator path constants that currently target the flat layout.
- **`settings.yml` schema.** Official keys: `name`, `strategy` (`polling`/`webhook`/`static`), `refresh_interval`, `no_screen_padding`, `dark_mode`, `custom_fields` (`keyname`/`name`/`field_type`/`options`, plus `default`/`optional`/`description`), and an `id` (required by `trmnlp push`).
- **Webhook payloads.** Use the `merge_variables` wrapper; incremental updates may use `merge_strategy: deep_merge` or `stream` with `stream_limit` (docs.trmnl.com private-plugins/webhooks).
- **Local preview data / secrets.** Official home is `.trmnlp.yml` (`variables:`, `custom_fields:`, `{{ env.* }}` interpolation). Prefer it over committing live values.
- **CI.** Official best practice is `trmnlp lint`, run from a repo-root workflow that loops `plugins/*/` (the official per-plugin `.github/workflows/trmnl.yml` assumes one-plugin-per-repo and does not work in a monorepo). The official `trmnlp push` job targets trmnl.com cloud and is omitted here because this stack distributes via LaraPaper BYOS, not the TRMNL marketplace.
- **Colour exception.** The official TRMNL Liquid/CSS design system targets the 800x480 2-bit grayscale panel (docs.trmnl.com private-plugins/templates). The live device is a 6/7-colour ACeP Spectra panel; the repo's indexed-colour sidecar supplies panel-correct colour via LaraPaper's generated-image handoff. That is a legitimate BYOS extension, documented here, not a regression to monochrome.

## Settings Requirements

`settings.yml` must expose configuration rather than hardcoding local assumptions. At minimum, Home Assistant-style plugins must expose:

- dashboard title
- Home Assistant URL
- entity IDs
- room/device labels where user-specific naming matters
- fixed card slot type/entity/label/detail settings when a renderer supports configurable card intent
- renderer or colour profile when multiple display classes are supported
- refresh interval

Secrets must use password fields or live secret stores and must never be committed with live values.

## Payload Requirements

Webhook plugins must use TRMNL's `merge_variables` pattern.

Each plugin must document:

- top-level merge variables
- nested objects and arrays
- required fields
- optional fields
- fallback behavior when a field is missing

Payload examples must stay small enough to reflect TRMNL webhook limits. Larger payloads should use documented summarization, `deep_merge`, `stream`, or sidecar-hosted data as appropriate.

As of the current TRMNL webhook documentation, the same custom plugin webhook endpoint can also be read with `GET` to inspect existing `merge_variables`. Incremental payload updates can use `merge_strategy: "deep_merge"` for nested object updates or `merge_strategy: "stream"` with `stream_limit` for bounded top-level arrays. LaraPaper `0.35.0` adds support for these webhook merge strategies; the live stack was updated to `0.35.0` on 2026-05-19, but any production use should still be tested against the local LaraPaper endpoint before changing existing payload flows.

## Sidecar Requirements

A sidecar renderer is acceptable only when it improves a documented limitation such as colour reproduction.

Sidecar renderers must:

- keep the Pi as a thin display client
- keep mode decisions out of the Pi
- preserve a plugin-level configuration contract
- generate from repo-owned source
- output a panel-compatible image
- provide a test command and expected logs
- document any divergence from official TRMNL/LaraPaper behavior

For the HA dashboard, the accepted sidecar details live in `docs/COLOUR_SIDECAR_PATH.md`.

The accepted colour-dashboard visual reference is `scripts/tmp/sidecar_colour_dashboard_proof_2026-05-01.png`. Sidecar implementations for this plugin should preserve that seven-colour, icon-led style unless a later accepted reference supersedes it in the same document. Normal renderer runs must write separate iteration files and must not overwrite the tracked proof reference.

## Color Screen Usage

Whenever possible, layouts, rendering templates, and sidecars must make full, deliberate use of the physical 7-color Spectra screen. Do not fallback to monochrome or grayscale designs when color-coded accents, status badges, or colored iconography can be used to improve readability and aesthetics. The palette must consist of the full ACeP spectrum:
- Black
- White
- Red
- Green
- Blue
- Yellow
- Orange

## Exception Process

If a screen cannot be packaged as a normal plugin/recipe, its README must include:

- what official plugin/recipe expectation cannot be met
- why it cannot be met
- what compatibility layer remains
- what would be needed to remove the exception

Absent that explanation, plugin packaging is mandatory.
