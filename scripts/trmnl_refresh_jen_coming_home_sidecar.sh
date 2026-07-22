#!/usr/bin/env bash
set -euo pipefail

# Renders the "Jen Coming Home" colour sidecar and hands the image to LaraPaper.
# Reuses the existing jen_commute display mode (which is the "Jen coming home from
# work" mode in Home Assistant) but drives the new "Jen Coming Home" plugin/view.

LARAPAPER_CONTAINER="${TRMNL_LARAPAPER_CONTAINER:-larapaper-app-1}"
SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do
  DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"
  SOURCE="$(readlink "$SOURCE")"
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
done
SCRIPT_DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"

# 1. Active Mode Check (the coming-home screen rides on the jen_commute mode)
if [[ "${1:-}" != "--force" ]]; then
  if ! "${TRMNL_SET_DISPLAY_MODE_BIN:-/home/dave/bin/trmnl-set-display-mode}" status | grep -q "TRMNL Mode: jen_commute"; then
    echo "Display is not in jen_commute mode. Skipping refresh."
    exit 0
  fi
fi

# 2. Copy live DB to where the renderer reads it
mkdir -p "${HOME}/tmp"
docker cp "${LARAPAPER_CONTAINER}:/var/www/html/database/storage/database.sqlite" "${HOME}/tmp/larapaper.sqlite"

# 3. Render the colour PNG (reads the "Jen Coming Home" payload from the DB)
python3 "${SCRIPT_DIR}/render_jen_coming_home.py"

# 4. Copy image to LaraPaper container
SIDECAR_IMAGE_PATH="${SCRIPT_DIR}/tmp/sidecar_jen_coming_home_next.png"
SIDECAR_IMAGE_NAME="sidecar_jen_coming_home_next"
SIDECAR_CONTAINER_IMAGE_PATH="/var/www/html/storage/app/public/images/generated/${SIDECAR_IMAGE_NAME}.png"

if [[ ! -s "${SIDECAR_IMAGE_PATH}" ]]; then
  echo "sidecar update skipped; image not found: ${SIDECAR_IMAGE_PATH}" >&2
  exit 1
fi

docker cp "${SIDECAR_IMAGE_PATH}" "${LARAPAPER_CONTAINER}:${SIDECAR_CONTAINER_IMAGE_PATH}"

# 5. Update database row in LaraPaper
docker exec \
  -e PLUGIN_NAME="Jen Coming Home" \
  -e SIDECAR_IMAGE_NAME="${SIDECAR_IMAGE_NAME}" \
  -e TRMNL_DEVICE_ID="${TRMNL_DEVICE_ID:-1}" \
  -i "${LARAPAPER_CONTAINER}" php <<'PHP'
<?php
require '/var/www/html/vendor/autoload.php';
$app = require '/var/www/html/bootstrap/app.php';
$app->make(Illuminate\Contracts\Console\Kernel::class)->bootstrap();

$pluginName = getenv('PLUGIN_NAME');
$imageName = getenv('SIDECAR_IMAGE_NAME');
$metadata = json_encode([
    'width' => 800,
    'height' => 480,
    'rotation' => 0,
    'palette_id' => 10,
    'mime_type' => 'image/png',
    'renderer' => 'trmnl-display jen coming home colour sidecar',
]);

$updated = DB::table('plugins')
    ->where('name', $pluginName)
    ->update([
        'current_image' => $imageName,
        'current_image_metadata' => $metadata,
        'data_payload_updated_at' => now()->subHours(2),
        'data_stale_minutes' => 1440,
        'updated_at' => now(),
    ]);

DB::table('devices')
    ->where('id', (int) (getenv('TRMNL_DEVICE_ID') ?: 1))
    ->update([
        'current_screen_image' => $imageName,
        'updated_at' => now(),
    ]);

if ($updated < 1) {
    fwrite(STDERR, "Plugin not found: {$pluginName}\n");
    exit(2);
}

echo json_encode([
    'sidecar_plugin_update' => true,
    'playlist_safe' => true,
    'plugin' => $pluginName,
    'image' => $imageName,
]);
PHP

echo "Jen Coming Home sidecar refresh complete"
