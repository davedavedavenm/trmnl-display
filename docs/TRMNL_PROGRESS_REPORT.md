# TRMNL Integration: Progress Report

## Accomplishments to Date

### 1. Documentation Deep-Dive
- Audited official TRMNL BYOD and BYOS documentation.
- Analyzed the TRMNL Private API (/api/display) for image rendering and refresh cycles.
- Reviewed the trmnl-display Go client architecture.

### 2. Hardware Audit
- **Confirmed Device:** Pimoroni Inky Impression 7.3" (800x480).
- **Driver Verification:** Confirmed that trmnl-display has explicit built-in support for this specific hardware via the Spectra 7.3" driver.
- **Refresh Optimization:** Identified that TRMNL's zero-flicker and 4-level grayscale hacking are compatible with this Waveshare-based panel.

### 3. Migration Strategy
- Authored and pushed docs/TRMNL_INTEGRATION_PLAN.md to GitHub.
- Defined a phased approach: Hardware PoC -> Local BYOS -> Plugin Migration.

### 4. Local Environment Setup (On Pi)
- **Mock Server:** Deployed scripts/trmnl_mock_server.py on the Raspberry Pi to simulate the TRMNL backend locally.
- **Client Build:** Successfully cloned and compiled the official trmnl-display Go client on the device.
- **API Validation:** Successfully verified that the Go client can fetch images from the local mock server (Status 200).

### 5. Hardware PoC - COMPLETE
- **Physical screen render confirmed:** `show_img` binary successfully drives the Inky Impression 7.3" via SPI.
- **No permissions issues:** User `dave` already has spi/gpio/i2c group membership. No sudo required.
- **Go client pipeline verified:** trmnl-display -> show_img -> EPD works end-to-end.

### 6. BYOS Server - COMPLETE
- **Evaluated usetrmnl/byos_fastapi:** Too heavy for Pi (requires Chromium, 100MB+ RAM, heavy deps like d3blocks/html2image).
- **Built lightweight BYOS server:** `scripts/trmnl_byos_server.py` - Flask-based, ~30MB RAM, runs on port 4567.
- **Endpoints:** `/api/display`, `/api/setup`, `/api/log`, `/api/config`, `/health`, `/images/<filename>`.
- **Auto-cleanup:** Rotates generated images, keeps last 10.
- **Configurable:** `config.json` for refresh rate, timezone, playlist.

### 7. Systemd Services - COMPLETE
- **trmnl-byos.service:** Runs the BYOS server, enabled at boot.
- **trmnl-display.service:** Runs the Go client, depends on BYOS server, enabled at boot.
- Both services auto-restart on failure.

## Architecture

```
[Systemd: trmnl-display.service]
         |
         | polls every 300s (configurable)
         v
[Systemd: trmnl-byos.service] :4567
         |
         | GET /api/display -> {image_url, filename, refresh_rate}
         v
   [show_img] -> SPI -> [Inky Impression 7.3" EPD]
```

## File Locations on Pi

| Component | Path |
|---|---|
| BYOS Server | `/home/dave/trmnl-byos/server.py` |
| BYOS Config | `/home/dave/trmnl-byos/config.json` |
| BYOS Images | `/home/dave/trmnl-byos/images/` |
| Go Client | `/home/dave/trmnl-display/trmnl-display` |
| show_img | `/usr/local/bin/show_img` |
| show_img config | `/home/dave/.config/trmnl/show_img.json` |
| systemd (server) | `/etc/systemd/system/trmnl-byos.service` |
| systemd (client) | `/etc/systemd/system/trmnl-display.service` |

## Current Status
Phase 1 (Hardware PoC) and Phase 2 (Local BYOS) are **complete**. The display is running autonomously via systemd services and will survive reboots.

## Next Planned Steps
1. Port existing InkyPi Python plugins (weather, calendar, todo) as TRMNL plugin modules for the BYOS server.
2. Implement playlist rotation in the BYOS server (cycle through multiple plugin outputs).
3. Add dark mode scheduling (invert at night).
