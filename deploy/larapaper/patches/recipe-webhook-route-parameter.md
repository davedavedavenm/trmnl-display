# LaraPaper Recipe Webhook Route Parameter Patch

Date: 2026-05-02

## Problem

The live LaraPaper recipe detail page returned HTTP 500 for the Home Assistant recipe.

The container log showed:

```text
Missing required parameter for [Route: api.custom_plugins.webhook] [URI: api/custom_plugins/{plugin}] [Missing parameter: plugin]
```

The live route expects `{plugin}`, but the recipe Blade view generated the webhook URL with `plugin_uuid`.

## Live Patch

Patch inside `larapaper-app-1`:

```sh
docker exec -i larapaper-app-1 php <<'PHP'
<?php
$path = '/var/www/html/resources/views/livewire/plugins/recipe.blade.php';
$s = file_get_contents($path);
$s = str_replace('[\'plugin_uuid\' => $plugin->uuid]', '[\'plugin\' => $plugin->uuid]', $s);
file_put_contents($path, $s);
PHP
docker exec -i larapaper-app-1 php artisan view:clear
```

## Verification

```sh
docker exec -i larapaper-app-1 php <<'PHP'
<?php
require '/var/www/html/vendor/autoload.php';
$app = require '/var/www/html/bootstrap/app.php';
$app->make(Illuminate\Contracts\Console\Kernel::class)->bootstrap();
$plugin = DB::table('plugins')->where('name', 'Home Assistant')->first(['uuid']);
echo route('api.custom_plugins.webhook', ['plugin' => $plugin->uuid]), "\n";
PHP
```

Expected: a URL like:

```text
https://trmnl.magnusfamily.co.uk/api/custom_plugins/<plugin-uuid>
```

## Notes

This is a LaraPaper view compatibility patch. It does not change the sidecar image path or the Pi BYOS polling contract.
