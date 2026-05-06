#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="${NANGO_ENV_FILE:-/home/dave/.env.nango}"

if [[ -f "${ENV_FILE}" ]]; then
  set -a
  source "${ENV_FILE}"
  set +a
fi

python3 "${SCRIPT_DIR}/nango_calendar_fetch.py"

python3 "${SCRIPT_DIR}/render_calendar_dayview.py" --payload "${SCRIPT_DIR}/tmp/nango_calendar_payload.json"

export TRMNL_CALENDAR_SIDECAR_IMAGE_PATH="${SCRIPT_DIR}/tmp/sidecar_calendar_day_next.png"
export TRMNL_CALENDAR_PLUGIN_NAME="Calendar Day View"
bash "${SCRIPT_DIR}/trmnl_update_calendar_sidecar_image.sh"

echo "Calendar sidecar refresh complete"
