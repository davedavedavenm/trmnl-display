#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-}"
if [[ -z "${MODE}" ]]; then
  echo "usage: trmnl_set_display_mode.sh <mode|status>" >&2
  exit 1
fi

LARAPAPER_CONTAINER="${TRMNL_LARAPAPER_CONTAINER:-larapaper-app-1}"
DEVICE_ID="${TRMNL_DEVICE_ID:-1}"
PLAYLIST_PREFIX="${TRMNL_PLAYLIST_PREFIX:-TRMNL Mode}"
REFRESH_TIME="${TRMNL_MODE_REFRESH_TIME:-600}"
SIDECAR_HANDOFF_ENABLED="${TRMNL_SIDECAR_HANDOFF_ENABLED:-1}"
SIDECAR_IMAGE_PATH="${TRMNL_SIDECAR_IMAGE_PATH:-/home/dave/sidecar_colour_dashboard_next.png}"
SIDECAR_IMAGE_NAME="${TRMNL_SIDECAR_IMAGE_NAME:-sidecar_colour_dashboard_next}"
SIDECAR_CONTAINER_IMAGE_PATH="${TRMNL_SIDECAR_CONTAINER_IMAGE_PATH:-/var/www/html/storage/app/public/images/generated/${SIDECAR_IMAGE_NAME}.png}"

plugin_name_for_mode() {
  case "$1" in
    calendar) echo "${TRMNL_MODE_PLUGIN_CALENDAR:-Multi-Calendar}" ;;
    idle) echo "${TRMNL_MODE_PLUGIN_IDLE:-Multi-Calendar}" ;;
    sonos) echo "${TRMNL_MODE_PLUGIN_SONOS:-Sonos Local}" ;;
    jen_commute) echo "${TRMNL_MODE_PLUGIN_JEN_COMMUTE:-Jen Commute}" ;;
    ha_dashboard) echo "${TRMNL_MODE_PLUGIN_HA_DASHBOARD:-Home Assistant}" ;;
    jen_morning) echo "${TRMNL_MODE_PLUGIN_JEN_MORNING:-Jen Morning}" ;;
    dave_commute) echo "${TRMNL_MODE_PLUGIN_DAVE_COMMUTE:-}" ;;
    alert) echo "${TRMNL_MODE_PLUGIN_ALERT:-Alert}" ;;
    *) return 1 ;;
  esac
}

if [[ "${MODE}" == "status" ]]; then
  docker exec -e DEVICE_ID="${DEVICE_ID}" -i "${LARAPAPER_CONTAINER}" php <<'PHP'
<?php
require '/var/www/html/vendor/autoload.php';
$app = require '/var/www/html/bootstrap/app.php';
$app->make(Illuminate\Contracts\Console\Kernel::class)->bootstrap();
$active = DB::table('playlists')
    ->where('device_id', (int) getenv('DEVICE_ID'))
    ->where('is_active', 1)
    ->get(['id', 'name', 'refresh_time']);
echo json_encode($active);
PHP
  exit 0
fi

PLUGIN_NAME="$(plugin_name_for_mode "${MODE}")" || {
  echo "unknown mode: ${MODE}" >&2
  exit 1
}

if [[ -z "${PLUGIN_NAME}" ]]; then
  echo "mode ${MODE} is not configured; leaving current playlist unchanged"
  exit 0
fi

PLAYLIST_NAME="${PLAYLIST_PREFIX}: ${MODE}"

docker exec \
  -e DEVICE_ID="${DEVICE_ID}" \
  -e MODE="${MODE}" \
  -e PLUGIN_NAME="${PLUGIN_NAME}" \
  -e PLAYLIST_NAME="${PLAYLIST_NAME}" \
  -e REFRESH_TIME="${REFRESH_TIME}" \
  -i "${LARAPAPER_CONTAINER}" php <<'PHP'
<?php
require '/var/www/html/vendor/autoload.php';
$app = require '/var/www/html/bootstrap/app.php';
$app->make(Illuminate\Contracts\Console\Kernel::class)->bootstrap();

$deviceId = (int) getenv('DEVICE_ID');
$mode = getenv('MODE');
$pluginName = getenv('PLUGIN_NAME');
$playlistName = getenv('PLAYLIST_NAME');
$refreshTime = (int) getenv('REFRESH_TIME');

