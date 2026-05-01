# Hardware Inventory

Last live scan: `2026-04-30`

## Conclusion

The physical display is not the common black-and-white TRMNL panel.

It is an `800x480` colour e-paper panel in the Pimoroni Inky Impression 7.3 / Spectra class, driven on the Pi as:

```json
{
  "adapter": "pimoroni",
  "panel_1bit": "EP73_SPECTRA_800x480"
}
```

Treat this as a colour-first target. Any change that silently downgrades recipes, LaraPaper device settings, or Pi output to 1-bit black/white is a regression.

## Live Host

| Item | Value |
|---|---|
| Host | `trmnl-pi` |
| LAN IP | `192.168.1.74` |
| Board | Raspberry Pi Zero 2 W Rev 1.0 |
| OS | Debian GNU/Linux 12 |
| Kernel at scan | `6.12.75+rpt-rpi-v8` |
| Primary display service | `trmnl-display.service` |
| Display writer | `/usr/local/bin/show_img.bin` via `/usr/local/bin/show_img` |

Network interfaces observed during the scan:

| Interface | Address |
|---|---|
| `wlan0` | `192.168.1.74/24` |
| `wg0` | `10.77.0.74/24` |
| `tailscale0` | `100.70.156.72/32` |

## Hardware Interfaces

The Pi has the expected display buses enabled:

- `/dev/spidev0.0`
- `/dev/i2c-1`
- `/dev/i2c-2`
- `/dev/gpiochip0`

`/boot/firmware/config.txt` enables SPI and I2C:

```ini
dtparam=i2c_arm=on
dtparam=spi=on
dtoverlay=spi0-0cs
```

Loaded kernel modules include:

- `spidev`
- `spi_bcm2835`
- `i2c_bcm2835`
- `i2c_dev`
- `raspberrypi_gpiomem`

GPIO scan showed SPI0 on GPIO 9/10/11 and the expected Pimoroni-style control pins. This matches the `bb_epaper` Pimoroni adapter mapping used by `show_img`.

## Display Identification Evidence

### Pi Client Config

Live file: `/home/dave/.config/trmnl/show_img.json`

```json
{
  "adapter": "pimoroni",
  "stretch": "aspectfill",
  "panel_1bit": "EP73_SPECTRA_800x480"
}
```

### Live Refresh Logs

Recent `trmnl-display.service` logs reported successful physical refreshes with:

```text
panel1bit = 37 (EP73_SPECTRA_800x480)
image specs: 800 x 480, 4-bpp
Preparing image for EPD as 4-bpp
Writing data to EPD...
Refresh complete
```

The `show_img --help` text mentions generic automatic conversion to 2-bit grayscale for some paths. Do not use that generic help text to override the live panel identity: the active config and service logs show the Spectra `800x480` path and 4-bpp prepared output.

### Driver Source

The installed `bb_epaper` source labels `EP73_SPECTRA_800x480` as:

```text
Spectra 6 7-color 800x480
```

Its `show_img` documentation also says that Spectra 6 panels like the Inky Impression 7.3 `800x480` should use:

```text
adapter = pimoroni
panel_1bit = EP73_SPECTRA_800x480
```

The installed Pimoroni Inky Python package also includes `800x480` definitions for the Inky Impression 7.3 colour panel family, including Spectra 6.

### LaraPaper Device Model

LaraPaper live DB record, queried from `khpi5`:

| Field | Value |
|---|---|
| Device name | `David M's TRMNL` |
| MAC | `88:A2:9E:2B:2B:B9` |
| Device model | `inky_impression_7_3` |
| Model label | `Inky Impression 7.3` |
| Width | `800` |
| Height | `480` |
| Palette ID | `10` |
| Model colours | `6` |
| Model bit depth | `3` |
| Model kind | `byod` |
| Maximum compatibility | `0` |

This LaraPaper model is the correct live BYOD profile for the colour screen.

Generated PNGs for this model are quantized by LaraPaper into six panel colour buckets. In live samples those buckets appear as white, black, blue, green/olive, yellow/ochre, and brown/red-orange. CSS colours such as bright red or orange may map into the brown/red-orange bucket rather than staying visually separate.

## Inconclusive Evidence

The I2C scan found a device at `0x50`, consistent with a HAT EEPROM address, but the EEPROM did not expose a useful text identity during the scan. Hardware identification should therefore rely on the active Pi config, `bb_epaper` panel constant, successful refresh logs, LaraPaper model, and physical visual verification.

## Operational Rules

- Keep `config/trmnl/show_img.json` aligned with the live `EP73_SPECTRA_800x480` config.
- Keep LaraPaper on the `inky_impression_7_3` BYOD model unless a replacement is physically tested.
- Use colour-safe recipe design and the ACeP palette guidance in `docs/LIVE_DEPLOYMENT_WORKFLOW.md`.
- Verify physical output after render-path changes; LaraPaper preview alone is not enough.
- Do not commit `/home/dave/.config/trmnl/config.json`; it contains the live device API key.
