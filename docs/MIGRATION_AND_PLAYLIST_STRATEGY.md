# Migration & Playlist Strategy

This document outlines the current playlist and dashboard architecture and provides a step-by-step migration path to align all plugins/recipes with the modern, clean, card-based "new design" (`compact_grid`) instead of the blocky "bento" layout.

---

## 1. Current Dashboard & Playlist Setup

Our Home Assistant-integrated TRMNL BYOS stack uses a decoupled model:
1. **Home Assistant (Orchestration)**: Decides *what* mode to show (e.g. `ha_dashboard`, `calendar`, `sonos`, `alert`) based on triggers, time, or presence. It calls the mode bridge via a `rest_command`.
2. **Mode Bridge (`trmnl-mode-bridge.service` on `khpi5`)**: Exposes an HTTP API. When it receives a mode request, it executes `/home/dave/bin/trmnl-set-display-mode <mode>`, which directly modifies LaraPaper's SQLite database to make the corresponding playlist active.
3. **Playlists (LaraPaper)**: Each display mode is a dedicated LaraPaper playlist (e.g. `TRMNL Mode: ha_dashboard`). This playlist contains exactly one plugin item.
4. **Sidecar Rendering (Visual Fidelity)**:
   - Instead of letting LaraPaper's default HTML-to-image pipeline render our layouts, we use dedicated Python scripts (`render_colour_dashboard.py` for HA, `render_calendar_dayview.py` for calendars, etc.) to render a pixel-perfect, indexed 7-color `800x480` PNG.
   - For routine state changes, the companion scripts overwrite the plugin's `current_image` in LaraPaper's public storage and update the database metadata directly. This is a **playlist-safe update**—it updates the image without triggering a full LaraPaper playlist cycle or causing display desync.
5. **Active Layout**: The HA Dashboard is currently running in `compact_grid` layout (restored via `TRMNL_LAYOUT_VARIANT=compact_grid` in `/home/dave/.env.trmnl-ha-dashboard`), which represents the clean card-based UI with nice iconography and light colors.

---

## 2. Bento vs. Compact Grid Designs

- **Bento Design (`layout_variant = "bento"`)**:
  - Uses full-bleed, high-saturation solid background color blocks (yellow, blue, green, red, orange) across the grid.
  - While optimized to prevent pigment bleeding on the physical ACeP panel, it can feel dither-heavy and visually busy ("very old").
- **Compact Grid Design (`layout_variant = "compact_grid"`)**:
  - Uses a modern card-based look with a clean off-white background (`#f8f5ed`).
  - Cards have clean borders (`1px solid #6f6f6f`), rounded corners (`6px`), and high-contrast dark text/outlines.
  - Color is used deliberately as accent fills (e.g. status badges, calendar indicator bars, icons) rather than full-bleed section blocks.

---

## 3. Safe Migration Path for Plugins

To unify all screens under the clean, modern card-based design, follow these guidelines for each plugin:

### A. Multi-Calendar (`trmnl-multi-calendar`)
The calendar plugin already supports a clean, light-themed card layout, but is currently configured to use `dark` mode by default.

- **How to migrate**:
  1. Open `/home/dave/trmnl-calendar/.env` on `khpi5`.
  2. Change `TRMNL_THEME=dark` to `TRMNL_THEME=light`.
  3. Run the calendar fetch/render script manually to verify the output:
     ```bash
     cd /home/dave/trmnl-calendar && .venv/bin/python main.py
     ```
  4. Ensure `plugins/trmnl-multi-calendar/full.liquid` is synced to LaraPaper with `theme: light` active in custom settings.

### B. Bus Departures (`trmnl-bus-departures`)
The bus departures script (`render_bus_departures.py`) is currently hardcoded to use a solid black background with white text.

- **How to migrate**:
  1. Modify `scripts/render_bus_departures.py` to change the background to off-white:
     ```python
     # Replace:
     # img = Image.new("RGB", (WIDTH, HEIGHT), BLACK)
     # With:
     img = Image.new("RGB", (WIDTH, HEIGHT), WHITE) # or (248, 245, 237)
     ```
  2. Update text drawings to use `BLACK` or `DARK_GREY` instead of `WHITE`.
  3. Restructure the rows to draw inside individual card rectangles (using `draw.rounded_rectangle` with a thin border) rather than drawing flat lines across a black canvas.
  4. Update the Liquid fallback `plugins/trmnl-bus-departures/full.liquid` to use identical styles.

### C. Sonos Local (`trmnl-sonos-local`)
The local Sonos plugin relies on LaraPaper to render its `full.liquid` template.

- **How to migrate**:
  1. Update `plugins/trmnl-sonos-local/full.liquid` to define:
     - Base screen background: `#f8f5ed`
     - Text colors: `#111` (primary), `#555` (secondary)
     - Album art border: `1px solid #6f6f6f`
     - Up Next track items: Rounded cards with a subtle gray border.
  2. Repush/re-import the updated `full.liquid` template into LaraPaper.

---

## 4. General Design System Guidelines (The "New Design" Standard)

When creating or transforming layouts for the 7-color Inky Impression screen:
1. **Backgrounds**: Always use off-white (`#f8f5ed` / `(248, 245, 237)`) or white (`#ffffff`).
2. **Cards**: Enclose logical blocks inside cards.
   - CSS: `border: 1px solid #6f6f6f; border-radius: 6px; background: #fff;`
   - PIL: `draw.rounded_rectangle([x1, y1, x2, y2], radius=6, fill=WHITE, outline=DARK_GREY, width=2)`
3. **Typography**: Keep text dark (`#111` or `(17, 17, 17)`) and choose legible sans-serif sizes. Keep outlines around small text to prevent color bleed.
4. **Color Accents**: Use the 7-color palette (`RED`, `GREEN`, `BLUE`, `YELLOW`, `ORANGE`, `BLACK`, `WHITE`) only for high-contrast indicators, status pills, or specific icon accents.
