# Changelog

## 2026-07-26

- Added explicit `healthy`, `degraded`, and `unavailable` source health to the
  Nango and Fire calendar payloads. Provider failures now carry redacted type
  and HTTP-status diagnostics instead of being indistinguishable from an empty
  calendar.
- Kept the SpaceMail CalDAV client open through discovery and event search,
  added bounded retry/backoff, and verified five consecutive live 30-day reads.
- Coalesced simultaneous 7-day and 30-day Home Assistant requests into one
  cached 30-day provider fetch, then safely trimmed each response. This removes
  the two-sensor CalDAV race without changing either dashboard's horizon.
- Preserved the previous HA weekend-event helper state whenever source health
  is not fully healthy, preventing an outage from writing a false `off` state.
- Added four regression tests for healthy, partial-failure, total-failure and
  credential-safe diagnostic behavior. Python compilation and tests pass; the
  live bridge was backed up, deployed, restarted and verified active.

## 2026-07-14

- Reconciled drift in `plugins/trmnl-calendar-dayview/README.md`: replaced
  the stale four-row "Data Sources" table (which hardcoded four personal
  calendar sources) with a portable description of the twelve-slot model
  defined in `settings.yml`. The live plugin (LaraPaper plugin #27 on
  `khpi5`) binds eleven slots across eight Nango connections, so the
  README now documents the slot fields generically and stays shareable.
- Disabled slot 8 of LaraPaper plugin #27 (Calendar Day View). Slot 8
  pointed at the Outlook `United Kingdom holidays` sub-calendar on the
  `outlook-example` connection and was the source of unwanted UK
  bank-holiday events appearing on the physical display. Applied as a
  live DB edit (`calendar_8_connection_id` cleared); `settings.yml`
  ships no slot-8 value, so no repo value required changing.
- Read-only inventory of one identity that has two Nango connections
  (Google + Outlook) confirmed a dormant Google
  `Holidays in United Kingdom` sub-calendar that is intentionally not
  slotted, and that one slot's on-screen label matches its source
  calendar name but holds family scheduling rather than public holidays.
- Relabeled Calendar Day View slots on LaraPaper plugin #27 to match
  account reality (a couple of slots were relabeled to the correct
  owner; one had been misattributed). Where a Google account's primary
  calendar id differs from the address originally used to connect it,
  the slot now resolves to the current primary id.
- A Nango connection_id handle that no longer matches its owner's current
  address is intentionally retained: Nango's admin API does not support
  renaming a connection_id (it is the immutable primary key; `PATCH
  /connections/{id}` only edits tags/webhook/end_user). The handle is
  invisible to viewers — only the on-screen label changes. (Note: the
  per-slot connection list and labels now live in the plugin's Web UI
  settings / the sidecar fetcher config rather than as hardcoded enums —
  see the Phase 2 PII removal in `docs/AUDIT_2026-07-22.md`.)

## 2026-06-26

- Orchestration audit: confirmed the jen_morning switch at 06:45 BST
  on 2026-06-26 was the expected cascade behaviour of
  `trmnl_resolve_display_mode_v1`, not a bug. Source:
  `docs/TRMNL_ORCHESTRATION_AUDIT_2026-06-26.md`.
- Identified that `scripts/trmnl_set_display_mode.sh` on `khpi5`
  explicitly SSHes to the Pi and runs `sudo systemctl restart
  trmnl-display.service` at the end of every mode change. This is
  the actual cause of the 06:45:03 Pi service restart, not the
  systemd `morning-start.timer` (which fires 2-3 s earlier and is
  now redundant for the morning case). The timer is kept as a
  safety net for the night-stop recovery case.
- Verified `scripts/trmnl_set_display_mode.sh` in repo matches the
  live `/home/dave/bin/trmnl-set-display-mode` on `khpi5` (no diff;
  no sync required).
- Added live schedule reference: jen_morning 06:45–07:45 BST
  weekdays, bus 07:50–09:30, night ≥22:50 or <06:40, default
  weekday=`calendar`, default weekend=`ha_dashboard`, per-mode
  refresh intervals (`bus=600`, `sonos=60`, `jen_commute=420`,
  `jen_morning=600`, `calendar=7200`, `idle=7200`,
  `ha_dashboard=600`).
