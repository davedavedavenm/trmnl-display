# Plugin And Recipe Contract

Date: 2026-05-01

This repo must preserve TRMNL/LaraPaper plugin and recipe portability.

The colour sidecar path is allowed because the live Inky/Spectra panel needs better indexed colour output than LaraPaper currently produces. It does not remove the requirement to package screens as normal shareable plugins or recipes wherever possible.

## Mandatory Rule

Every user-facing screen must have a shareable plugin/recipe contract unless a clear technical blocker is documented in the screen's README.

That contract must include:

- `settings.yml` with user-editable fields
- `README.md` with install and configuration instructions
- `full.liquid` or equivalent TRMNL-compatible markup when possible
- documented `merge_variables`
- a sample payload
- a field/schema document for any sidecar renderer or companion script
- no user-specific secrets or hardcoded credentials

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

For each plugin directory under `plugins/`:

```text
plugins/<plugin-id>/
  README.md
  settings.yml
  full.liquid
  payload.example.json
  fields.schema.json
```

`full.liquid` may be a compatibility renderer if the final colour path uses a sidecar. Do not delete the Liquid version unless a replacement recipe export format exists and is documented.

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

Payload examples must stay small enough to reflect TRMNL webhook limits. Larger payloads should use documented summarization, `deep_merge`, stream, or sidecar-hosted data as appropriate.

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

## Exception Process

If a screen cannot be packaged as a normal plugin/recipe, its README must include:

- what official plugin/recipe expectation cannot be met
- why it cannot be met
- what compatibility layer remains
- what would be needed to remove the exception

Absent that explanation, plugin packaging is mandatory.
