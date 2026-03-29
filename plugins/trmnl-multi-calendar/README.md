# TRMNL Multi-Calendar

Webhook-driven TRMNL/LaraPaper recipe for merging up to 6 calendar feeds into one display.

This package contains the shareable recipe side:
- `settings.yml` - importable plugin schema
- `full.liquid` - current working layout

The companion sync script lives at `scripts/trmnl_calendar_multi.py` and is responsible for:
- fetching ICS feeds
- applying labels and colors per source
- merging events into one payload
- POSTing to the LaraPaper webhook endpoint

## Current Capabilities

- up to 6 calendar sources
- per-calendar label
- per-calendar color
- optional per-calendar custom color text
- optional per-calendar HTTP headers for authenticated ICS feeds
- 3 / 7 / 14 day windows
- 12h / 24h support
- hide empty days
- show/hide all-day events
- show/hide calendar labels
- max events per day

## Color Model

The recipe supports both:
- curated named colors for predictable ACeP e-ink rendering: `black`, `red`, `blue`, `green`, `yellow`, `orange`
- optional custom text colors for future/non-ACeP use

## Provider Setup

### Google Calendar

1. Open Google Calendar on desktop.
2. Go to `Settings` -> your calendar -> `Integrate calendar`.
3. Copy `Secret address in iCal format`.
4. Paste that into `TRMNL_CALn_URL`.

Notes:
- this is read-only
- treat the URL like a secret
- if exposed, reset it in Google

### Apple / iCloud Calendar

1. Open iCloud Calendar on desktop.
2. Open the calendar sharing/info menu.
3. Enable `Public Calendar`.
4. Copy the generated public link.
5. Convert `webcal://` to `https://` if needed.

Notes:
- public sharing is required for a simple ICS URL
- private Apple sharing is not suitable for this basic webhook flow

### Outlook.com / Outlook on the web

1. In Outlook Calendar choose `Add calendar`.
2. Use `Subscribe from web` if you are consuming another ICS feed, or share/export your own calendar where available.
3. Use the published ICS/web URL in `TRMNL_CALn_URL`.

Notes:
- Outlook subscription refresh may lag significantly
- imported `.ics` files are snapshots and do not auto-refresh

### Generic CalDAV / ICS

Use any published ICS endpoint. If authentication headers are required, provide them as:

`authorization=Bearer xxx&content-type=application/json`

in `TRMNL_CALn_HEADERS`.

## Example `.env`

```env
TRMNL_WEBHOOK_URL=http://localhost:4567/api/custom_plugins/YOUR-UUID
TRMNL_TITLE=Calendar
TRMNL_TZ=Europe/London
TRMNL_DAYS=7
TRMNL_TIME_FORMAT=%H:%M
TRMNL_TIME_MODE=24h
TRMNL_SHOW_SOURCE_LABELS=true
TRMNL_SHOW_ALL_DAY_EVENTS=true
TRMNL_HIDE_EMPTY_DAYS=true
TRMNL_MAX_EVENTS_PER_DAY=6
TRMNL_NUMBER_COLUMNS=4

TRMNL_CAL1_ENABLED=true
TRMNL_CAL1_LABEL=Calendar A
TRMNL_CAL1_COLOR=blue
TRMNL_CAL1_URL=https://calendar.google.com/calendar/ical/.../basic.ics

TRMNL_CAL2_ENABLED=true
TRMNL_CAL2_LABEL=Calendar B
TRMNL_CAL2_COLOR=red
TRMNL_CAL2_URL=https://calendar.google.com/calendar/ical/.../basic.ics
```

## Validation Workflow

After every change:

1. Run the sync script manually on `khpi5`.
2. Confirm the webhook returns HTTP 200.
3. Confirm LaraPaper serves a fresh `/api/display` image.
4. Refresh `trmnl-display.service` on `inky-pi`.
5. Verify the physical screen updates correctly.