- Cross-referenced `docs/SOURCE_OF_TRUTH.md` managed surfaces with
  related deploy units and operational docs (added "Related docs /
  units" column).
- Documented "What wakes the Pi" in `docs/OPERATIONS.md` covering the
  dual SSH-restart + systemd-timer mechanism.
- Cross-linked `docs/HA_DISPLAY_ORCHESTRATION_PLAN.md` to the new
  audit doc for the live schedule reference.
- Filed as a follow-up (no change in this commit): gate the
  `trmnl_ha_dashboard_helper_change_refresh_v1` automation in
  `config/packages/trmnl_ha_dashboard.yaml` to only fire when
  `input_select.trmnl_display_mode == 'ha_dashboard'`.

## 2026-05-19

- Recorded a read-only live baseline: LaraPaper healthy on image label `0.34.0`, HA core check passing, mode bridge active, active playlist `ha_dashboard`, and Pi sidecar renders flowing as indexed `800x480` images prepared as `4-bpp`.
- Documented upstream LaraPaper `0.35.0` relevance: webhook `merge_strategy` support and the native fix for the recipe webhook route parameter patch.
- Updated plugin contract notes for TRMNL webhook `GET`, `deep_merge`, and `stream` usage.
- Updated live LaraPaper to `0.35.0` without pinning the compose image reference, after backing up compose, `.env`, and SQLite database files on `khpi5`.
- Verified post-update LaraPaper health, active `ha_dashboard` playlist, Home Assistant config check, playlist-safe sidecar refresh, local generated-image serving, and a forced Pi BYOS display refresh.
- Confirmed the recipe webhook route patch is no longer needed on `0.35.0`; reapplied the relative preview image URL patch.

## 2026-05-06

- Updated AGENTS.md with new architecture rule #9 formalising HA/LaraPaper playlist boundary, refreshed managed surfaces and validation commands.
- Fixed UK Bus Departures Liquid template variable binding: restored `{{timespan}}`, `{{atco}}`, `{{app_id}}`, `{{app_key}}` in polling URL so LaraPaper resolves them at poll time via `Plugin::resolveLiquidVariables()` instead of using hardcoded values.
- Added bus departure colour sidecar: `scripts/render_bus_departures.py` renders TransportAPI data as a full-screen 800x480 indexed 7-colour PNG with route-coloured badges and on-time/late status.
- Created `scripts/trmnl_update_bus_sidecar_image.sh` for playlist-safe sidecar handoff into LaraPaper generated-image storage.
- Created `scripts/trmnl_refresh_bus_sidecar.sh` as the combined refresh wrapper.
- Created `plugins/trmnl-bus-departures/` plugin contract (settings, schema, payload, README).
- Removed split-screen mashup from bus departures playlist item; bus now renders full-screen.
- Added calendar colour sidecar: 7-day week agenda view with per-calendar colour bars (BLUE=Dave, GREEN=Family, RED=Outlook), calendar name pills, and clean list layout. Fetches live via Nango OAuth proxy.

## 2026-05-02

- Added a HA dashboard plugin contract validator to catch drift between `settings.yml`, `fields.schema.json`, and `payload.example.json`.
- Added a colour dashboard validation script that renders default, card-type, generic, and hidden slot cases and enforces `800x480`, paletted seven-colour output.
- Documented the HA dashboard plugin's three installation modes: standard LaraPaper, Spectra colour sidecar, and optional local Home Assistant helper UI.
- Wired HA dashboard helper changes to the playlist-safe sidecar refresh endpoint with deliberate `force` refreshes so local slot edits propagate without waiting for the next scheduled cycle.
- Added an optional Home Assistant managed configuration facade for the HA colour dashboard slots, including helpers, a refresh button, and a Lovelace helper-view YAML source.
- Increased the HA colour sidecar card fill saturation so card backgrounds read more strongly on the physical Spectra panel while keeping seven-colour indexed output.
- Implemented configurable fixed card slots for the HA colour dashboard plugin contract, added `generic_entities`, and wired a playlist-safe `/ha-dashboard/refresh` endpoint with a 120-second cooldown for Sonos/media-triggered updates.
- Added a playlist-safe HA sidecar updater that refreshes the LaraPaper plugin image without activating playlists or overriding the device current image, and documented the dynamic card-slot roadmap.
- Reworked the HA colour sidecar grid to hide visible light cards, combine climate and humidity into one indoor card, and use the freed space for a wider home-status row.
- Refined the HA colour sidecar layout to remove the top bar, bottom navigation, and energy card, group people into one presence card, and dedicate the lower-right card to media.
- Updated the HA dashboard plugin contract, payload example, and docs so navigation and energy are no longer advertised as active fields in the current `compact_grid` sidecar layout.
- Expanded the HA dashboard plugin contract with configurable labels for sidecar cards, light cards, media/presence summaries, and bottom navigation.
- Improved the proof-style sidecar render so it avoids clipped metric titles, uses higher-contrast navigation labels, and shows honest empty-state text for unconfigured optional cards.
- Integrated the accepted HA colour sidecar back into LaraPaper BYOS delivery by handing off `sidecar_colour_dashboard_next.png` through LaraPaper's generated-image storage during `ha_dashboard` mode.
- Updated the `khpi5` HA dashboard cron so live payload pushes re-render the sidecar and refresh the handoff only when `ha_dashboard` is already active.
- Fixed the Pi display shell's shutdown trap so service restarts no longer wait for systemd to kill a sleeping process during sidecar verification.
- Made `scripts/tmp/sidecar_colour_dashboard_proof_2026-05-01.png` the tracked canonical colour-dashboard visual reference and documented that the muted LaraPaper-style render is not the target design.
- Restored `scripts/render_colour_dashboard.py` to the accepted proof-style icon/card layout while keeping TRMNL `merge_variables` payload input and writing non-overwriting `*_next.png` iteration files.
- Extended the HA dashboard plugin contract and companion payload writer with optional light and energy fields for the proof-style card surfaces.
- Aligned the HA dashboard colour sidecar with the plugin payload contract by rendering from TRMNL `merge_variables` JSON instead of static proof data.
- Updated the HA dashboard companion payload to include plugin fields and configurable entity IDs via `/home/dave/.env.trmnl-ha-dashboard`.
- Added a khpi5 environment example and documented local/live sidecar payload rendering.
- Added an explicit blind open-position setting so inverted cover controllers do not require hardcoded renderer logic.
- Restored the colour sidecar to the compact icon-led dashboard layout with solid seven-colour panel fills.

## 2026-05-01

- Documented the TRMNL BYOS colour-renderer audit, including Terminus, LaraPaper, BYOS Next, Node Lite, and the official ImageMagick guidance.
- Added and hardware-tested a quick seven-colour sidecar dashboard renderer for the Inky/Spectra panel.
- Locked in the colour sidecar as the preferred path forward for colour-critical dashboard rendering.
- Added mandatory plugin/recipe portability rules and expanded the HA dashboard plugin field/payload contract.
