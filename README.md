# TRMNL Display

This repository contains the TRMNL/LaraPaper-based homelab deployment for a Home Assistant-led e-paper appliance.

## Current Direction
The system architecture uses a "Bring Your Own Server" (BYOS) TRMNL approach:
- `khpi5` runs LaraPaper and the local companion scripts for private plugins
- the Pi Zero / Inky device acts as a thin TRMNL display client
- Home Assistant is the intended orchestration layer for screen modes and automations

## Primary Focus
- **Home Assistant Edition**: Home Assistant decides what the screen should show and when; LaraPaper renders the active recipe; the display client fetches the image.
- **Shareable TRMNL recipes/plugins**: Recipes should be exportable, reusable, and standards-compliant.
- **ACeP-first colour rendering**: Target display is a 7-colour panel.

## Active Components
- **Scripts**: Contains the BYOS server and update template scripts.
- **Plugins**: Contains TRMNL plugins/recipes (e.g. `trmnl-multi-calendar`, `trmnl-alert`, `trmnl-sonos-local`).

*(Note: Legacy Inky Impression 7.3 Python codebase has been removed as the project has transitioned entirely to the TRMNL ecosystem.)*
