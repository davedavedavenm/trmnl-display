# TRMNL BYOS Colour Audit

Date: 2026-05-01

This note records the current assessment of TRMNL BYOS options for the live colour display.

## Current Hardware Constraint

The live device is a Raspberry Pi Zero 2 W driving a Pimoroni Inky Impression 7.3 / Spectra-class panel. The Pi logs identify the panel path as `EP73_SPECTRA_800x480` and show successful `800 x 480, 4-bpp` refreshes.

That means the display path is not limited to the normal black-and-white TRMNL output. The limiting factor is the server-side renderer and image preprocessing pipeline.

## Official BYOS Contract

The official BYOS model is intentionally simple: the device calls a self-hosted server, including device headers, and asks for `/api/setup`, `/api/display`, and `/api/log`. The `/api/display` response points the device at an image to fetch.

This means colour handling does not have to be built into LaraPaper specifically. Any BYOS-compatible server or sidecar can generate a better colour image as long as the Pi receives a compatible URL and file.

Source: https://docs.trmnl.com/go/diy/byos

## Implementation Findings

### Terminus / BYOS Hanami

Best colour candidate.

Terminus has an explicit colour converter that:

- reads model palette colours
- builds an ImageMagick palette from those colours
- normalizes and saturates the input
- applies Floyd-Steinberg dithering
- remaps the rendered image to the device palette

This is the strongest upstream fit for the Inky/Spectra panel because the palette is a first-class part of the renderer instead of an incidental result of CSS colour choices.

Source: https://github.com/usetrmnl/terminus/blob/main/app/aspects/screens/converters/color.rb

### LaraPaper / BYOS Laravel

Best current management UI for this deployment, but currently weak for rich colour output.

LaraPaper is working well for device management, plugins, playlists, and previews. The observed output for this panel is still being collapsed into a small fixed palette. Recent dashboard work can push more semantic colour into the source HTML, but the renderer/palette path remains the cap.

Use LaraPaper as the active BYOS server until a sidecar or replacement is proven, but do not assume LaraPaper is the best final colour renderer.

Source: https://github.com/usetrmnl/byos_laravel

### BYOS Next

Good candidate for modern UI authoring, not currently a better colour pipeline.

BYOS Next uses modern JavaScript/React-style tooling and includes image processing, but the built-in BMP renderer converts images to grayscale levels of 2, 4, or 16. It is useful for richer grayscale TRMNL output, not for native colour palette remapping without extra work.

Source: https://github.com/usetrmnl/byos_next/blob/main/utils/render-bmp.ts

### BYOS Node Lite

Not suitable for this colour target.

The Node Lite image path explicitly converts PNG input to grayscale and emits a 1-bit monochrome BMP. It is intentionally minimal and should not be used for the colour panel unless rewritten.

Source: https://github.com/usetrmnl/byos_node_lite/blob/main/src/Screen/PNGto1BIT.ts

### Official ImageMagick Guidance

The TRMNL ImageMagick guide confirms that preprocessing is the right layer for display-specific image quality. Its examples are mostly monochrome and grayscale, but the same `-remap` approach applies to a colour palette file for the Inky/Spectra display.

Source: https://docs.trmnl.com/go/diy/imagemagick-guide

## Recommendation

Do not replace LaraPaper immediately.

Instead, add a repo-owned colour renderer proof of concept:

1. Render the dashboard source at `800x480`.
2. Build a real panel palette file for the Inky/Spectra colours.
3. Remap the rendered image with ImageMagick using the same class of operation Terminus uses: palette remap plus dithering.
4. Serve the processed image through a small BYOS-compatible endpoint or inject it into LaraPaper through an image/plugin path.
5. Compare LaraPaper output, no-dither output, Floyd-Steinberg output, and ordered-dither output before pushing to the panel.

If the proof of concept clearly improves colour, the preferred long-term options are:

- keep LaraPaper for device/plugin management and use a colour-render sidecar for the HA dashboard
- pilot Terminus as a replacement BYOS server
- extend LaraPaper's renderer to use an explicit Inky/Spectra palette remap

## Quick Proof

The first proof script is `scripts/render_colour_dashboard.py`.

It generates:

- `scripts/tmp/sidecar_colour_dashboard_source.png` as the RGB source render
- `scripts/tmp/sidecar_colour_dashboard.png` as the indexed seven-colour panel render

The output uses the full test palette:

- black
- white
- red
- yellow
- blue
- green
- orange

Hardware test command used on `trmnl-pi`:

```sh
/usr/local/bin/show_img.bin file=/tmp/sidecar_colour_dashboard.png invert=false mode=full
```

Result:

- `image specs: 800 x 480, 8-bpp`
- `Preparing image for EPD as 4-bpp`
- `Refresh complete`

This confirms the physical Pi/panel path can accept a richer indexed colour image than LaraPaper's current generated dashboard output.

## Acceptance Criteria

A colour pipeline is better than the current LaraPaper path only if:

- the generated image uses the full intended device palette, not just four to six incidental buckets
- iconography and card surfaces remain legible after remapping
- text remains high contrast at e-ink scale
- the Pi logs still show successful `800 x 480, 4-bpp` refreshes
- the generated image is stored or reproducible from this repo
