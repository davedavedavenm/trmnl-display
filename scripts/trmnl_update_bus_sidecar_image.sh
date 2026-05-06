#!/usr/bin/env bash
set -euo pipefail

LARAPAPER_CONTAINER="${TRMNL_LARAPAPER_CONTAINER:-larapaper-app-1}"
PLUGIN_NAME="${TRMNL_BUS_PLUGIN_NAME:-UK Bus Departures (TransportAPI)}"
SIDECAR_IMAGE_PATH="${TRMNL_BUS_SIDECAR_IMAGE_PATH:-/home/dave/sidecar_bus_departures_next.png}"
SIDECAR_IMAGE_NAME="${TRMNL_BUS_SIDECAR_IMAGE_NAME:-sidecar_bus_departures_next}"
SIDECAR_CONTAINER_IMAGE_PATH="${TRMNL_BUS_SIDECAR_CONTAINER_IMAGE_PATH:-/var/www/html/storage/app/public/images/generated/${SIDECAR_IMAGE_NAME}.png}"

if [[ ! -s "${SIDECAR_IMAGE_PATH}" ]]; then
  echo "sidecar update skipped; image not found: ${SIDECAR_IMAGE_PATH}" >&2
  exit 1
fi

docker cp "${SIDECAR_IMAGE_PATH}" "${LARAPAPER_CONTAINER}:${SIDECAR_CONTAINER_IMAGE_PATH}"

docker exec \
  -e PLUGIN_NAME="${PLUGIN_NAME}" \
  -e SIDECAR_IMAGE_NAME="${SIDECAR_IMAGE_NAME}" \
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
    'renderer' => 'trmnl-display bus colour sidecar',
]);

$updated = DB::table('plugins')
    ->where('name', $pluginName)
    ->update([
        'current_image' => $imageName,
        'current_image_metadata' => $metadata,
        'data_payload_updated_at' => now(),
        'data_stale_minutes' => 1440,
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