$plugin = DB::table('plugins')->where('name', $pluginName)->first();
if (! $plugin) {
    fwrite(STDERR, "Plugin not found for mode {$mode}: {$pluginName}\n");
    exit(2);
}

$playlist = DB::table('playlists')
    ->where('device_id', $deviceId)
    ->where('name', $playlistName)
    ->first();

if (! $playlist) {
    $playlistId = DB::table('playlists')->insertGetId([
        'device_id' => $deviceId,
        'name' => $playlistName,
        'is_active' => 0,
        'weekdays' => null,
        'active_from' => null,
        'active_until' => null,
        'refresh_time' => $refreshTime,
        'created_at' => now(),
        'updated_at' => now(),
    ]);
} else {
    $playlistId = $playlist->id;
    DB::table('playlists')
        ->where('id', $playlistId)
        ->update([
            'refresh_time' => $refreshTime,
            'updated_at' => now(),
        ]);
}

DB::table('playlist_items')
    ->where('playlist_id', $playlistId)
    ->update([
        'is_active' => 0,
        'updated_at' => now(),
    ]);

$item = DB::table('playlist_items')
    ->where('playlist_id', $playlistId)
    ->where('plugin_id', $plugin->id)
    ->first();

if (! $item) {
    DB::table('playlist_items')->insert([
        'playlist_id' => $playlistId,
        'plugin_id' => $plugin->id,
        'order' => 1,
        'is_active' => 1,
        'last_displayed_at' => null,
        'created_at' => now(),
        'updated_at' => now(),
        'mashup' => null,
    ]);
} else {
    DB::table('playlist_items')
        ->where('id', $item->id)
        ->update([
            'order' => 1,
            'is_active' => 1,
            'updated_at' => now(),
        ]);
}

DB::table('playlists')
    ->where('device_id', $deviceId)
    ->update([
        'is_active' => 0,
        'updated_at' => now(),
    ]);

DB::table('playlists')
    ->where('id', $playlistId)
    ->update([
        'is_active' => 1,
        'updated_at' => now(),
    ]);

echo json_encode([
    'mode' => $mode,
    'plugin' => $pluginName,
    'playlist_id' => $playlistId,
    'playlist_name' => $playlistName,
]);
PHP

if [[ "${MODE}" == "ha_dashboard" && "${SIDECAR_HANDOFF_ENABLED}" == "1" ]]; then
  if [[ ! -s "${SIDECAR_IMAGE_PATH}" ]]; then
    echo "sidecar handoff skipped; image not found: ${SIDECAR_IMAGE_PATH}" >&2
    exit 0
  fi

  docker cp "${SIDECAR_IMAGE_PATH}" "${LARAPAPER_CONTAINER}:${SIDECAR_CONTAINER_IMAGE_PATH}"

  docker exec \
    -e DEVICE_ID="${DEVICE_ID}" \
    -e PLUGIN_NAME="${PLUGIN_NAME}" \
    -e SIDECAR_IMAGE_NAME="${SIDECAR_IMAGE_NAME}" \
    -i "${LARAPAPER_CONTAINER}" php <<'PHP'
<?php
require '/var/www/html/vendor/autoload.php';
$app = require '/var/www/html/bootstrap/app.php';
$app->make(Illuminate\Contracts\Console\Kernel::class)->bootstrap();

$deviceId = (int) getenv('DEVICE_ID');
$pluginName = getenv('PLUGIN_NAME');
$imageName = getenv('SIDECAR_IMAGE_NAME');
$metadata = json_encode([
    'width' => 800,
    'height' => 480,
    'rotation' => 0,
    'palette_id' => 10,
    'mime_type' => 'image/png',
]);

DB::table('devices')
    ->where('id', $deviceId)
    ->update([
        'current_screen_image' => $imageName,
        'updated_at' => now(),
    ]);

DB::table('plugins')
    ->where('name', $pluginName)
    ->update([
        'current_image' => $imageName,
        'current_image_metadata' => $metadata,
        'data_payload_updated_at' => now()->subHours(2),
        'updated_at' => now(),
    ]);

echo json_encode([
    'sidecar_handoff' => true,
    'plugin' => $pluginName,
    'image' => $imageName,
]);
PHP
fi
