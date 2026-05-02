# Changelog

## 2026-05-02

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
