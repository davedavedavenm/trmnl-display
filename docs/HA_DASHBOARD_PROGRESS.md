# HA Dashboard Plugin - Progress Report

## Overview
The Home Assistant Dashboard plugin (`trmnl-ha-dashboard`) was redesigned from a basic developer-style terminal output into a polished, 7-color ACeP e-ink optimized "Bento-box" layout. The plugin is now fully user-configurable through the LaraPaper web UI with 9 editable fields.

## Design Evolution

### V1: Original (Terminal-Style)
- Pure black background with thin neon RGB borders
- Text-heavy, utilitarian layout
- Static Sonos card showing all 5 rooms regardless of state
- No iconography, no album art
- Suffered from pigment bleeding on ACeP e-ink panel

### V2: Bento-Box Redesign
- **Solid Color Blocks:** Replaced thin borders with large, solid ACeP color blocks (White, Blue, Red, Yellow) that render cleanly on e-ink
- **Dynamic Layout:** Sonos card only appears when music is playing; Weather and Home Status cards expand to fill available space when idle
- **Rich Media:** Album art fetched via `entity_picture` and displayed as large thumbnails
- **Chunky SVGs:** Replaced thin wireframe icons with heavy, filled SVG paths for maximum readability
- **Heavy Typography:** Font weights increased to 900, temperature display scaled to 90px/60px
- **Status Badges:** Humidity, wind, blind position, and thermostat temp rendered as high-contrast capsules (black pills with colored text)

## Technical Changes

### 1. Python Script (`scripts/trmnl_ha_dashboard.py`)
- Added `entity_picture` fetching for Sonos album art
- Added error logging for debugging HA connectivity issues
- Updated to fetch real-time data from Home Assistant API

### 2. Liquid Template (`plugins/trmnl-ha-dashboard/full.liquid`)
- Complete rewrite using CSS Grid (2x2 layout)
- Conditional rendering for Sonos card (`{% if is_playing %}`)
- Defensive Liquid checks (`{% if weather.temperature != blank %}` instead of `{% if weather %}`)
- Container height set to `470px` (from `480px`) to prevent bottom cut-off
- Grid rows use `minmax(0, 1fr)` to prevent overflow

### 3. Plugin Schema (`plugins/trmnl-ha-dashboard/settings.yml`)
- Added `description`, `author`, `version` fields for TRMNL compliance
- Added 9 `custom_fields` for user-editable configuration:
  - `ha_url` (text): Home Assistant URL
  - `ha_token` (password): Long-Lived Access Token
  - `sonos_entities` (multi_string): Comma-separated Sonos media players
  - `person_entities` (multi_string): Comma-separated person entities
  - `weather_entity` (text): Weather entity ID
  - `door_entity` (text): Door lock binary sensor
  - `washer_entity` (text): Washer status binary sensor
  - `blind_entity` (text): Blinds cover entity
  - `thermostat_entity` (text): Climate/thermostat entity

### 4. LaraPaper Database Configuration
- Updated `configuration_template` with proper `name` keys (not `label`)
- Populated default `configuration` values for all 9 fields
- Set `palette_id` to `6` (color-7a) to enable 7-color ACeP rendering

### 5. Documentation
- Created `.cursorrules` with strict AI directives for future agents
- Updated `docs/building_plugins.md` with:
  - Defensive Liquid Templates section
  - E-Ink Visual Design Rules (7-color ACeP)
  - E2E Validation of Plugins workflow
- Added `plugins/trmnl-ha-dashboard/README.md` for community shareability

## E2E Validation Process

The following pipeline was verified end-to-end:
1. **Payload Push:** Webhook POST to LaraPaper (`/api/custom_plugins/{uuid}`) returns 200
2. **Database Update:** `current_image` UUID generated in LaraPaper SQLite DB
3. **Image Extraction:** PNG copied from `larapaper_storage` Docker volume
4. **Visual Inspection:** Screenshot downloaded and verified for:
   - No `Liquid error` messages
   - Correct color mapping (White, Blue, Red, Yellow blocks)
   - No bottom cut-off (all 4 rows visible)
   - Album art rendering when Sonos is playing
5. **Display Client:** `trmnl-display.service` on `inky-pi` actively polling `/api/display` every ~6 minutes

## Known Issues Resolved
- **500 Error on Recipe Page:** Fixed by changing `label` to `name` in custom_fields (LaraPaper validation requirement)
- **Grayscale Rendering:** Fixed by setting `palette_id=6` (color-7a) in devices table
- **Bottom Cut-off:** Fixed by reducing container height to `470px` and tightening grid gaps
- **Invalid HA Token:** Discovered stored token on `khpi5` was returning 401; updated to active token

## Architecture Notes
- **Deployment Topology:** BYOS server on `khpi5` (LaraPaper via Docker), display client on `inky-pi` (192.168.1.89)
- **Plugin Strategy:** `webhook` - Home Assistant pushes data via `rest_command` automation
- **Rendering:** LaraPaper uses external Ruby liquid renderer (`trmnl-liquid`) for templates with `for` loops
- **Image Pipeline:** Liquid template + JSON payload → Headless Chrome → PNG → InkyPi display client

## Next Steps
- Fix HA automation packages (`alexa_e2e_test_package_v1.yaml`, `auto_test_house_empty.yaml`) that prevent `ha core check` from passing
- Migrate HA dashboard push from Python script to native Home Assistant `rest_command` automation
- Add Google OAuth companion for richer calendar metadata
- Implement Jen Commute recipe as next HA-driven screen
