# Jen Morning Mashup

This document captures the LaraPaper playlist state for the current morning split-screen layout.

## Current Intended Mashup

- playlist: `TRMNL Mode: jen_morning`
- layout: `1Lx1R`
- left plugin: `Jen Morning`
- right plugin: `Potter Quotes`
- mashup name: `Jen Morning + Potter Quotes`

This is a LaraPaper playlist/database concern. It is not stored in Home Assistant and it is not encoded in the `Jen Morning` plugin itself.

## Recreate Or Repair

Run the script on the LaraPaper host:

```bash
bash scripts/larapaper_manage_mashup.sh apply
```

Check the current playlist state:

```bash
bash scripts/larapaper_manage_mashup.sh status
```

## Environment Overrides

The script is parameterized so the pattern can be reused:

- `PLAYLIST_NAME`
- `LEFT_PLUGIN_NAME`
- `RIGHT_PLUGIN_NAME`
- `MASHUP_LAYOUT`
- `MASHUP_NAME`
- `LARAPAPER_CONTAINER`

Example:

```bash
PLAYLIST_NAME="TRMNL Mode: jen_morning" \
LEFT_PLUGIN_NAME="Jen Morning" \
RIGHT_PLUGIN_NAME="Potter Quotes" \
MASHUP_LAYOUT="1Lx1R" \
bash scripts/larapaper_manage_mashup.sh apply
```

## Notes

- The script updates playlist DB state only.
- It does not create or edit the plugin templates.
- The `Jen Morning` template and user-editable fields still live in:
  - `plugins/trmnl-jen-morning/settings.yml`
  - `plugins/trmnl-jen-morning/full.liquid`
  - `plugins/trmnl-jen-morning/half_vertical.liquid`
- Home Assistant owns the data payload and display override timing.
