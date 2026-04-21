# HA Display Orchestration Plan

This document defines the intended control model for the TRMNL/LaraPaper display stack.

## Goal

Home Assistant should own **screen policy**.
LaraPaper should own **rendering and delivery**.
The Pi display client should remain a **dumb fetch-and-render endpoint**.

That means:
- HA decides which mode should be shown
- HA or local scripts push payloads into the relevant LaraPaper plugin
- LaraPaper activates the relevant playlist/plugin and renders the image
- the Pi only pulls the resulting image from LaraPaper

## Design Principles

- Prefer mostly static or slow-changing pages as the baseline
- Use event-driven screens only as temporary overrides
- Keep the global screen decision in one place
- Avoid multiple feature automations fighting over `input_select.trmnl_display_mode`
- Make policy configurable with helpers rather than hardcoding priorities in several automations

## Baseline Screen Types

### Resting Screens
- `calendar`
- `idle`

These should occupy the display most of the time.

### Context Screens
- `jen_commute`
- `dave_commute`

These appear only when the underlying commute context is active.

### Live Media Screens
- `sonos`

This should appear while playback is relevant, then yield back to the resting screen after a configurable hold period.

### Interrupt Screens
- `alert`

This is the highest-priority override and should be explicitly time-bound.

## Configurable Policy Model

The first implementation pass should expose policy through helpers:

### Master Controls
- `input_boolean.trmnl_display_automation_enabled`
- `input_select.trmnl_display_mode`
- `input_select.trmnl_display_default_mode`
- `input_select.trmnl_display_manual_override`

### Per-Mode Enable Flags
- `input_boolean.trmnl_mode_calendar_enabled`
- `input_boolean.trmnl_mode_sonos_enabled`
- `input_boolean.trmnl_mode_jen_commute_enabled`
- `input_boolean.trmnl_mode_dave_commute_enabled`
- `input_boolean.trmnl_mode_alert_enabled`

### Hold / Timing Controls
- `input_number.trmnl_sonos_hold_minutes`
- `input_datetime.trmnl_sonos_hold_until`

### Initial Alert Control
- `input_boolean.trmnl_alert_active`

The first alert implementation can simply use a helper so the override path exists before a richer alert system is built.

## Resolver Model

There should be one central resolver script or automation that computes the final requested mode.

Decision order for the first pass:

1. manual override if not `auto`
2. `alert` when enabled and active
3. `sonos` when enabled and playback is active or within hold window
4. `jen_commute` when enabled and commute context is active
5. `dave_commute` when enabled and its context is active
6. configured default mode if enabled
7. `idle`

Important rule:
- feature automations may produce payloads and signals
- only the central resolver should decide the final mode

## Implementation Stages

### Stage 1
- add configurable helpers
- add central resolver
- add Sonos hold tracking
- stop `jen_commute` from setting the display mode directly

### Stage 2
- stop any remaining feature automation from setting mode directly
- add real alert override path
- add `dave_commute`

### Stage 3
- optionally make priority order itself configurable instead of fixed
- add richer time-window policy
- add per-mode quiet hours if useful

## Validation

For each stage:

1. update HA config
2. run `ha core check`
3. restart HA
4. verify helper defaults are sane
5. verify resolver changes `input_select.trmnl_display_mode` correctly
6. verify the LaraPaper playlist bridge activates the expected playlist
7. verify the Pi displays the expected result

## Current Safe Default

Until the full resolver is validated:
- keep `input_boolean.trmnl_display_automation_enabled` off by default
- continue using the proven Sonos page as the live baseline
- only enable the global resolver once the priority behavior is explicit and tested
