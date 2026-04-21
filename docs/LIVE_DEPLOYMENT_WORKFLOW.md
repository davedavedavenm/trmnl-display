# Live Deployment Workflow

This document is the working contract for the current TRMNL/LaraPaper-based stack.

## Current Architecture
- Local repo: source of truth for templates, scripts, docs, and Home Assistant packages
- `khpi5`: live LaraPaper server and companion-script host
- Pi Zero / Inky device: thin display client only
- Home Assistant: orchestration and mode selection layer

Do not treat a local render or local code change as "done" for TRMNL work. The change is only complete once it has been deployed to `khpi5` and verified on the physical panel.

## First Visual Check
For this stack, the LaraPaper web UI preview and the generated PNG file are the first visual proxy for the live screen.

Use them before concluding anything about the physical panel:
- if LaraPaper preview is grayscale, the problem is still in the server render path
- if LaraPaper preview is colour but the panel is grayscale, the problem is in the final device path on `inky-pi`

## Deployment Rule
For any change that affects a TRMNL plugin, LaraPaper webhook flow, companion script, or Home Assistant orchestration path, follow this sequence:

1. Make and test the code change locally.
2. Push or copy the relevant change to `khpi5`.
3. Run the server-side script or refresh path on `khpi5`.
4. Confirm LaraPaper generated a fresh image and inspect the preview/PNG visually.
5. Confirm the Pi client pulled that image.
6. Confirm the physical display matches the intended result.

## Validation Gates
- Gate A: data fetch or payload generation succeeds
- Gate B: LaraPaper render succeeds and a new image is generated
- Gate C: `trmnl-display` pulls the new image successfully
- Gate D: the physical panel updates correctly
- Gate E: unrelated recipes still render cleanly

## Colour Rule
For the current 7.3" panel, the target is full ACeP palette usage, not grayscale fallback.

In practice that means:
- preserve distinct colours where the panel can render them well
- avoid accidentally biasing recipes toward monochrome for convenience
- treat a regression from colour to grayscale as a bug unless it is an intentional user-selectable mode

## Sonos-Specific Rule
The Sonos recipe must preserve a colour-capable path.

If image preprocessing is used, it must be tunable and must not silently collapse the live output into grayscale-like rendering. If there is a tradeoff between legibility and colour richness, expose it as an explicit mode rather than baking it into a single default.

When Sonos appears grayscale:
- check the live Sonos payload first to see whether album art is present
- inspect the live LaraPaper preview/PNG
- verify the `inky_impression_7_3` device model on `khpi5` is still using the 7-colour palette and not a 1-bit black/white model
- only then adjust recipe styling or artwork preprocessing

## Known Root Cause
One confirmed failure mode already occurred in this project:
- LaraPaper on `khpi5` drifted so `inky_impression_7_3` was configured as `colors=2`, `bit_depth=1`, `palette=bw`
- result: all recipes rendered as black/white PNGs even when recipe code expected colour

Treat that configuration drift as a primary diagnostic check whenever colour disappears.

## Documentation Rule
When making decisions about TRMNL recipes, private plugins, palettes, BYOS behavior, or community-supported integrations:
- prefer official TRMNL documentation first
- then use official or well-supported community recipe guidance
- document any deliberate divergence in this repo

## Empirical Override Rule
When vendor documentation, product naming, or nominal hardware taxonomy conflicts with a render path that has already been validated on the live stack:
- prefer the empirically validated live render behavior
- do not change live palette/model assumptions without side-by-side proof that the new path is better on the actual screen
- treat the currently working LaraPaper + `trmnl-display` + `show_img` output as canonical until a replacement is tested and accepted

## Current Server Roles
- LaraPaper host: `khpi5`
- Display client: Pi Zero / Inky hardware
- Home Assistant role: orchestration, helpers, automations, webhook/script triggers

## Definition Of Done
A TRMNL-facing change is done only when:
- the repo is updated
- the live server on `khpi5` is updated
- the generated output is validated
- the physical display is checked
