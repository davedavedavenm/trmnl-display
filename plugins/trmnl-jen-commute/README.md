# TRMNL Jen Commute

HA-driven Jen commute screen for LaraPaper/TRMNL BYOS.

This recipe is designed to receive webhook payloads from Home Assistant containing commute, route, and home-prep context.

Recipe files:
- `plugins/trmnl-jen-commute/settings.yml`
- `plugins/trmnl-jen-commute/full.liquid`

Expected payload fields:
- `updated_at`
- `headline`
- `eta_minutes`
- `route_label`
- `distance_km`
- `commute_state`
- `heading_home`
- `home_prep_status`
- `prep_note`
- `map_url`

Notes:
- This is intended as a shareable webhook recipe, with Home Assistant acting as the orchestration/data source.
- Keep user-facing options in `settings.yml` and HA-specific decision logic on the Home Assistant side.
