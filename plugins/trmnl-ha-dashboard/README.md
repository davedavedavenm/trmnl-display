# HA Dashboard Plugin

A custom, 7-color ACeP optimized dashboard plugin for TRMNL / LaraPaper, designed to surface key Home Assistant state data via webhooks.

## Features

- **Bento-box Layout:** Uses solid color blocks (White, Blue, Yellow, Orange) to maximize e-ink contrast and prevent color bleeding.
- **Dynamic Content:** The "Now Playing" Sonos card only appears when music is actively playing, freeing up screen real estate for weather and home status when idle.
- **Rich Media:** Fetches and displays Sonos album artwork natively.
- **Iconography:** Uses clean SVG iconography for Home Status (Locks, Laundry, Blinds, Thermostat) for scannability.
- **Shareable:** Conforms to the official TRMNL plugin structure.

## Setup

1. Import the `settings.yml` and `full.liquid` into your TRMNL / LaraPaper instance as a new custom plugin.
2. Note your newly generated Webhook URL.
3. Configure the Python sync script (`trmnl_ha_dashboard.py`) with your `HA_URL`, `HA_TOKEN`, and `TRMNL_WEBHOOK_URL`.
4. Run the script via cron or a Home Assistant automation to push state updates to the display.

## Compatibility
Designed explicitly for the Pimoroni Inky Impression 7.3" (800x480) 7-color panel, taking advantage of its ability to render solid high-contrast color blocks.