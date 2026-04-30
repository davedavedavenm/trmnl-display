# TRMNL Integration: Progress Report

## Accomplishments to Date

### 1. Documentation Deep-Dive
- Audited official TRMNL BYOD and BYOS documentation.
- Analyzed the TRMNL Private API (/api/display) for image rendering and refresh cycles.
- Reviewed the trmnl-display Go client architecture.
- Researched all official BYOS server implementations (Terminus, LaraPaper, byos_fastapi, byos_django).
- Audited 700+ community recipes and 201 OSS catalog recipes for color e-ink compatibility.

### 2. Hardware Audit
- **Confirmed Device:** Pimoroni Inky Impression 7.3" (800x480).
- **Panel Type:** 7-color ACeP (Black, White, Red, Green, Blue, Yellow, Orange) - NOT grayscale only.
- **Driver:** `bb_epaper` via `show_img` binary with `EP73_SPECTRA_800x480` panel driver.
- **Refresh Mode:** Only `REFRESH_FULL` works on ACeP. No partial/fast refresh available.
- **Refresh Interval:** 15-30 seconds per refresh. Recommended 600s (10 min) poll interval.
- **Panel Lifetime:** ~50,000-100,000 refresh cycles.
- **Permissions:** User `dave` has spi/gpio/i2c group membership. No sudo required.

### 3. Migration Strategy
- Authored and pushed docs/TRMNL_INTEGRATION_PLAN.md to GitHub.
- Defined a phased approach: Hardware PoC -> BYOS Server -> Plugin Migration.
- Evolved plan: BYOS server moved from Pi Zero to khpi5 (Pi 5, 16GB RAM, NVMe).

### 4. Hardware PoC - COMPLETE
- Mock server deployed and validated on Pi.
- Go client (`trmnl-display`) built and tested on Pi Zero.
- Physical screen render confirmed: `show_img` -> SPI -> EPD works end-to-end.
- Color render verified: 4-bpp (7-color) mode confirmed via BMP test image.

### 5. BYOS Server - LaraPaper on khpi5 - COMPLETE
- **Evaluated byos_fastapi:** Too heavy for Pi Zero (requires Chromium, d3blocks, 100MB+ RAM).
- **Built custom Flask BYOS server** (`scripts/trmnl_byos_server.py`) - lightweight, ~30MB RAM.
- **Deployed LaraPaper** on khpi5 via Docker (ghcr.io/usetrmnl/larapaper:latest).
- LaraPaper runs on port 4567 with Docker volumes for database and storage persistence.
- Device registered: MAC `88:A2:9E:2B:2B:B9`; the API key is stored only in the live Pi config and must not be committed.

### 6. Color E-Ink Configuration - COMPLETE
- Updated LaraPaper `inky_impression_7_3` device model: 7 colors, 3-bit, palette `color-7a`.
- Updated `show_img.json` on Pi: removed `panel_2bit` to enable 4-bpp color mode.
- Verified: LaraPaper generates 4-bit colormap PNGs when device model is set correctly.
- `trmnl-liquid-cli` installed in LaraPaper container for recipe rendering.

### 7. Systemd Services - COMPLETE (Pi Zero)
- **trmnl-display.service:** Runs Go client, points at khpi5:4567, enabled at boot.
- **trmnl-byos.service:** Local Flask BYOS server (now DISABLED - replaced by LaraPaper on khpi5).
- Both services auto-restart on failure with 15s delay.

### 8. Recipe Research - COMPLETE
- Audited all 201 OSS catalog recipes and TRMNL official catalog.
- **Zero recipes explicitly support 7-color ACeP**, but many use semantic colors that map well.
- Identified top candidates: Uptime Kuma, Crypto Fear & Greed, Air Quality, F1 Dashboard, US Weather Maps.
- Comics and photos work but with heavy dithering.

