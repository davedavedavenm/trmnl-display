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
- [x] Wire initial live runtime support for key settings (`theme`, `days_ahead`, `show_source_labels`, `max_events_per_day`)
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
- [x] Build a local Sonos webhook plugin using Sonos LAN APIs / `soco`
- [x] Support room name, artist, track, album, play state, album art
- [x] Avoid TRMNL cloud OAuth dependency entirely
- [x] Make Sonos plugin exportable/shareable as a recipe package
- [x] Add queue preview (`Up Next`)
- [x] Add grouped-room / multi-room awareness
- [x] Add automatic scheduled refresh for the local Sonos script on khpi5
- [ ] Add more live settings/runtime wiring for Sonos plugin options
- [ ] Explore Home Assistant automation-driven webhook updates as an alternative integration path

## Phase 10: Home Assistant Orchestration Layer [PLANNED]
- [x] Audit local HA config repo and host access paths (`homelab-ha/live-config`, `home-assistant`, `ha-super`)
- [x] Confirm relevant HA domains/entities already exist: Sonos media players, presence, commute system, Waze-based traffic, notifications
- [x] Add initial HA orchestration package with helpers and a proof automation
- [ ] Introduce a HA-side display mode helper (for example `input_select.trmnl_display_mode`)
- [ ] Define screen modes such as `calendar`, `jen_commute`, `dave_commute`, `sonos`, `alert`, `idle`
- [ ] Define priority/override order for screen modes so alerts and live context can supersede background screens
- [ ] Add HA `rest_command` pattern(s) for posting directly to LaraPaper custom plugin webhooks
- [ ] Add HA `shell_command` / SSH pattern(s) for invoking scripts on `khpi5` where local Python logic is preferable
- [ ] Build Jen commute plugin + HA automation path as the first HA-driven screen mode
- [ ] Build HA-driven Sonos mode switching as the second orchestration path
- [ ] Build alert override path as the third orchestration path
- [ ] Add example HA automations for webhook payload pushes and playlist/mode switching

## Phase 11: Google OAuth Companion Service [PLANNED]
- [ ] Build an optional local Google Calendar API companion service for richer metadata than ICS provides
- [ ] Support Google OAuth login flow, callback handling, refresh token storage, and token refresh
- [ ] Fetch richer event metadata: per-event colors, descriptions, attendee status, calendar list, and native Google attributes
- [ ] Keep the main multi-calendar recipe compatible with simple ICS feeds; use OAuth backend only as an advanced optional source
- [ ] Define secure local token storage and backup strategy for homelab use

## Phase 12: Optimization & Advanced Features [PLANNED]
- [ ] Tune refresh interval per-plugin (currently LaraPaper serves 120s; ACeP target is still 600s)
- [ ] Add sleep mode scheduling
- [ ] Explore custom ACeP-optimized recipes
- [ ] Consider image_webhook plugin for custom Python-generated content
- [ ] Add dark mode / night schedule
- [ ] Port InkyPi Python plugins as image_webhook plugins (if needed)
- [ ] Build custom color recipes using ACeP palette
- [ ] Evaluate bb_epaper dithering options for better color rendering
- [ ] Add a real-photo comparison workflow (plain vs dither vs mild saturation preprocess)
- [ ] Investigate optional image preprocessing controls for image-heavy plugins (saturation, contrast, sharpness)
- [ ] Add monitoring/alerting for display health

## Home Assistant Audit Notes
- Existing HA config already includes strong building blocks for orchestration:
  - Sonos entities: `media_player.living_room`, `media_player.bedroom`, `media_player.kitchen`, `media_player.gym`, `media_player.sonos_roam`
  - presence entities: `person.david`, `person.jennifer`
  - commute package/history: `jen_commute_system.yaml`
  - Waze commute signal: `sensor.waze`
  - existing rich automation style using helpers, scripts, notifications, and mobile app actions
- Best architecture is:
  - HA = orchestration and decision layer
  - LaraPaper = rendering layer
  - Pi = display client
- Preferred integration methods:
  - HA `rest_command` -> LaraPaper plugin webhook for direct payload pushes
  - HA `shell_command` / SSH -> script on `khpi5` when local Python logic is better

## Validation Gates
- **Gate A: Data fetch** - run sync script manually, verify all configured ICS feeds fetch successfully and payload includes expected events and source metadata.
- **Gate B: LaraPaper render** - verify plugin `current_image` regenerates and `/api/display` serves a new image filename.
- **Gate C: Device pull** - restart `trmnl-display.service` or wait for poll; confirm the Pi downloads the new image without errors.
- **Gate D: Physical render** - verify the screen updates cleanly with no partial-refresh corruption and expected color accents.
- **Gate E: Regression check** - confirm unrelated plugins still render and LaraPaper remains healthy after each change.
