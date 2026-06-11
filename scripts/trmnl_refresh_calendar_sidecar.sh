#!/usr/bin/env bash
set -euo pipefail

# Resolve symlinks to find the real script directory
SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do
  DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"
  SOURCE="$(readlink "$SOURCE")"
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
done
SCRIPT_DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"
ENV_FILE="${NANGO_ENV_FILE:-/home/dave/.env.nango}"
SETTINGS_FILE="${TRMNL_CALENDAR_SETTINGS_FILE:-${SCRIPT_DIR}/.env.calendar}"

if [[ -f "${ENV_FILE}" ]]; then
  set -a
  source "${ENV_FILE}"
  set +a
fi

if [[ -f "${SETTINGS_FILE}" ]]; then
  set -a
  source "${SETTINGS_FILE}"
  set +a
fi

# Defaults
export TRMNL_CALENDAR_THEME="${TRMNL_CALENDAR_THEME:-dark}"
export TRMNL_CALENDAR_LAYOUT="${TRMNL_CALENDAR_LAYOUT:-featured}"

python3 "${SCRIPT_DIR}/nango_calendar_fetch.py"

python3 "${SCRIPT_DIR}/render_calendar_dayview.py" --payload "${SCRIPT_DIR}/tmp/nango_calendar_payload.json"

export TRMNL_CALENDAR_SIDECAR_IMAGE_PATH="${SCRIPT_DIR}/tmp/sidecar_calendar_day_next.png"
export TRMNL_CALENDAR_PLUGIN_NAME="Calendar Day View"
bash "${SCRIPT_DIR}/trmnl_update_calendar_sidecar_image.sh"

echo "Calendar sidecar refresh complete"
