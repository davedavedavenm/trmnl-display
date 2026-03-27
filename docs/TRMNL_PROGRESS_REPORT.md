# TRMNL Integration: Progress Report

## Accomplishments to Date

### 1. Documentation Deep-Dive
- Audited official TRMNL BYOD and BYOS documentation.
- Analyzed the TRMNL Private API (/api/display) for image rendering and refresh cycles.
- Reviewed the trmnl-display Go client architecture.
- Researched all official BYOS server implementations (Terminus, LaraPaper, byos_fastapi, byos_django).
- Audited 700+ community recipes and 201 OSS catalog recipes for color e-ink compatibility.

### 2. Hardware Audit
- **Confirmed Device:** Pimoroni Inky Impression 7.3" (800x480).
- **Panel Type:** 7-color ACeP (Black, White, Red, Green, Blue, Yellow, Orange) - NOT grayscale only.
- **Driver:** `bb_epaper` via `show_img` binary with `EP73_SPECTRA_800x480` panel driver.
- **Refresh Mode:** Only `REFRESH_FULL` works on ACeP. No partial/fast refresh available.
- **Refresh Interval:** 15-30 seconds per refresh. Recommended 600s (10 min) poll interval.
- **Panel Lifetime:** ~50,000-100,000 refresh cycles.
- **Permissions:** User `dave` has spi/gpio/i2c group membership. No sudo required.

### 3. Migration Strategy
- Authored and pushed docs/TRMNL_INTEGRATION_PLAN.md to GitHub.
- Defined a phased approach: Hardware PoC -> BYOS Server -> Plugin Migration.
- Evolved plan: BYOS server moved from Pi Zero to khpi5 (Pi 5, 16GB RAM, NVMe).

### 4. Hardware PoC - COMPLETE
- Mock server deployed and validated on Pi.
- Go client (`trmnl-display`) built and tested on Pi Zero.
- Physical screen render confirmed: `show_img` -> SPI -> EPD works end-to-end.
- Color render verified: 4-bpp (7-color) mode confirmed via BMP test image.

### 5. BYOS Server - LaraPaper on khpi5 - COMPLETE
- **Evaluated byos_fastapi:** Too heavy for Pi Zero (requires Chromium, d3blocks, 100MB+ RAM).
- **Built custom Flask BYOS server** (`scripts/trmnl_byos_server.py`) - lightweight, ~30MB RAM.
- **Deployed LaraPaper** on khpi5 via Docker (ghcr.io/usetrmnl/larapaper:latest).
- LaraPaper runs on port 4567 with Docker volumes for database and storage persistence.
- Device registered: MAC `88:A2:9E:2B:2B:B9`, API key `VAtHzgSkFcV6dtvbGSYxrE`.

### 6. Color E-Ink Configuration - COMPLETE
- Updated LaraPaper `inky_impression_7_3` device model: 7 colors, 3-bit, palette `color-7a`.
- Updated `show_img.json` on Pi: removed `panel_2bit` to enable 4-bpp color mode.
- Verified: LaraPaper generates 4-bit colormap PNGs when device model is set correctly.
- `trmnl-liquid-cli` installed in LaraPaper container for recipe rendering.

### 7. Systemd Services - COMPLETE (Pi Zero)
- **trmnl-display.service:** Runs Go client, points at khpi5:4567, enabled at boot.
- **trmnl-byos.service:** Local Flask BYOS server (now DISABLED - replaced by LaraPaper on khpi5).
- Both services auto-restart on failure with 15s delay.

### 8. Recipe Research - COMPLETE
- Audited all 201 OSS catalog recipes and TRMNL official catalog.
- **Zero recipes explicitly support 7-color ACeP**, but many use semantic colors that map well.
- Identified top candidates: Uptime Kuma, Crypto Fear & Greed, Air Quality, F1 Dashboard, US Weather Maps.
- Comics and photos work but with heavy dithering.

### 9. Installed Plugins (in LaraPaper)
- OBB Departures (recipe)
- Weather (recipe)
- Zen Quotes (recipe)
- This Day in History (recipe)
- Home Assistant (recipe) - needs correct HA URL
- Sunrise/Sunset (recipe)
- Pollen Forecast (recipe)
- Holidays iCal (recipe)
- Netflix Release Radar (recipe)
- Horizontal World Clock (recipe) - needs timezone config
- UK Bus Departures TransportAPI (recipe) - polling URL hardcoded to fix Liquid template bug
- Uptime Kuma Statuspage (recipe)

### 10. Known Issues
- **Bus departures:** Liquid template `timespan` variable not injected into polling URL. Workaround: hardcoded full URL.
- **Home Assistant:** URL `raspberrypi.local` not resolvable from khpi5 container. Needs correct IP.
- **World Clock:** No timezone/city data configured.
- **Duplicate device bug:** LaraPaper auto-assign creates ghost devices when `assign_new_devices=1` and Go client sends empty `ID` header. Fix: disabled auto-assign, set correct config.
- **Force refresh:** No UI button. Must run `ssh inky-pi 'sudo systemctl restart trmnl-display'`.

## Architecture

```
[Pi Zero - InkyPi]
    |
    | systemd: trmnl-display.service
    | polls every 600s (configurable via LaraPaper)
    | headers: ID=MAC, access-token=API_KEY
    v
    GET http://192.168.1.143:4567/api/display
    |
    v
[Pi 5 - khpi5]
    |
    | Docker: ghcr.io/usetrmnl/larapaper:latest
    | Port 4567
    | Renders Liquid templates via headless browser
    | Applies 7-color palette via ImageStage->colormap()
    | Returns: {image_url, filename, refresh_rate}
    v
    Pi Zero downloads PNG -> show_img -> SPI -> EPD
```

## File Locations

### Pi Zero (inky-pi) - Display Client
| Component | Path |
|---|---|
| Go Client | `/home/dave/trmnl-display/trmnl-display` |
| Client Config | `/home/dave/.config/trmnl/config.json` |
| show_img | `/usr/local/bin/show_img` |
| show_img Config | `/home/dave/.config/trmnl/show_img.json` |
| systemd (display) | `/etc/systemd/system/trmnl-display.service` |
| Old BYOS Server | `/home/dave/trmnl-byos/server.py` (DISABLED) |
| Old BYOS systemd | `/etc/systemd/system/trmnl-byos.service` (DISABLED) |

### Pi 5 (khpi5) - BYOS Server
| Component | Path |
|---|---|
| Docker Compose | `/home/dave/larapaper/docker-compose.yml` |
| Database Volume | `larapaper_database` |
| Storage Volume | `larapaper_storage` |
| Image Output | `storage/app/public/images/generated/` |
| Web UI | `http://192.168.1.143:4567` |

## Next Planned Steps
1. Set up LaraPaper auto-update via watchtower or cron on khpi5.
2. Clean up old BYOS server from Pi Zero.
3. Fix Home Assistant URL for khpi5 container resolution.
4. Configure World Clock timezones.
5. Explore and install more color-capable recipes.
6. Consider custom recipe development for ACeP 7-color palette.
