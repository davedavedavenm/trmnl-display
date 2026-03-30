#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  larapaper_manage_mashup.sh apply
  larapaper_manage_mashup.sh status

Environment overrides:
  LARAPAPER_CONTAINER   Docker container name (default: larapaper-app-1)
  PLAYLIST_NAME         LaraPaper playlist name
                        (default: TRMNL Mode: jen_morning)
  LEFT_PLUGIN_NAME      Left-side plugin name (default: Jen Morning)
  RIGHT_PLUGIN_NAME     Right-side plugin name (default: Potter Quotes)
  MASHUP_LAYOUT         LaraPaper mashup layout (default: 1Lx1R)
  MASHUP_NAME           Friendly mashup name
                        (default: Jen Morning + Potter Quotes)

This script is meant to run on the LaraPaper host.
It updates playlist DB state only. It does not modify plugin templates.
EOF
}

command="${1:-}"
if [[ -z "${command}" ]]; then
  usage
  exit 1
fi

container="${LARAPAPER_CONTAINER:-larapaper-app-1}"
playlist_name="${PLAYLIST_NAME:-TRMNL Mode: jen_morning}"
left_plugin_name="${LEFT_PLUGIN_NAME:-Jen Morning}"
right_plugin_name="${RIGHT_PLUGIN_NAME:-Potter Quotes}"
layout="${MASHUP_LAYOUT:-1Lx1R}"
mashup_name="${MASHUP_NAME:-Jen Morning + Potter Quotes}"

php_common='require "/var/www/html/vendor/autoload.php";
$app = require "/var/www/html/bootstrap/app.php";
$kernel = $app->make(Illuminate\Contracts\Console\Kernel::class);
$kernel->bootstrap();'

if [[ "${command}" == "apply" ]]; then
  php_code=$(cat <<PHP
<?php
${php_common}

\$playlist = App\Models\Playlist::where('name', '${playlist_name}')->firstOrFail();
\$left = App\Models\Plugin::where('name', '${left_plugin_name}')->firstOrFail();
\$right = App\Models\Plugin::where('name', '${right_plugin_name}')->firstOrFail();
\$item = App\Models\PlaylistItem::where('playlist_id', \$playlist->id)
    ->orderBy('order')
    ->first();

if (! \$item) {
    \$order = (int) App\Models\PlaylistItem::where('playlist_id', \$playlist->id)->max('order');
    \$item = App\Models\PlaylistItem::createMashup(
        \$playlist,
        '${layout}',
        [\$left->id, \$right->id],
        '${mashup_name}',
        \$order + 1
    );
} else {
    \$item->plugin_id = \$left->id;
    \$item->mashup = [
        'mashup_layout' => '${layout}',
        'mashup_name' => '${mashup_name}',
        'plugin_ids' => [\$left->id, \$right->id],
    ];
    \$item->is_active = true;
    \$item->save();
}

echo json_encode([
    'playlist' => ['id' => \$playlist->id, 'name' => \$playlist->name],
    'item' => ['id' => \$item->id, 'order' => \$item->order],
    'mashup' => \$item->mashup,
    'plugins' => [
        'left' => ['id' => \$left->id, 'name' => \$left->name],
        'right' => ['id' => \$right->id, 'name' => \$right->name],
    ],
], JSON_PRETTY_PRINT) . PHP_EOL;
PHP
)
elif [[ "${command}" == "status" ]]; then
  php_code=$(cat <<PHP
<?php
${php_common}

\$playlist = App\Models\Playlist::where('name', '${playlist_name}')->first();
if (! \$playlist) {
    fwrite(STDERR, "Playlist not found: ${playlist_name}\n");
    exit(2);
}
\$items = App\Models\PlaylistItem::where('playlist_id', \$playlist->id)
    ->orderBy('order')
    ->get(['id', 'order', 'plugin_id', 'mashup', 'is_active'])
    ->toArray();

echo json_encode([
    'playlist' => ['id' => \$playlist->id, 'name' => \$playlist->name],
    'items' => \$items,
], JSON_PRETTY_PRINT) . PHP_EOL;
PHP
)
else
  usage
  exit 1
fi

printf '%s\n' "${php_code}" | docker exec -i "${container}" php /dev/stdin
