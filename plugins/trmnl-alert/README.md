# TRMNL Alert

Generic webhook-driven alert screen for LaraPaper/TRMNL BYOS.

This recipe is intended to be reusable across Home Assistant alert sources. Keep
the payload generic and let Home Assistant decide when the alert mode should be active.

Recipe files:
- `plugins/trmnl-alert/settings.yml`
- `plugins/trmnl-alert/full.liquid`

Expected payload fields:
- required:
  - `updated_at`
  - `title`
  - `message`
- optional:
  - `severity`
  - `footer`

Example payload:

```json
{
  "merge_variables": {
    "updated_at": "30 Mar 09:05",
    "title": "Front Door Open",
    "message": "The front door has been open for more than 5 minutes.",
    "severity": "high",
    "footer": "Home Assistant alert"
  }
}
```

Notes:
- This is a display recipe, not an alert engine.
- Home Assistant should decide when the alert is active, how long it should remain on screen, and what payload it should send.
- Keep the alert payload simple so the recipe remains exportable and reusable.
