# TRMNL Jen Morning

Scheduled morning commute screen for LaraPaper/TRMNL BYOS.

This recipe is intended for a predictable weekday morning window such as `07:00-07:30`.
It is separate from the main Jen commute automation/state machine and should not alter that logic.

Recipe files:
- `plugins/trmnl-jen-morning/settings.yml`
- `plugins/trmnl-jen-morning/full.liquid`

Expected payload fields:
- required:
  - `updated_at`
  - `headline`
  - `eta_minutes`
  - `route_label`
- optional:
  - `distance_km`
  - `quote_text`
  - `quote_source`

Example payload:

```json
{
  "merge_variables": {
    "updated_at": "30 Mar 07:10",
    "headline": "Time To Work",
    "eta_minutes": "42",
    "route_label": "Woollard Ln",
    "distance_km": "29.4",
    "quote_text": "Happiness can be found, even in the darkest of times.",
    "quote_source": "Albus Dumbledore"
  }
}
```

Notes:
- This is a separate morning screen, not a replacement for the main `Jen Commute` recipe.
- The intended Home Assistant pattern is: a dedicated TRMNL package pushes payloads and temporarily sets a TRMNL manual override during the configured morning window.