### 9. Installed Plugins (in LaraPaper)
- OBB Departures (recipe)
- Weather (recipe)
- Zen Quotes (recipe)
- This Day in History (recipe)
- Home Assistant (recipe) - needs correct HA URL
- Sunrise/Sunset (recipe)
- Pollen Forecast (recipe)
- Holidays iCal (recipe)
- Netflix Release Radar (recipe)
- Horizontal World Clock (recipe) - needs timezone config
- UK Bus Departures TransportAPI (recipe) - polling URL hardcoded to fix Liquid template bug
- Uptime Kuma Statuspage (recipe)

### 10. Multi-Calendar Plugin - IN PROGRESS
- Built a working webhook-driven multi-calendar proof of concept using `scripts/trmnl_calendar_multi.py`.
- Current implementation merges multiple Google ICS feeds locally on khpi5 and POSTs the result to LaraPaper.
- Current recipe package lives in `plugins/trmnl-multi-calendar/` and is import/export compatible in structure.
- Source labels and source colors are already present in payload and render path.
- Expanded the recipe schema to support up to 6 calendar feeds, per-calendar labels, per-calendar colors, optional custom colors, and optional HTTP headers.
- Added provider setup guidance for Google, Apple/iCloud, Outlook, and generic CalDAV/ICS.
- Added split-screen support with dedicated `half_horizontal.liquid` and `quadrant.liquid` templates for mashups.
- Migrated the live khpi5 runtime to the new 6-calendar env format and added a third live calendar feed.
- Added event-level color resolution logic: native event color -> category mapping -> calendar color fallback.
- Added an explicit dark-mode, high-contrast treatment to improve physical ACeP readability.
- Wired live LaraPaper custom settings into the runtime script for key behaviors (`theme`, `days_ahead`, `show_source_labels`, `max_events_per_day`).
- Baseline verified: events are fetched, merged, posted, rendered, and shown on the physical display.
- Live khpi5 deployment has now been migrated to the new 6-calendar-ready env format and revalidated end to end.
- Current gap: the layout still needs a stronger final design pass.

### 11. Official Calendar Feature Audit - COMPLETE
- Audited official TRMNL **Google Calendar** integration page.
- Audited official TRMNL **CalDAV** integration page.
- Extracted common feature surface to guide the custom plugin roadmap:
  - multiple layouts (`Agenda`, `Default`, `Week`, `Rolling Week`, `Work Week`, `Month`, `Rolling Month`)
  - `12h/24h`, multiple date formats, timezone override
  - include descriptions, include event times, include past events
  - fixed week, week start day, fixed start/end time
  - ignored phrases, event status filter, highlight today
  - week numbers, current time indicator, vertical alignment
  - CalDAV-specific ideas: multiple ICS URLs, optional HTTP headers

### 12. Provider Compatibility Notes - COMPLETE
- **Google Calendar:** use `Settings -> Integrate calendar -> Secret address in iCal format`.
- **Apple/iCloud:** use `Public Calendar` sharing and copy the generated link.
- **Outlook.com / Outlook on the web:** subscribe via ICS/web URL; updates may lag significantly.
- **Generic CalDAV/ICS:** official TRMNL CalDAV plugin accepts published ICS endpoints and optional HTTP headers.
- **Google CalDAV:** not a realistic current path for this project; Google Calendar is better accessed via ICS (simple) or Google Calendar API via OAuth (richer, more complex).

