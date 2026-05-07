# Calendar Week Ahead

7-day week agenda view for the TRMNL/LaraPaper BYOS display. Shows upcoming events from Nango-connected calendars (Google, Outlook) in a colour-coded list. Each calendar gets its own coloured accent bar and pill label. Only days with events are shown.

## Data Sources

The sidecar fetches events via Nango OAuth proxy. Each connected calendar uses a distinct panel colour:

| Source | Colour |
|---|---|
| REDACTED@example.com | Blue |
| REDACTED@example.com | Green |
| REDACTED@example.com | Red |
| Outlook Calendar | Orange |

## Installation

Standard LaraPaper webhook plugin. Create a webhook plugin named "Calendar Week Ahead" and configure the Nango secret key.

## Payload Format

The renderer expects a JSON payload with this shape:

```json
{
  "today": "2026-05-07",
  "days": [
    {
      "date": "2026-05-07",
      "day_name": "Thursday",
      "calendars": [
        {
          "name": "REDACTED-CONNECTION",
          "color": [0, 0, 255],
          "events": [
            {
              "summary": "Event title",
              "start": "2026-05-07T14:45:00+01:00",
              "end": "2026-05-07T15:45:00+01:00",
              "all_day": false,
              "location": "Venue"
            }
          ]
        }
      ]
    }
  ]
}
```

## Files

| File | Purpose |
|---|---|
| `scripts/render_calendar_dayview.py` | 7-day week agenda renderer |
| `scripts/nango_calendar_fetch.py` | Nango API fetcher for all connected calendars |
| `scripts/trmnl_update_calendar_sidecar_image.sh` | Playlist-safe handoff into LaraPaper |
| `scripts/trmnl_refresh_calendar_sidecar.sh` | Combined fetch-render-handoff wrapper |
| `plugins/trmnl-calendar-dayview/settings.yml` | Plugin configuration |
| `plugins/trmnl-calendar-dayview/fields.schema.json` | Sidecar field schema |
| `plugins/trmnl-calendar-dayview/payload.example.json` | Example payload |
