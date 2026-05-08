# Harry Potter Quotes Plugin

A colour sidecar-rendered Harry Potter quote display for Spectra-class e-paper panels.

This plugin is **sidecar-only** — there is no Liquid template. A Python renderer generates an indexed 7-colour 800x480 PNG from a bundled quote database. The renderer is required for the colour Spectra panel output.

## Features

- Random quote from a curated selection of ~75 quotes across all HP books
- Parchment/cream background with elegant serif typography
- Attribution with character and source book
- House colour accent stripe (auto-detected from quote metadata)
- Configurable layout mode: full-screen or half-vertical (for morning mashup)
- Decorative quote marks and subtle border

## Files

| File | Purpose |
|---|---|
| `settings.yml` | Shareable plugin fields for LaraPaper import |
| `fields.schema.json` | Field contract and sidecar metadata |
| `payload.example.json` | Example webhook payload shape |
| `quotes.json` | Bundled quote data (character, text, book, house) |
| `render_hp_quotes.py` | Colour sidecar renderer (in `scripts/`) |

## Setup

1. Import `settings.yml` into your TRMNL/LaraPaper instance as a new custom plugin.
2. Note the Webhook URL.
3. Run the sidecar renderer to generate and hand off the image.

## Payload

The plugin accepts a standard `merge_variables` payload with these optional overrides:

| Field | Type | Default | Description |
|---|---|---|---|
| `layout_mode` | string | `full_screen` | `full_screen` or `half_vertical` |
| `theme` | string | `parchment` | `parchment` or `dark` |
| `house_accent` | string | `auto` | `auto`, `gryffindor`, `slytherin`, `ravenclaw`, `hufflepuff`, `none` |
| `show_house_banner` | bool | true | Show house colour stripe |
| `show_source_book` | bool | true | Show book name in attribution |

All fields are optional. The renderer falls back to defaults if omitted.

When no payload is provided, the renderer picks a random quote and uses default display settings.

## Installation Modes

### Full-Screen Evening Display

- Layout mode: `full_screen`
- Shows quote centered on a parchment background with house accent stripe
- Used in evening "both home" mode

### Half-Vertical Morning Mashup

- Layout mode: `half_vertical`
- Shows quote in the right half of the display, intended for compositing with Jen Morning ETA on the left
- Used in weekday 06:45-07:30 morning window

## Colour Palette

The renderer uses the same 7-colour panel palette as the other sidecar renderers:

| Colour | Usage |
|---|---|
| BLACK | Quote text, attribution, borders |
| WHITE | Background, quote marks |
| RED | Gryffindor accents, decorative elements |
| YELLOW | Hufflepuff accents, stars |
| BLUE | Ravenclaw accents |
| GREEN | Slytherin accents |
| ORANGE | Warm parchment tone, decorative elements |
