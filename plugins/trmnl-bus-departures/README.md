# UK Bus Departures (TransportAPI)

Real-time UK bus departure board for TRMNL/LaraPaper BYOS, with optional repo-owned colour sidecar for improved indexed-colour rendering on Spectra/ACeP panels.

## Installation Modes

### Standard LaraPaper (polling recipe)

Uses TransportAPI polling URL with Liquid template variables. Configure via LaraPaper:

- **ATCO Code** — the bus stop ATCO code
- **Timespan** — how many hours ahead to fetch departures
- **TransportAPI App ID & API Key** — your TransportAPI credentials
- **Stop Display Name** — friendly name for the colour sidecar

The Liquid template in `polling_url` uses `{{atco}}`, `{{timespan}}`, `{{app_id}}`, `{{app_key}}` variables.

### Spectra Colour Sidecar

For improved 7-colour indexed rendering on the Pimoroni Inky Impression 7.3 / Spectra-class panel:

1. Ensure LaraPaper's bus plugin is configured and polling successfully.
2. Run the colour sidecar renderer and handoff:

```bash
/home/dave/bin/trmnl-refresh-bus-sidecar
```

This will:
- Force a fresh data poll via LaraPaper
- Render a full 800x480 7-colour indexed PNG
- Install it into LaraPaper's generated-image storage as the bus plugin's `current_image`
- The Pi displays it on its next poll cycle

## Colour Sidecar Architecture

```
LaraPaper polling  →  data_payload in DB  →  render_bus_departures.py  →  7-colour indexed PNG
                                                                              ↓
Pi display  ←  LaraPaper /api/display  ←  trmnl_update_bus_sidecar_image.sh  ←
```

The sidecar reads TransportAPI data from LaraPaper's plugin data payload, renders a colour-optimised departure board, and hands it back to LaraPaper as a plugin image — the Pi remains a thin BYOS client.

## Expected Logs

```
image specs: 800 x 480, 8-bpp
Preparing image for EPD as 4-bpp
Refresh complete
```

## Files

| File | Purpose |
|---|---|
| `scripts/render_bus_departures.py` | Colour sidecar renderer |
| `scripts/trmnl_update_bus_sidecar_image.sh` | Handoff script (docker cp + PHP DB update) |
| `scripts/trmnl_refresh_bus_sidecar.sh` | Combined refresh wrapper |
| `plugins/trmnl-bus-departures/settings.yml` | Plugin configuration fields |
| `plugins/trmnl-bus-departures/fields.schema.json` | Sidecar field schema |
| `plugins/trmnl-bus-departures/payload.example.json` | Example payload |
