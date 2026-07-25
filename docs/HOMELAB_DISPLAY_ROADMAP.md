# Homelab Display Roadmap

Date: 2026-07-25

Planned modes and improvements for the TRMNL/Spectra display, ordered by
value-vs-effort. Everything here must obey the existing contracts:

- Plugins stay shareable: official `settings.yml` schema, `merge_variables`,
  no PII, fields configurable via the LaraPaper Web UI (see
  `docs/PLUGIN_RECIPE_CONTRACT.md`).
- Colour stays ACeP: 800x480 indexed palette, black outlines, deliberate
  6/7-colour use (see `docs/COLOUR_SIDECAR_PATH.md`).
- Architecture rules: HA orchestrates (mode selection), LaraPaper playlists
  decide when content cycles, the Pi is a thin BYOS client, sidecars render
  colour-critical output. New modes follow the existing mode recipe; they do
  not bypass the playlist system.

## The mode recipe (checklist for every new mode)

Every mode in this roadmap is built the same proven way:

1. `plugins/<name>/settings.yml` + `README.md` (+ `full.liquid` only if it
   renders through Liquid; colour sidecar plugins are exempt with a documented
   generated-image handoff note).
2. A sidecar renderer `scripts/render_<name>.py` producing an 800x480
   indexed PNG to `tmp/sidecar_<name>_next.png`.
3. A wrapper `scripts/trmnl_refresh_<name>_sidecar.sh` (mode-gated) that
   renders + hands off to LaraPaper **without** touching
   `devices.current_screen_image` (the reconciler owns that).
4. A cron entry on `khpi5`.
5. A `input_select` option + resolver variable in
   `config/packages/trmnl_display_orchestration.yaml` (priority order).
6. A LaraPaper playlist `TRMNL Mode: <name>` with the plugin as its active
   item, and a mode mapping in the mode bridge / `trmnl-set-display-mode`.
7. Web-UI validation: `trmnlp lint` (advisory CI), a direct `show_img.bin`
   hardware proof, then BYOS polling.
8. Commit repo, deploy, verify Web UI == panel (reconciler keeps them equal).

## Phase 1 — Wire real incidents into Alert mode (smallest change, high value)

The `alert` mode, playlist, and `trmnl_set_alert` script already exist but are
almost never used. Make them earn their place.

- Feed Beszel long-down watch (`run_beszel_long_down_watch.sh`) and the
  universalcron notify-spool into `trmnl_set_alert` so genuine outages
  pre-empt the display automatically (alert is highest priority in the
  resolver already).
- Severity mapping: down>30m = critical, flapping/degraded = high, info = low.
- Auto-clear when the watcher recovers, so the display returns to normal mode.
- Effort: ~1 day. No new renderer needed (alert plugin + sidecar exist).

## Phase 2 — Homelab Health mode (biggest daily value)

A colour-coded status board of the whole homelab, replacing or complementing
the HA house dashboard in some windows.

Data sources (all already running):

- Beszel long-down watch reports (host up/down states)
- Proxmox hosts/VMs up/down (qm/pct status)
- khpi5 Docker container health (`docker ps` states)
- Disk guard free-space report
- Pangolin/reverse-proxy reachability
- trmnl-pi uptime/battery/RSSI (from `/api/display` headers or ssh)

Renderer: tile grid, one tile per check, colour-coded green/yellow/red with
black outlines. Name: `trmnl-homelab-health`. Playlist
`TRMNL Mode: homelab_health`. Resolver: high priority behind alert when any
check is red; otherwise opt-in via manual override or a scheduled window.

- Effort: ~2-3 days (fetcher + renderer + resolver wiring).
- Portability: all thresholds/hosts in Web-UI fields; a generic default
  profile so others can reuse it.

## Phase 3 — Backups & freshness (small add-on)

- Last-backup age + integrity for the compose snapshot / restic jobs and the
  LaraPaper DB backup cron. Red tile if a backup is older than its SLA.
- Could be a tile inside Homelab Health rather than its own mode. Decide in
  Phase 2 design.

## Phase 4 — Fun/practical modes (as appetite allows)

Each follows the mode recipe, ~1 day each:

- **Bin-collection reminders** — colour = bin colour; weekly schedule source
  (ICS or HA sensor).
- **Energy/Octopus** — tariff + current usage vs cheap windows.
- **WAN quality** — periodic speedtest/latency strip chart.
- **Ship/flight tracker** — local area traffic; shows off the palette and
  dithered orange.
- **Weekly-at-a-glance Sunday mode** — extended calendar view (week strip
  layout already exists in the renderer) shown on Sundays.

## Phase 5 — Policy tweaks (config only)

- **Low-refresh night layout** — during 22:50-06:40, a minimal status/clock
  layout with fewer EPD refreshes (night window already exists in the resolver).
- **Weekend default mode choice** — keep `ha_dashboard` or switch weekend
  default to `homelab_health` once Phase 2 lands (one input_select initial).

## Notes

- No mode here should change the display's update cadence without checking
  the playlist `refresh_time` against panel wear (e-ink longevity).
- Every new plugin gets a CI lint pass automatically via the existing
  `.github/workflows/trmnl-lint.yml`.
