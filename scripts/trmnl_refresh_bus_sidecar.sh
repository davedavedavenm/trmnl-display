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

# Force fresh data poll synchronously using php artisan tinker
echo 'App\Models\Plugin::find(11)->updateDataPayload();' | docker exec -i "${LARAPAPER_CONTAINER}" php artisan tinker


# Copy live DB to where the renderer reads it
docker cp "${LARAPAPER_CONTAINER}:/var/www/html/database/storage/database.sqlite" "${HOME}/tmp/larapaper.sqlite"

# Render the colour PNG
python3 "${SCRIPT_DIR}/render_bus_departures.py"

# Handoff to LaraPaper
export TRMNL_BUS_SIDECAR_IMAGE_PATH="${SIDECAR_IMAGE}"
bash "${HANDOFF_SCRIPT}"

echo "Bus sidecar refresh complete"
