# TRMNL Jen Commute

HA-driven Jen commute screen for LaraPaper/TRMNL BYOS.

This recipe is designed to receive webhook payloads from Home Assistant containing commute, route, and home-prep context.

Recipe files:
- `plugins/trmnl-jen-commute/settings.yml`
- `plugins/trmnl-jen-commute/full.liquid`

Expected payload fields:
- required:
  - `updated_at`
  - `headline`
  - `eta_minutes`
  - `route_label`
  - `commute_state`
  - `heading_home`
- optional:
  - `distance_km`
  - `home_prep_status`
  - `prep_note`
  - `map_url`
  - `quote_text`
  - `quote_source`

Example payload:

```json
{
  "merge_variables": {
    "updated_at": "30 Mar 08:10",
    "headline": "Heading Home",
    "eta_minutes": "27",
    "route_label": "Direct",
    "distance_km": "10.4",
    "commute_state": "journey_started",
    "heading_home": "Yes",
    "home_prep_status": "Needed",
    "prep_note": "Heating or home prep would help before arrival.",
    "map_url": "https://www.google.com/maps/dir/?api=1&origin=A&destination=B&travelmode=driving",
    "quote_text": "Happiness can be found, even in the darkest of times.",
    "quote_source": "Albus Dumbledore"
  }
}
```

Notes:
- This is intended as a shareable webhook recipe, with Home Assistant acting as the orchestration/data source.
- Keep user-facing options in `settings.yml` and HA-specific decision logic on the Home Assistant side.
- The recipe should stay generic: only the small screen label should be personalized. The payload contract itself should remain reusable for any commute-style screen.
- A good Home Assistant implementation may either switch this screen only for active commute context, or use a configurable morning time window for a predictable "time to work" screen.