### 13. Local Sonos Plugin - IN PROGRESS
- Built a local Sonos now-playing proof of concept using `soco` on `khpi5`.
- Sonos discovery works locally without TRMNL cloud OAuth.
- Current implementation detects active rooms/groups, reads current track metadata, album art, and queue preview.
- Added multi-room context support: grouped rooms, same-content rooms, and other active rooms.
- Added a shareable recipe package under `plugins/trmnl-sonos-local/`.
- Installed a `khpi5` cron-driven local refresh path for the Sonos script (`/home/dave/run_trmnl_sonos.sh`).
- Added local album-art preprocessing in the Sonos script so LaraPaper receives a preprocessed image instead of only the raw Sonos URL.
- Restored a full-colour Sonos path by generating multiple album-art variants server-side and exposing recipe-level render modes (`vivid`, `balanced`, `raw`, `mono`) through `settings.yml`.
- Diagnosed a live colour regression correctly by inspecting the LaraPaper preview/generated PNG instead of treating the physical panel as the only source of truth.
- Root cause of the regression: live LaraPaper model drift on `khpi5` had changed `inky_impression_7_3` to `colors=2`, `bit_depth=1`, `palette=bw`.
- Additional Sonos-specific finding: when no album art is present, subtle accent colours can quantize away; stronger ACeP-safe solid fills survive the render pipeline more reliably.
- Verified end-to-end: local discovery -> webhook POST -> LaraPaper render -> Pi display update.
- Home Assistant integration paths identified: HA automation can either POST directly to the webhook or invoke the local Sonos script.

### 14. Home Assistant Audit - COMPLETE (Read-Only)
- Identified local HA config repo: `C:\Users\Dave\repos\homelab-ha\live-config`.
- Identified HA host access paths: `home-assistant` / `ha-super` -> `192.168.1.89:2222`.
- Confirmed strong existing HA building blocks for screen orchestration:
  - Sonos media players across multiple rooms
  - `person.david` / `person.jennifer` presence tracking
  - substantial Jen commute package and Waze-based traffic summary logic
  - extensive helper/script/automation patterns already in use
- Conclusion: HA should act as the orchestration layer while LaraPaper remains the rendering layer and the Pi remains the display client.
- Recommended next HA implementation path:
  1. add a display-mode helper in HA
  2. build Jen commute as the first HA-driven screen mode
  3. add Sonos and alert override modes
  4. use HA `rest_command` / `shell_command` patterns to drive LaraPaper

### 15. Home Assistant Proof Automation - COMPLETE
- Added `packages/trmnl_display_orchestration.yaml` to the HA config.
- Created helper entities:
  - `input_boolean.trmnl_display_automation_enabled`
  - `input_select.trmnl_display_mode`
- Added `rest_command.trmnl_sonos_push` for direct HA -> LaraPaper webhook posting.
- Added automation `automation.trmnl_sonos_push_from_ha`.
- Validation:
  - package deployed to `/config/packages/`
  - `ha core check` passed
- HA core restarted successfully
- logs confirmed the automation executed from the time-pattern trigger and called services successfully
- This provides a concrete proof that HA can orchestrate TRMNL/LaraPaper directly, not just in theory.

### 15a. Home Assistant Playlist Switching Bridge - COMPLETE
- Added a local mode-switch script under `scripts/trmnl_set_display_mode.sh`.
- Deployed that script to `khpi5` as `/home/dave/bin/trmnl-set-display-mode`.
- Added a small authenticated HTTP mode bridge on `khpi5` so Home Assistant can request playlist changes without SSHing out of the HA core container.
- Confirmed LaraPaper's native playlist model is the correct switch mechanism: devices render from the first active playlist with an available item.
- Updated Home Assistant to call the local bridge with `rest_command`.
- Verified end to end:
  - HA resolves `calendar`, `sonos`, and `alert` correctly
  - `khpi5` accepts those mode changes on demand
  - active playlist was restored to `sonos` after testing
- Important current constraint: the global mode-switch automation remains gated by `input_boolean.trmnl_display_automation_enabled`, which is still the correct safe default until priority rules are defined.

### 15b. First Customizable Display Resolver - COMPLETE
- Added the first helper-driven policy layer in Home Assistant.
- New helper categories now exist for:
  - default mode
  - manual override
  - per-mode enable flags
  - Sonos hold minutes
  - Sonos hold-until timestamp
  - initial alert-active and dave-commute-active signals
- Added a central resolver automation that computes the final display mode from one place instead of letting feature automations compete directly.
- Decision order in the first pass:
  - manual override
  - alert
  - sonos
  - jen_commute
  - dave_commute
  - configured default mode
  - idle
