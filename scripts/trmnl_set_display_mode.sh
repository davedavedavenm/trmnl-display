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

plugin_name_for_mode() {
  case "$1" in
    calendar) echo "${TRMNL_MODE_PLUGIN_CALENDAR:-Multi-Calendar}" ;;
    idle) echo "${TRMNL_MODE_PLUGIN_IDLE:-Multi-Calendar}" ;;
    sonos) echo "${TRMNL_MODE_PLUGIN_SONOS:-Sonos Local}" ;;
    jen_commute) echo "${TRMNL_MODE_PLUGIN_JEN_COMMUTE:-Jen Commute}" ;;
    dave_commute) echo "${TRMNL_MODE_PLUGIN_DAVE_COMMUTE:-}" ;;
    alert) echo "${TRMNL_MODE_PLUGIN_ALERT:-}" ;;
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
