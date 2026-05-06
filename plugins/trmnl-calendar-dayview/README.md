# Calendar Day View

Today's events from all connected Nango calendars, rendered as a colour-coded day timeline for the TRMNL display.

Each calendar gets its own colour accent bar. Events are shown on a 06:00-23:00 timeline with coloured bars, titles, times, and locations.

## Data Source

The sidecar fetches events via the Nango proxy API. Configured connections:

| Calendar | Colour |
|---|---|
| Dave (Google) | Blue |
| Family (Google) | Green |
| Outlook | Red |
| Birthdays | Yellow |

## Files

| File | Purpose |
|---|---|
| `scripts/render_calendar_dayview.py` | Timeline renderer |
| `scripts/nango_calendar_fetch.py` | Nango API fetcher |
| `plugins/trmnl-calendar-dayview/settings.yml` | Plugin config |
| `plugins/trmnl-calendar-dayview/fields.schema.json` | Sidecar schema |
| `plugins/trmnl-calendar-dayview/payload.example.json` | Example payload |

## Usage

```bash
# Render from example payload
python3 scripts/render_calendar_dayview.py --payload plugins/trmnl-calendar-dayview/payload.example.json

# Fetch live and render (requires NANGO_SECRET_KEY env var)
python3 scripts/render_calendar_dayview.py
```
