# TRMNL Jen Morning

Scheduled morning commute screen for LaraPaper/TRMNL BYOS.

This recipe is intended for a predictable weekday morning window such as `06:45-07:30`. It is separate from the main Jen commute automation/state machine and should not alter that logic.

## Rendering Paths

### Colour Sidecar (Primary for Spectra Panels)

The recommended path for colour-capable TRMNL panels (Inky Impression 7.3 / Spectra-class) is the **Maps Style** colour sidecar renderer. This produces a rich, high-fidelity left/right split display with gradient panels, bold typography, and a companion HP quote on the right half.

- Renderer: `scripts/render_morning_mashup.py`
- Output: indexed 7-colour PNG at 800x480
- Proof: `scripts/tmp/sidecar_morning_mashup_source_next.png`

### Liquid Templates (Fallback)

For standard monochrome TRMNL panels or when the sidecar is unavailable, the plugin falls back to LaraPaper's Liquid rendering using `full.liquid` (standalone) or `half_vertical.liquid` (mashup). These use the `editorial` and `structured` layout variants.

## Files

| File | Purpose |
|---|---|
| `settings.yml` | Shareable plugin fields for LaraPaper import |
| `fields.schema.json` | Field contract and sidecar metadata |
| `payload.example.json` | Example webhook payload shape |
| `full.liquid` | Standalone Liquid template (editorial/structured layouts) |
| `half_vertical.liquid` | Half-width Liquid template for mashup compositing |
| `README.md` | This file |

## Expected Payload Fields

```json
{
  "merge_variables": {
    "updated_at": "08 May 07:15",
    "headline": "Time To Work",
    "eta_minutes": 42,
    "route_label": "Via A13",
    "distance_km": 28.5
  }
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `updated_at` | string | yes | Timestamp shown in header |
| `headline` | string | yes | Destination or commute headline |
| `eta_minutes` | number | yes | Drive time in minutes |
| `route_label` | string | yes | Route name (e.g., "Via A13") |
| `distance_km` | number | no | Route distance |

## User-Editable Settings

| Setting | Type | Default | Description |
|---|---|---|---|
| `Layout Mode` | select | `mashup` | `mashup` for split-screen with HP quote, `standalone` for full-screen |
| `Layout Variant` | select | `automotive_hud` | `swiss_typographic`, `infographic_timeline`, `bauhaus_geometric`, `automotive_hud`, `split_contrast`, `bento_grid`, `minimalist`, `dark_tech` |
| `Screen Label` | string | `Jen Morning` | Header label at top of commute panel |
| `Headline Fallback` | string | `Time To Work` | Used when payload omits `headline` |
| `Colour Profile` | select | `navy_blue` | `navy_blue`, `slate`, or `forest` gradient for left panel |
| `ETA Label` | string | `DRIVE TIME` | Label below the ETA number |
| `ETA Unit Label` | string | `min` | Unit beside the ETA value |
| `Show Distance` | boolean | `true` | Show route distance in card |
| `Distance Unit` | string | `km` | Unit suffix for distance |

## Setup

1. Import `settings.yml` into your TRMNL/LaraPaper instance as a new custom plugin.
2. Note the Webhook URL.
3. For colour sidecar rendering, run:
   ```bash
   python scripts/render_morning_mashup.py --payload /path/to/payload.json
   ```
4. For standard Liquid rendering, point a webhook sender (e.g., Home Assistant) at the plugin's custom-plugin endpoint.

## Suggested LaraPaper Setup

### Morning Mashup (Weekday 06:45-07:30)

1. Create the `Jen Morning` custom plugin from this folder.
2. Create the `Harry Potter Quotes` plugin from `plugins/trmnl-hp-quotes`.
3. Create a LaraPaper mashup playlist item using:
   - `Jen Morning` on the left (layout mode: `mashup`)
   - `Harry Potter Quotes` on the right (layout mode: `half_vertical`)
   - Layout: `1Lx1R`
4. Point a webhook sender at the Jen Morning plugin endpoint during the morning window.

### Standalone Full-Screen

- Layout mode: `standalone`
- Layout variant: `editorial` or `structured`
- Uses Liquid templates for monochrome panels

## Notes

- This is a separate morning screen, not a replacement for the main `Jen Commute` recipe.
- The intended Home Assistant pattern is: a dedicated TRMNL package pushes payloads and temporarily sets a TRMNL manual override during the configured morning window.
- Keep the recipe reusable by leaving commute-specific decision logic in Home Assistant or another upstream orchestrator. The plugin should stay focused on presentation and small user-configurable labels.
- For the currently used playlist-level wiring, see `docs/JEN_MORNING_MASHUP.md` and `scripts/larapaper_manage_mashup.sh`.
