# Changelog

## 2026-05-02

- Reworked the HA colour sidecar grid to hide visible light cards, combine climate and humidity into one indoor card, and use the freed space for a wider home-status row.
- Refined the HA colour sidecar layout to remove the top bar, bottom navigation, and energy card, group people into one presence card, and dedicate the lower-right card to media.
- Updated the HA dashboard plugin contract, payload example, and docs so navigation and energy are no longer advertised as active fields in the current `compact_grid` sidecar layout.
- Expanded the HA dashboard plugin contract with configurable labels for sidecar cards, light cards, media/presence summaries, and bottom navigation.
- Improved the proof-style sidecar render so it avoids clipped metric titles, uses higher-contrast navigation labels, and shows honest empty-state text for unconfigured optional cards.
- Integrated the accepted HA colour sidecar back into LaraPaper BYOS delivery by handing off `sidecar_colour_dashboard_next.png` through LaraPaper's generated-image storage during `ha_dashboard` mode.
- Updated the `khpi5` HA dashboard cron so live payload pushes re-render the sidecar and refresh the handoff only when `ha_dashboard` is already active.
- Fixed the Pi display shell's shutdown trap so service restarts no longer wait for systemd to kill a sleeping process during sidecar verification.
- Made `scripts/tmp/sidecar_colour_dashboard_proof_2026-05-01.png` the tracked canonical colour-dashboard visual reference and documented that the muted LaraPaper-style render is not the target design.
- Restored `scripts/render_colour_dashboard.py` to the accepted proof-style icon/card layout while keeping TRMNL `merge_variables` payload input and writing non-overwriting `*_next.png` iteration files.
- Extended the HA dashboard plugin contract and companion payload writer with optional light and energy fields for the proof-style card surfaces.
- Aligned the HA dashboard colour sidecar with the plugin payload contract by rendering from TRMNL `merge_variables` JSON instead of static proof data.
- Updated the HA dashboard companion payload to include plugin fields and configurable entity IDs via `/home/dave/.env.trmnl-ha-dashboard`.
- Added a khpi5 environment example and documented local/live sidecar payload rendering.
- Added an explicit blind open-position setting so inverted cover controllers do not require hardcoded renderer logic.
- Restored the colour sidecar to the compact icon-led dashboard layout with solid seven-colour panel fills.

## 2026-05-01

- Documented the TRMNL BYOS colour-renderer audit, including Terminus, LaraPaper, BYOS Next, Node Lite, and the official ImageMagick guidance.
- Added and hardware-tested a quick seven-colour sidecar dashboard renderer for the Inky/Spectra panel.
- Locked in the colour sidecar as the preferred path forward for colour-critical dashboard rendering.
- Added mandatory plugin/recipe portability rules and expanded the HA dashboard plugin field/payload contract.
