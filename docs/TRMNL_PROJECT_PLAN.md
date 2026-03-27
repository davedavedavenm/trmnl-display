# TRMNL Project Plan

## Phase 1: Hardware PoC [COMPLETE]
- [x] Verify Pimoroni Inky Impression 7.3" compatibility with trmnl-display
- [x] Build and deploy Go client on Pi Zero
- [x] Confirm SPI permissions and show_img driver
- [x] Physical screen render test (grayscale + color)

## Phase 2: BYOS Server [COMPLETE]
- [x] Evaluate BYOS server options (Terminus, LaraPaper, byos_fastapi, custom Flask)
- [x] Deploy LaraPaper on khpi5 via Docker
- [x] Configure Docker volumes for persistence
- [x] Register device and configure API key
- [x] Fix duplicate device bug (disable auto-assign)
- [x] Point Pi Zero client at khpi5:4567

## Phase 3: Color E-Ink [COMPLETE]
- [x] Identify panel as 7-color ACeP (not grayscale)
- [x] Research bb_epaper color mode (4-bpp via BBEP_7COLOR)
- [x] Fix show_img.json (remove panel_2bit for 7-color mode)
- [x] Update LaraPaper device model (7 colors, 3-bit, color-7a palette)
- [x] Verify color image generation pipeline

## Phase 4: Systemd & Persistence [COMPLETE]
- [x] Create trmnl-display.service on Pi Zero
- [x] Create trmnl-byos.service on Pi Zero (now disabled)
- [x] Enable services for boot persistence
- [x] Configure Go client (api_key, device_id, base_url)

## Phase 5: Recipe Research & Installation [COMPLETE]
- [x] Audit 201 OSS catalog recipes for color compatibility
- [x] Audit TRMNL official catalog for color-capable recipes
- [x] Install initial recipes (12 plugins)
- [x] Fix bus departures polling URL

## Phase 6: Maintenance & Operations [IN PROGRESS]
- [ ] Set up LaraPaper auto-update (watchtower or cron) on khpi5
- [ ] Remove old InkyPi BYOS server + systemd service from Pi Zero
- [ ] E2E validate full pipeline after cleanup
- [ ] Fix Home Assistant recipe URL (raspberrypi.local not resolvable from khpi5)
- [ ] Configure World Clock timezones
- [ ] Fix bus departures Liquid template variable binding

## Phase 7: Optimization [PLANNED]
- [ ] Tune refresh interval per-plugin (currently 600s default)
- [ ] Add sleep mode scheduling
- [ ] Explore custom ACeP-optimized recipes
- [ ] Consider image_webhook plugin for custom Python-generated content
- [ ] Add dark mode / night schedule

## Phase 8: Advanced Features [PLANNED]
- [ ] Port InkyPi Python plugins as image_webhook plugins (if needed)
- [ ] Build custom color recipes using ACeP palette
- [ ] Evaluate bb_epaper dithering options for better color rendering
- [ ] Add monitoring/alerting for display health
