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

LARAPAPER_CONTAINER="${TRMNL_LARAPAPER_CONTAINER:-larapaper-app-1}"
PLUGIN_NAME="Jen Morning"

# Read payload from stdin
PAYLOAD=$(cat)

if [[ -z "${PAYLOAD}" ]]; then
  echo "Error: No payload received on stdin." >&2
  exit 1
fi

echo "Updating LaraPaper database for ${PLUGIN_NAME}..."

# Update LaraPaper's database row inside the container
docker exec \
  -e PLUGIN_NAME="${PLUGIN_NAME}" \
  -e PAYLOAD="${PAYLOAD}" \
  -i "${LARAPAPER_CONTAINER}" php <<'PHP'
<?php
require '/var/www/html/vendor/autoload.php';
$app = require '/var/www/html/bootstrap/app.php';
$app->make(Illuminate\Contracts\Console\Kernel::class)->bootstrap();

$pluginName = getenv('PLUGIN_NAME');
$payloadJson = getenv('PAYLOAD');

$data = json_decode($payloadJson, true);
$mergeVariables = $data['merge_variables'] ?? $data;

$updated = DB::table('plugins')
    ->where('name', $pluginName)
    ->update([
        'data_payload' => json_encode($mergeVariables),
        'data_payload_updated_at' => now()->subHours(2), // Force not stale
        'updated_at' => now(),
    ]);

if ($updated < 1) {
    fwrite(STDERR, "Plugin not found: {$pluginName}\n");
    exit(2);
}

echo "Successfully updated database payload.\n";
PHP

# Trigger the morning mashup sidecar rendering immediately
echo "Running morning mashup sidecar refresh..."
"${SCRIPT_DIR}/trmnl_refresh_morning_mashup.sh" --force
