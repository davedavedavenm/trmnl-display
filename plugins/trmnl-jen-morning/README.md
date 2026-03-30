# TRMNL Jen Morning

Scheduled morning commute screen for LaraPaper/TRMNL BYOS.

This recipe is intended for a predictable weekday morning window such as `07:00-07:30`.
It is separate from the main Jen commute automation/state machine and should not alter that logic.
It is designed to work either as a standalone morning screen or as the left side of a LaraPaper mashup.

Recipe files:
- `plugins/trmnl-jen-morning/settings.yml`
- `plugins/trmnl-jen-morning/full.liquid`
- `plugins/trmnl-jen-morning/half_vertical.liquid`

Expected payload fields:
- required:
  - `updated_at`
  - `headline`
  - `eta_minutes`
  - `route_label`
- optional:
  - `distance_km`

Example payload:

```json
{
  "merge_variables": {
    "updated_at": "30 Mar 07:10",
    "headline": "Time To Work",
    "eta_minutes": "42",
    "route_label": "Woollard Ln",
    "distance_km": "29.4"
  }
}
```

User-editable settings:
- `Layout Variant`: switch between `Editorial` and `Structured`
- `Screen Label`: small chip above the headline
- `Headline Fallback`: used if the webhook payload omits `headline`
- `Theme`: light or dark
- `ETA Label`: small label above the ETA number
- `ETA Unit Label`: text beside or below the ETA number
- `Route Label`: small label above the route name
- `Show Distance`: hides or shows distance when present in the payload
- `Distance Unit`: suffix used when rendering distance

Suggested LaraPaper setup:
1. Create the `Jen Morning` custom plugin from this folder.
2. Point a webhook sender such as Home Assistant at the plugin's custom-plugin endpoint.
3. For the split-screen version, create a LaraPaper mashup playlist item using:
   - `Jen Morning` on the left
   - a quote recipe such as `Potter Quotes` on the right
   - layout `1Lx1R`
4. For the currently used playlist-level wiring, see `docs/JEN_MORNING_MASHUP.md` and `scripts/larapaper_manage_mashup.sh`.

Notes:
- This is a separate morning screen, not a replacement for the main `Jen Commute` recipe.
- The intended Home Assistant pattern is: a dedicated TRMNL package pushes payloads and temporarily sets a TRMNL manual override during the configured morning window.
- The intended quote/content split should come from a LaraPaper mashup with a separate quote recipe, not from embedding quotes inside this plugin.
- Keep the recipe reusable by leaving commute-specific decision logic in Home Assistant or another upstream orchestrator. The plugin should stay focused on presentation and small user-configurable labels.
- LaraPaper standalone preview renders the plugin `full` layout, while the live split-screen playlist renders `half_vertical`. They should now share the same visual family and settings, but they will not be pixel-identical because they are different layout sizes.
