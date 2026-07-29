# Plan — Plugin Conformance, Settings Wiring & Modes

Date: 2026-07-29 · Status: ACTIVE (checkboxes updated as work lands)

## Intent

Make every plugin in this repo (a) **conform** to the official TRMNL/LaraPaper
field schema and plugin contract, and (b) **genuinely configurable** — every
user-facing field in the Web UI must be understandable and must actually drive
what renders. No decorative fields, no hardcoded local values in reusable
logic, no spec violations. Then build the new display modes from
`docs/HOMELAB_DISPLAY_ROADMAP.md`.

## Constraints (binding — from `DECISIONS.md` + `docs/PLUGIN_RECIPE_CONTRACT.md`)

- Flat plugin layout (settings.yml + liquids at plugin root), official
  `custom_fields` schema, `merge_variables`, no PII anywhere.
- Sidecars read settings from plugin payload/DB config first, env as fallback;
  never hardcode entity ids, labels, URLs, room names, or personal specifics.
- Repo-first changes; **live display must not regress** — settings.yml and
  renderer changes are validated offline (config-empty → env fallback →
  byte-identical to today) and only touch live when a render is proven equal.
- Commit per plugin (or per coherent chunk), update this doc's checkboxes as
  each lands, push at the end of the workstream.
- Field schema reference: official TRMNL custom-plugin form builder
  (types: `string, multi_string, text, code, number, password, date, time,
  select, xhrSelect, xhrSelectSearch, plugin_instance_select, time_zone,
  copyable, copyable_webhook_url, boolean, lat_lon, url, author_bio`; required
  keys: `keyname, name, field_type`; `select.default` must equal an option
  *value*; `options` only on `select`).

## Workstream A — Plugin field conformance + settings wiring (active)

### A1. Spec violations (settings.yml) — repo-only, no live impact

| Plugin | Violation | Fix | Done |
|---|---|---|---|
| trmnl-hp-quotes | `checkbox` (not an official type) x2 | → `boolean`, default `true` | [x] |
| trmnl-hp-quotes | dead `theme` field (unused by renderer) | remove field | [x] |
| trmnl-hp-quotes | `layout_mode`/`house_accent` as free `text` | → `select` with renderer-verified values | [x] |
| trmnl-hp-quotes | top-level `author: David` (PII, non-standard) | remove; `author_bio` field, generic | [x] |
| trmnl-bus-departures | `timespan` = `number` carrying `options` (a `select` trait) | → `select`, default `2` (value) | [x] |
| trmnl-bus-departures | `atco` default is a specific local stop | default `""`, placeholder example | [x] |

### A2. Usability pass (all plugins) — repo-only

- Every free-text credential/ID/URL gets `placeholder` + `help_text`
  (where to find the value).
- Long forms (`trmnl-ha-dashboard`, `trmnl-multi-calendar`,
  `trmnl-calendar-dayview`) get `group` accordions per official guidance.
- Personal-name defaults → generic (`Jen Commute` → `Commute`,
  `Jen Morning` → `Morning Commute`, `Jen Coming Home` → `Coming Home`).
- `lat_lon` field type for location inputs (coming-home work anchor +
  waypoint label becomes a `string` field); names/descriptions reviewed.

### A3. Settings-wiring audit + fixes — per renderer, offline-validated

Rule: each renderer must resolve user-facing settings as
`plugin config (DB configuration) → payload field → env → neutral default`.

| Renderer | Current source of user settings | Verdict | Fix | Done |
|---|---|---|---|---|
| render_jen_commute.py | DB `configuration` (SELECT data_payload, configuration) | reads config — OK | none | [x] verified |
| render_morning_mashup.py | DB `configuration` | reads config — OK | none | [x] verified |
| render_jen_coming_home.py | payload only (`data_payload`) | **disconnected** — `show_home_prep` toggle + work anchor not config-driven | read `configuration` for plugin 28; config-first, env fallback | [x] |
| render_hp_quotes.py | payload only (`data.get(...)`) | **disconnected** — layout/house/banner/book not config-driven | verify if morning-mashup passes config; add config read if needed | [ ] |
| render_bus_departures.py | polling model | settings used by LaraPaper polling (connected); sidecar `stop_name` from payload — OK | none | [x] verified |
| render_sonos_sidecar.py | payload from push (push uses env, not config) | **disconnected** — preferred_room, art mode, toggles not config-driven | push or render reads config; config-first, env fallback | [ ] |
| render_calendar_dayview.py | fetcher reads config → payload carries theme/layout | **connected** (config → fetcher → payload → render) | none | [x] verified |
| render_colour_dashboard.py | HA helpers (input_text/input_select) | **connected via HA** (architectural decision: HA helpers are the live config layer for this house-specific dashboard; plugin Web-UI fields serve as documentation/portability contract) | document the boundary; no code fix needed | [x] documented |

### A4. Calendar connection selection

`calendar_N_connection_id` stays free-text now (with strong help_text:
"paste the Nango connection id from your Nango instance → Connections").
Ideal future: `xhrSelect` populated from a Nango-connections endpoint on the
mode bridge. **Deferred** to follow-up — needs a new bridge endpoint +
restart; not part of A1–A3.

### A5. Domain placeholders

Replace `trmnl.magnusfamily.co.uk` (docs) and `caldav.spacemail.com` default
(fire_calendar_fetch.py → env-driven `CALDAV_SERVER_URL`) with placeholders.
Must first confirm `CALDAV_SERVER_URL` is set in live `.env.spacemail`, or add
it (host-only, no repo value).

### A6. Validation + docs + push

- `py_compile` all touched scripts; YAML parse all touched settings.yml;
  `trmnlp lint` (advisory CI) on touched plugins; offline render equality
  check for any renderer touched (config-empty fallback == current output).
- Update `docs/OPERATIONS.md` (wiring rule), `docs/PLUGIN_RECIPE_CONTRACT.md`
  if contract wording changes, `DECISIONS.md` for any settled/reversed
  decision. Then push.

## Workstream B — New modes (after A, per `docs/HOMELAB_DISPLAY_ROADMAP.md`)

B1. Beszel/universalcron → Alert wiring (~1d). B2. Homelab Health mode (~2-3d).
B3. Backups freshness tile (fold into B2). B4. Fun modes (~1d each: bins,
energy, WAN, tracker, Sunday week-view). B5. Night low-refresh layout +
weekend default choice (config only). Each follows the mode recipe in the
roadmap doc; each gets its own plugin dir, sidecar renderer, wrapper, cron,
resolver entry, playlist, and Web-UI validation. Build order: B1 → B2 → rest.

## Rollback

- settings.yml: `git checkout <file>`; redeploy nothing (live untouched).
- renderer changes: offline render must equal current output before any live
  deploy; if live output ever differs, restore from git and re-render.
