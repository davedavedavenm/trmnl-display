#!/usr/bin/env bash
set -euo pipefail

# Upgrade LaraPaper container and reapply custom relative image URL preview patches
# Designed to run from cron daily on khpi5.

cd /home/dave/larapaper
docker compose pull
docker compose up -d

echo "Copying patched PluginWebhookController..."
docker cp /home/dave/trmnl-display-scripts/PluginWebhookController.patched.php larapaper-app-1:/var/www/html/app/Http/Controllers/Api/PluginWebhookController.php

echo "Re-applying relative preview URLs and sidecar stale patches..."
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

$pluginPath = '/var/www/html/app/Models/Plugin.php';
if (file_exists($pluginPath)) {
    $s = file_get_contents($pluginPath);
    if (strpos($s, "str_starts_with(\$this->current_image") === false) {
        $s = str_replace(
            "public function isDataStale(): bool\n    {",
            "public function isDataStale(): bool\n    {\n        if (str_starts_with(\$this->current_image ?? '', 'sidecar_')) {\n            return false;\n        }",
            $s
        );
        $s = str_replace(
            "public function isDataStale(): bool\r\n    {",
            "public function isDataStale(): bool\r\n    {\r\n        if (str_starts_with(\$this->current_image ?? '', 'sidecar_')) {\r\n            return false;\r\n        }",
            $s
        );
        file_put_contents($pluginPath, $s);
        echo "Patched $pluginPath\n";
    }
}
PHP

docker exec -i larapaper-app-1 php -r "opcache_reset();"
docker exec -i larapaper-app-1 php artisan view:clear
echo "LaraPaper upgrade and patch completed successfully."
