#!/usr/bin/env bash
set -euo pipefail

LARAPAPER_CONTAINER="${TRMNL_LARAPAPER_CONTAINER:-larapaper-app-1}"
# Resolve symlinks to find the real script directory
SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do
  DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"
  SOURCE="$(readlink "$SOURCE")"
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
done
SCRIPT_DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"
SIDECAR_IMAGE="${SCRIPT_DIR}/tmp/sidecar_bus_departures_next.png"
HANDOFF_SCRIPT="${SCRIPT_DIR}/trmnl_update_bus_sidecar_image.sh"

# 1. Active Mode Check
# Only poll TransportAPI if the display mode is currently set to 'bus',
# unless the script is called with '--force' (e.g. during a manual/system override).
if [[ "${1:-}" != "--force" ]]; then
  if ! /home/dave/bin/trmnl-set-display-mode status | grep -q "TRMNL Mode: bus"; then
    echo "Display is not in bus mode. Skipping TransportAPI poll."
    exit 0
  fi
fi

# 2. Quota Check (Max 28 requests per rolling 24 hours to stay under the 30-hit free tier limit)
QUOTA_FILE="/tmp/trmnl_bus_api_calls.log"
touch "${QUOTA_FILE}"

now=$(date +%s)
one_day_ago=$((now - 86400))

# Filter timestamps older than 24 hours
if [ -f "${QUOTA_FILE}" ]; then
  tmp_file=$(mktemp)
  while read -r ts; do
    if [ -n "$ts" ] && [ "$ts" -gt "$one_day_ago" ] 2>/dev/null; then
      echo "$ts" >> "$tmp_file"
    fi
  done < "${QUOTA_FILE}"
  mv "$tmp_file" "${QUOTA_FILE}"
fi

call_count=$(wc -l < "${QUOTA_FILE}")
if [ "${call_count}" -ge 28 ]; then
  echo "Warning: TransportAPI daily limit reached (${call_count}/28 calls in last 24h). Skipping API poll to prevent ban."
  SKIP_POLL=1
else
  SKIP_POLL=0
fi

# 3. Fetch & Render
if [ "${SKIP_POLL}" -eq 0 ]; then
  echo "Forcing TransportAPI fresh data poll..."
  # Force fresh data poll synchronously using php artisan tinker
  echo 'App\Models\Plugin::find(11)->updateDataPayload();' | docker exec -i "${LARAPAPER_CONTAINER}" php artisan tinker

  # Log this API hit timestamp
  date +%s >> "${QUOTA_FILE}"
else
  echo "Using cached LaraPaper payload for rendering..."
fi

# Copy live DB to where the renderer reads it
docker cp "${LARAPAPER_CONTAINER}:/var/www/html/database/storage/database.sqlite" "${HOME}/tmp/larapaper.sqlite"

# Render the colour PNG
python3 "${SCRIPT_DIR}/render_bus_departures.py"

# Handoff to LaraPaper
export TRMNL_BUS_SIDECAR_IMAGE_PATH="${SIDECAR_IMAGE}"
bash "${HANDOFF_SCRIPT}"

echo "Bus sidecar refresh complete"