- Adjusted the architecture so:
  - feature automations push payloads and expose signals
  - the resolver owns `input_select.trmnl_display_mode`
  - the LaraPaper playlist bridge applies the chosen mode
- Validation:
  - package deployed to Home Assistant
  - `ha core check` passed
  - HA restarted successfully
  - active LaraPaper playlist remained on `sonos` because the master automation switch is still off, which is the intended safe default

### 15c. Alert Override Path - COMPLETE
- Added a shareable `plugins/trmnl-alert/` recipe package to the repo.
- Created a live LaraPaper `Alert` plugin on `khpi5`.
- Added a new HA webhook path for the alert plugin.
- Added helper fields for alert title, message, footer, and severity.
- Added simple HA scripts for:
  - setting the active alert payload
  - clearing the alert-active signal
- Verified end to end:
  - alert webhook payload POST succeeds
  - LaraPaper `alert` playlist can be activated on demand
  - active playlist was restored to `sonos` after testing
- Current shape is intentionally simple: the alert path now exists as a real override screen, and richer alert sources can be wired into it later.

### 16. Jen Commute Recipe Track - STARTED
- Added a shareable `plugins/trmnl-jen-commute/` recipe package to this repo.
- Positioned `jen_commute` as the next Home Assistant-driven screen after Sonos stabilization.
- Working rule for this track: keep commute decision logic in Home Assistant and keep the recipe webhook payload simple and shareable.
- Added a live LaraPaper custom plugin on `khpi5` and a matching HA webhook path.
- Tightened the recipe contract so it uses a cleaner shareable payload, optional screen labeling, and safer empty-state handling.
- Fixed a recipe bug where the map-link panel could render without a valid `map_url`.
- Tightened the HA automation so it only claims the display mode when commute context is actually active, rather than hijacking the screen while idle.

