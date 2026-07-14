# Calendar Week Ahead

7-day week agenda view for the TRMNL/LaraPaper BYOS display. Shows upcoming events from Nango-connected calendars (Google, Outlook) in a colour-coded list. Each calendar gets its own coloured accent bar and pill label. Only days with events are shown.

## Data Sources

Events are fetched through a Nango OAuth proxy (`nango_base_url` and `nango_secret_key` in the plugin settings). The fetcher supports up to **twelve calendar slots**; each slot binds one Nango connection to the display and is independent of the others:

| Slot field | Purpose |
|---|---|
| `calendar_N_connection_id` | Nango connection id. Empty / `Disabled` skips the slot. |
| `calendar_N_calendar_id` | Optional sub-calendar id. Defaults to the account's primary (Google) or default (Outlook) calendar. |
| `calendar_N_label` | Pill label shown on screen. |
| `calendar_N_color` | Accent colour: `blue`, `red`, `green`, `yellow`, `orange`, or `black`. |
| `calendar_N_color_custom` | Optional hex / CSS override. |

Several slots may point at the same Nango connection with different sub-calendars — for example an account's primary calendar, a shared family calendar, and the provider's auto-generated "Birthdays" aggregate can each be their own slot. Any feed the operator does not want on screen (e.g. a provider's built-in "Holidays in United Kingdom" sub-calendar) is simply left unslotted or set to `Disabled`.

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
