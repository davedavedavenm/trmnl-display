#!/usr/bin/env bash
set -euo pipefail

DASHBOARD_SCRIPT="${TRMNL_HA_DASHBOARD_SCRIPT:-/home/dave/trmnl_ha_dashboard.py}"
RENDERER="${TRMNL_COLOUR_RENDERER:-/home/dave/render_colour_dashboard.py}"
PAYLOAD_PATH="${TRMNL_SIDECAR_PAYLOAD_PATH:-/home/dave/trmnl-ha-dashboard-payload.json}"
OUTPUT_PATH="${TRMNL_SIDECAR_IMAGE_PATH:-/home/dave/sidecar_colour_dashboard_next.png}"
SOURCE_OUTPUT_PATH="${TRMNL_SIDECAR_SOURCE_IMAGE_PATH:-/home/dave/sidecar_colour_dashboard_source_next.png}"
UPDATE_SCRIPT="${TRMNL_HA_SIDECAR_UPDATE_SCRIPT:-/home/dave/bin/trmnl-update-ha-sidecar-image}"
WORKDIR="${TRMNL_HA_SIDECAR_WORKDIR:-/home/dave}"

cd "$WORKDIR"

python3 "$DASHBOARD_SCRIPT"
python3 "$RENDERER" \
  --payload "$PAYLOAD_PATH" \
  --output "$OUTPUT_PATH" \
  --source-output "$SOURCE_OUTPUT_PATH"
"$UPDATE_SCRIPT"
