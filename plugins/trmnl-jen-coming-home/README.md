# TRMNL Jen Coming Home

Bold colour screen for **Jen's evening commute home from work** on the LaraPaper /
TRMNL BYOS stack. Makes the Work → Home journey the hero: where Jen is, how far,
when she's home, and whether the house needs prep before she's back.

This is distinct from the morning (TO-work) screen (`trmnl-jen-morning`) — do not
conflate the two.

> **Rendering path (official exception).** This plugin ships **no Liquid screen template**. The on-screen image is produced by the repo's indexed-colour sidecar (`scripts/render_jen_coming_home.py`) and installed into LaraPaper via its **generated-image / image-webhook handoff** — an official LaraPaper screen-generation mechanism (LaraPaper supports Screenshot / Image Webhook / API rendering alongside recipe Liquid). The official TRMNL Liquid/CSS design system targets the 800×480 2-bit grayscale panel, so the colour sidecar is a deliberate BYOS extension for the 6/7-colour ACeP Spectra panel. The plugin stays fully configurable through `settings.yml` and the documented `merge_variables` payload; the sidecar reads the same contract, not hardcoded values. See `docs/PLUGIN_RECIPE_CONTRACT.md`.

**Portability note.** The commute origin used for the work→home progress indicator is read from the `TRMNL_WORK_ANCHOR` environment variable (`latitude,longitude`) on the host running the renderer; it is intentionally not stored in source.

## How it fits together

- **Plugin**: LaraPaper webhook custom plugin `Jen Coming Home` (id 28,
  `data_strategy=webhook`). Receives the commute payload from Home Assistant.
- **Image**: rendered by [`scripts/render_jen_coming_home.py`](../../scripts/render_jen_coming_home.py)
  into the indexed 6-colour sidecar `sidecar_jen_coming_home_next.png`.
- **Refresh**: [`scripts/trmnl_refresh_jen_coming_home_sidecar.sh`](../../scripts/trmnl_refresh_jen_coming_home_sidecar.sh)
  (cron `*/2`, and on `jen_commute` mode activation). Renders from the plugin's
  live `data_payload` and hands the image to the BYOS device.
- **Mode**: rides on the existing `jen_commute` display mode (the "coming home"
  mode in Home Assistant). `trmnl_set_display_mode.sh` maps `jen_commute` →
  `Jen Coming Home`.
- **Data**: Home Assistant `rest_command.trmnl_jen_commute_push` posts Waze /
  `person.<your_person_entity>` data to this plugin's webhook; the automation only claims the
  display while a commute is actually active.

## Webhook contract

POST `http://<larapaper>:4567/api/custom_plugins/<uuid>` with:

```json
{
  "merge_variables": {
    "updated_at": "22 Jun 18:05",
    "headline": "Heading Home",
    "eta_minutes": 23,
    "route_label": "A4 via Keynsham Bypass",
    "distance_km": 12.6,
    "commute_state": "journey_started",
    "heading_home": "Yes",
    "home_prep_status": "Needed",
    "prep_note": "Heating or home prep would help before arrival.",
    "map_url": "https://www.google.com/maps/dir/?api=1&origin=A&destination=B&travelmode=driving"
  }
}
```

Fields:
- required: `eta_minutes`, `route_label`, `commute_state`, `heading_home`
- optional: `headline`, `updated_at`, `distance_km`, `home_prep_status`, `prep_note`, `map_url`

`commute_state` of `via_clean_bean` highlights a configured waypoint on the route
(the label comes from the upstream payload/automation, not hardcoded here).
`home_prep_status` of `Active` / `Needed` / `Not Needed` drives the footer prep card colour.