### 16a. Community Pattern Audit - COMPLETE
- Confirmed that official TRMNL guidance supports Home Assistant integration and a separate screenshot-based dashboard path.
- Confirmed that community TRMNL examples already use the pattern `Home Assistant state -> webhook payload -> TRMNL recipe/plugin render`.
- Confirmed that broader e-paper/Home Assistant projects commonly use thin display clients with server-side or HA-side orchestration.
- Conclusion: this repo should stay recipe-first and payload-first for shareable work, while treating screenshot flows as a valid but secondary option for dense dashboards.
- Reference set:
  - [TRMNL Home Assistant Integration](https://help.trmnl.com/en/articles/12494449-home-assistant-integration)
  - [TRMNL Home Assistant Screenshot](https://help.trmnl.com/en/articles/13281388-home-assistant-screenshot)
  - [ha_trmnl_weather_station](https://github.com/TilmanGriesel/ha_trmnl_weather_station)
  - [hass-inkplate-dashboards](https://github.com/brodykenrick/hass-inkplate-dashboards)
  - [Home-Assistant-eink-remote-display](https://github.com/briandorey/Home-Assistant-eink-remote-display)

### 17. Future Work: Optional Google OAuth Companion
- Added a future-work track for an optional local Google Calendar API companion service.
- Rationale: Google ICS feeds do not expose useful per-event color/category metadata in the current live calendars.
- Goal: enable richer Google-specific metadata such as per-event colors, descriptions, attendee status, and other native fields.
- Important constraint: this would be an advanced optional local backend, not a replacement for the shareable ICS-based plugin path.

### 18. Future Work: Render Crispness / Screenshot Quality
- Added a future-work track to investigate render-side sharpness improvements, not just CSS/layout tweaks.
- LaraPaper's rendering stack exposes scale-related hooks (`scale_factor`, Browsershot/device scale options) that may improve text crispness before panel quantization.
- This should be evaluated carefully on the physical ACeP panel because sharper source screenshots may improve legibility more than additional design changes.

### 19. Color Pipeline Experiment - COMPLETE
- Built controlled LaraPaper comparison plugins for image-heavy rendering.
- Compared four render paths on the physical display:
  - plain palette mapping
  - dithering enabled via `image-dither`
  - saturation preprocessed to `0.0`
  - saturation preprocessed to `0.5`
- Findings:
  - plain palette mapping preserves distinct ACeP colors well for simple graphics
  - generic dithering adds objectionable visible noise/patterning on this panel for this content
  - saturation `0.0` collapses color separation too aggressively
  - saturation `0.5` is a more promising preprocessing direction than full desaturation
- Conclusion: do not enable dithering globally; image-heavy/photo workflows likely need tuned preprocessing rather than naive dithering.
- Next validation needed: repeat the same test with a real photograph, not just synthetic graphics.

### 20. Known Issues
- **Bus departures:** Liquid template `timespan` variable not injected into polling URL. Workaround: hardcoded full URL.
- **Home Assistant:** URL `raspberrypi.local` not resolvable from khpi5 container. Needs correct IP.
- **World Clock:** No timezone/city data configured.
- **Duplicate device bug:** LaraPaper auto-assign creates ghost devices when `assign_new_devices=1` and Go client sends empty `ID` header. Fix: disabled auto-assign, set correct config.
- **Force refresh:** No UI button. Must run `ssh trmnl-pi 'sudo systemctl restart trmnl-display'`.
- **Calendar UX:** current multi-calendar layout works but needs a proper polished design pass and richer configuration options.
- **Calendar settings:** key settings are now wired through, but not every field from the schema is implemented in the runtime yet.
- **Calendar crispness:** render-side sharpness tuning has not yet been tested; current improvements are mostly contrast and styling based.
- **Photo quality:** LaraPaper color rendering is improved by careful preprocessing, but a true real-photo comparison against old Inky Impression 7.3 behavior is still outstanding.
- **Sonos polish:** the local Sonos plugin is functional and respectable, but still has room for layout polish and broader settings/runtime wiring.
- **Operational memory:** first inspect LaraPaper preview/current PNG when debugging display appearance. Only treat the panel as the differentiator after the server render is known.

### 21. ACeP Color Pipeline Fix - COMPLETE
- **Root cause:** LaraPaper container auto-updated to Chromium 144, which renders CSS colors in Display P3 color space instead of sRGB. This causes `#FF0000` (Red) to render as `#FF00FF` (Magenta) and `#00FF00` (Green) to render as `#00FFFF` (Cyan). The `remapImage()` step then maps these shifted colors to wrong palette entries, eliminating Red and Green from the 7-color ACeP output.
- **Previously working:** an older LaraPaper build (pre-Chromium 144) rendered colors correctly, which is why full color was seen on the screen before.
- **Fixes applied to LaraPaper on khpi5 (in-container patches, not persistent across docker image pulls):**
  1. Device model `inky_impression_7_3` palette restored to `color-7a` (id=6), `colors=7`, `bit_depth=4` — was drifted to `bw` (id=1), `colors=2`, `bit_depth=1`.
  2. Added `fixDisplayP3ColorShifts()` method to `ImageStage.php` — replaces `#FF00FF→#FF0000` and `#00FFFF→#00FF00` before palette remapping.
  3. Added `transformImageColorspace(COLORSPACE_SRGB)` call before colormap application for color palettes.
  4. Changed `remapImage()` to always use `DITHERMETHOD_FLOYDSTEINBERG` instead of `DITHERMETHOD_NO` (was defaulting to no dithering).
  5. Added Chromium flags `--force-color-profile=srgb` and `--force-rendering-color-space=srgb` to Puppeteer args in `ImageGenerationService.php`.
  6. Added `color-profile: srgb` CSS to the HA dashboard template.
- **Result:** All 7 ACeP colors now render correctly. Green (#00FF00) has 104,487px (27.2%), Red (#FF0000) has 2,469px (0.6%), matching the intended layout.
- **HA Dashboard redesign:** Redesigned Presence panel (red background with white/green badges) and Home panel (black background with green accent lines/highlights). Both panels now use ACeP-safe solid color backgrounds instead of thin borders or subtle fills that dither poorly.
- **Warning:** These patches are in-container changes to the LaraPaper Docker container. They will be lost on `docker compose pull && docker compose up -d`. A persistent solution requires either:
  - Upstream fix in `trmnl-pipeline-php` (filed as potential PR)
  - Custom Dockerfile that applies patches on build
  - Volume-mounted override of the patched PHP files
- **Template changes:** `plugins/trmnl-ha-dashboard/full.liquid` completely redesigned with 4-panel layout (Weather/blue, Presence/red, Home/black+green, Sonos/orange), all using solid ACeP-safe color fills.

## Architecture

```
[Pi Zero - Inky Impression 7.3]
    |
    | systemd: trmnl-display.service
    | polls every 600s (configurable via LaraPaper)
    | headers: ID=MAC, access-token=API_KEY
    v
    GET http://192.168.1.143:4567/api/display
    |
    v
[Pi 5 - khpi5]
    |
    | Docker: ghcr.io/usetrmnl/larapaper:latest
    | Port 4567
    | Renders Liquid templates via headless browser
    | Applies 7-color palette via ImageStage->colormap()
    | Returns: {image_url, filename, refresh_rate}
    v
    Pi Zero downloads PNG -> show_img -> SPI -> EPD
```

## File Locations

### Pi Zero (trmnl-pi) - Display Client
| Component | Path |
|---|---|
| Go Client | `/home/dave/trmnl-display/trmnl-display` |
| Client Config | `/home/dave/.config/trmnl/config.json` |
| show_img | `/usr/local/bin/show_img` |
| show_img Config | `/home/dave/.config/trmnl/show_img.json` |
| systemd (display) | `/etc/systemd/system/trmnl-display.service` |
| Old BYOS Server | `/home/dave/trmnl-byos/server.py` (DISABLED) |
| Old BYOS systemd | `/etc/systemd/system/trmnl-byos.service` (DISABLED) |

### Pi 5 (khpi5) - BYOS Server
| Component | Path |
|---|---|
| Docker Compose | `/home/dave/larapaper/docker-compose.yml` |
| Database Volume | `larapaper_database` |
| Storage Volume | `larapaper_storage` |
| Image Output | `storage/app/public/images/generated/` |
| Web UI | `http://192.168.1.143:4567` |

## Next Planned Steps
1. Migrate the live khpi5 calendar sync to the new 6-calendar-ready env format.
2. Validate the new script end to end on the physical screen.
3. Continue productizing the calendar plugin settings so runtime behavior matches the shareable schema.
4. Redesign the multi-calendar layout with e-ink-first polish while preserving the working data path.
5. Build a local Sonos plugin using LAN APIs instead of TRMNL cloud OAuth.
6. Continue stage-by-stage E2E validation after each change (fetch -> render -> device pull -> physical screen).

## Validation Baseline (Current)
- **Data fetch:** `python main.py` on khpi5 successfully fetched both configured ICS feeds and posted to LaraPaper.
- **Server render:** `/api/display` returned a fresh generated image URL for the device.
- **Client service:** `trmnl-display.service` on trmnl-pi is active and polling LaraPaper successfully.
- **Physical display:** calendar data is visible on screen, confirming the end-to-end pipeline works at baseline.

## Validation Stage: 6-Calendar Runtime Migration
- **Stage 1:** migrated live env from legacy `TRMNL_ICS_*` variables to `TRMNL_CAL1_* ... TRMNL_CAL6_*` format.
- **Stage 2:** manual sync execution on khpi5 fetched both live calendars successfully and returned HTTP 200 from the webhook endpoint.
- **Stage 3:** `/api/display` returned a fresh generated image (`670c3848-be8f-4383-9fa5-7e5fdb1bdac3.png`) after the migration.
- **Stage 4:** `trmnl-display.service` restarted cleanly and invoked `show_img` on the Pi, confirming device pull + physical render path still works.
