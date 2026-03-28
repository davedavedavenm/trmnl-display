# TRMNL Project Plan

## Phase 1: Hardware PoC [COMPLETE]
- [x] Verify Pimoroni Inky Impression 7.3" compatibility with trmnl-display
- [x] Build and deploy Go client on Pi Zero
- [x] Confirm SPI permissions and show_img driver
- [x] Physical screen render test (grayscale + color)

## Phase 2: BYOS Server [COMPLETE]
- [x] Evaluate BYOS server options (Terminus, LaraPaper, byos_fastapi, custom Flask)
- [x] Deploy LaraPaper on khpi5 via Docker
- [x] Configure Docker volumes for persistence
- [x] Register device and configure API key
- [x] Fix duplicate device bug (disable auto-assign)
- [x] Point Pi Zero client at khpi5:4567

## Phase 3: Color E-Ink [COMPLETE]
- [x] Identify panel as 7-color ACeP (not grayscale)
- [x] Research bb_epaper color mode (4-bpp via BBEP_7COLOR)
- [x] Fix show_img.json (remove panel_2bit for 7-color mode)
- [x] Update LaraPaper device model (7 colors, 3-bit, color-7a palette)
- [x] Verify color image generation pipeline

## Phase 4: Systemd & Persistence [COMPLETE]
- [x] Create trmnl-display.service on Pi Zero
- [x] Create trmnl-byos.service on Pi Zero (now disabled)
- [x] Enable services for boot persistence
- [x] Configure Go client (api_key, device_id, base_url)

## Phase 5: Recipe Research & Installation [COMPLETE]
- [x] Audit 201 OSS catalog recipes for color compatibility
- [x] Audit TRMNL official catalog for color-capable recipes
- [x] Install initial recipes (12 plugins)
- [x] Fix bus departures polling URL

## Phase 6: Maintenance & Operations [COMPLETE]
- [x] Set up LaraPaper auto-update via cron on khpi5
- [x] Remove old InkyPi BYOS server + systemd service from Pi Zero
- [x] E2E validate full pipeline after cleanup
- [x] Remove legacy InkyPi systemd service from Pi Zero
- [ ] Fix Home Assistant recipe URL (raspberrypi.local not resolvable from khpi5)
- [ ] Configure World Clock timezones
- [ ] Fix bus departures Liquid template variable binding

## Phase 7: Multi-Calendar Productization [IN PROGRESS]
- [x] Build working webhook-driven multi-calendar proof of concept
- [x] Merge multiple Google ICS feeds into a single payload
- [x] Add source labels and source colors in payload
- [x] Create initial shareable recipe package under `plugins/trmnl-multi-calendar/`
- [x] Expand schema from 2 feeds to up to 6 configurable calendar feeds
- [x] Add per-calendar config: enabled, label, ICS URL, palette color
- [x] Add provider support docs: Google, Apple/iCloud, Outlook, generic CalDAV/ICS
- [x] Add provider-specific options: ICS headers for authenticated feeds
- [x] Add recipe-level options: days ahead, layout style, time format, date format
- [x] Add recipe-level options: show labels, show all-day, hide empty days, max events/day
- [x] Add recipe-level options: timezone override, week start day, highlight today
- [x] Add import/export-safe `settings.yml` compatible with LaraPaper/TRMNL ZIP format
- [x] Validate schema/script migration end-to-end on the physical display
- [ ] Continue validating every subsequent stage end-to-end before moving on

## Phase 8: Calendar UX & Visual Design [PLANNED]
- [ ] Base designs on official TRMNL Google Calendar and CalDAV integrations
- [x] Add split-specific layouts for mashups (`half_horizontal`, `quadrant`)
- [x] Add explicit dark-mode, high-contrast theme pass
- [ ] Add explicit light/dark theme option in plugin settings and runtime wiring
- [ ] Create a strong default layout: compact editorial agenda
- [ ] Create alternate layouts: cards, week strip, agenda focus
- [ ] Keep e-ink-first color behavior using the 7-color ACeP-safe palette
- [ ] Add support for higher-density event display when more days/events are present
- [ ] Validate readability on the physical 800x480 panel at typical viewing distance
- [ ] Test render-side sharpness improvements via LaraPaper/device scale settings

## Phase 9: Local Sonos Integration [PLANNED]
- [ ] Build a local Sonos webhook plugin using Sonos LAN APIs / `soco`
- [ ] Support room name, artist, track, album, play state, volume, album art
- [ ] Avoid TRMNL cloud OAuth dependency entirely
- [ ] Make Sonos plugin exportable/shareable as a recipe package

## Phase 10: Google OAuth Companion Service [PLANNED]
- [ ] Build an optional local Google Calendar API companion service for richer metadata than ICS provides
- [ ] Support Google OAuth login flow, callback handling, refresh token storage, and token refresh
- [ ] Fetch richer event metadata: per-event colors, descriptions, attendee status, calendar list, and native Google attributes
- [ ] Keep the main multi-calendar recipe compatible with simple ICS feeds; use OAuth backend only as an advanced optional source
- [ ] Define secure local token storage and backup strategy for homelab use

## Phase 11: Optimization & Advanced Features [PLANNED]
- [ ] Tune refresh interval per-plugin (currently LaraPaper serves 120s; ACeP target is still 600s)
- [ ] Add sleep mode scheduling
- [ ] Explore custom ACeP-optimized recipes
- [ ] Consider image_webhook plugin for custom Python-generated content
- [ ] Add dark mode / night schedule
- [ ] Port InkyPi Python plugins as image_webhook plugins (if needed)
- [ ] Build custom color recipes using ACeP palette
- [ ] Evaluate bb_epaper dithering options for better color rendering
- [ ] Add monitoring/alerting for display health

## Validation Gates
- **Gate A: Data fetch** - run sync script manually, verify all configured ICS feeds fetch successfully and payload includes expected events and source metadata.
- **Gate B: LaraPaper render** - verify plugin `current_image` regenerates and `/api/display` serves a new image filename.
- **Gate C: Device pull** - restart `trmnl-display.service` or wait for poll; confirm the Pi downloads the new image without errors.
- **Gate D: Physical render** - verify the screen updates cleanly with no partial-refresh corruption and expected color accents.
- **Gate E: Regression check** - confirm unrelated plugins still render and LaraPaper remains healthy after each change.
