# Colour Sidecar Path

Date: 2026-05-01

This is the path forward for the Home Assistant dashboard on the live TRMNL display.

## Decision

Use a repo-owned colour renderer for colour-critical dashboards.

LaraPaper remains valuable for BYOS device management, playlists, plugin storage, and the normal TRMNL API surface, but it is no longer assumed to be the best renderer for the colour dashboard. The live panel can display a richer indexed colour image when the image is generated directly for the Inky/Spectra path.

## Proven Result

The proof script is:

```text
scripts/render_colour_dashboard.py
```

It generates:

```text
scripts/tmp/sidecar_colour_dashboard_source.png
scripts/tmp/sidecar_colour_dashboard.png
```

The output PNG is an indexed seven-colour image using:

- black
- white
- red
- yellow
- blue
- green
- orange

Direct hardware test on `trmnl-pi`:

```sh
scp scripts/tmp/sidecar_colour_dashboard.png trmnl-pi:/tmp/sidecar_colour_dashboard.png
ssh trmnl-pi "sudo systemctl stop trmnl-display.service && /usr/local/bin/show_img.bin file=/tmp/sidecar_colour_dashboard.png invert=false mode=full"
```

Confirmed output:

```text
image specs: 800 x 480, 8-bpp
Preparing image for EPD as 4-bpp
Refresh complete
```

This proves the physical Pi and panel can accept richer colour than the current LaraPaper-generated dashboard path.

## Target Architecture

```mermaid
flowchart LR
  HA["Home Assistant\nstate + mode intent"] --> Renderer["Colour renderer\nrepo-owned 800x480 indexed PNG"]
  Renderer --> Image["Panel-ready image\n7-colour indexed PNG"]
  Image --> BYOS["BYOS delivery\nLaraPaper or small sidecar endpoint"]
  BYOS --> Pi["trmnl-pi\nthin display client"]
  Pi --> Panel["Inky Impression 7.3\nEP73_SPECTRA_800x480"]
```

## Rendering Rules

1. Render at exactly `800x480`.
2. Keep the final panel image indexed/paletted, not full RGB.
3. Use the panel palette deliberately; do not rely on incidental CSS colour quantization.
4. Preserve strong black text and icon outlines.
5. Test generated PNGs locally before physical refresh.
6. Use direct `show_img.bin` tests for colour experiments before wiring them into the polling loop.
7. Once a screen is accepted, route it through a BYOS-compatible image URL so the Pi remains a thin client.

## Development Flow

1. Update `scripts/render_colour_dashboard.py` or successor renderer code.
2. Generate the source and indexed output PNGs.
3. Inspect the generated image visually.
4. Confirm palette use with Pillow or an equivalent image tool.
5. Stop `trmnl-display.service` only when doing a direct hardware proof.
6. Push the image to `/tmp` on `trmnl-pi`.
7. Run `show_img.bin`.
8. Record the result in docs and commit the source changes.

## Next Implementation Step

Turn the proof into a live sidecar flow:

- fetch real Home Assistant state
- render the accepted dashboard layout
- emit an indexed seven-colour PNG
- serve it from `khpi5`
- point the Pi at it through BYOS-compatible delivery

The first live version can be intentionally simple. It should prioritize colour fidelity, readable icons, and a stable direct path over full LaraPaper feature parity.

