#!/usr/bin/env bash
set -euo pipefail

# Upgrade LaraPaper container and reapply custom relative image URL preview patches
# Designed to run from cron daily on khpi5.

cd /home/dave/larapaper
docker compose pull
docker compose up -d

echo "Re-applying relative preview URLs patch..."
docker exec -i larapaper-app-1 php <<'PHP'
<?php
$files = [
    '/var/www/html/resources/views/livewire/device-dashboard.blade.php',
    '/var/www/html/resources/views/livewire/devices/configure.blade.php'
];
foreach ($files as $path) {
    if (file_exists($path)) {
        $s = file_get_contents($path);
        $target = "Storage::disk('public')->url('images/generated/' . \$current_image_uuid . '.' . \$file_extension)";
        $replace = "'/storage/images/generated/' . \$current_image_uuid . '.' . \$file_extension";
        if (strpos($s, $target) !== false) {
            file_put_contents($path, str_replace($target, $replace, $s));
            echo "Patched $path\n";
        }
    }
}
PHP

docker exec -i larapaper-app-1 php artisan view:clear
echo "LaraPaper upgrade and patch completed successfully."
