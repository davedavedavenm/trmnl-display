#!/usr/bin/env bash
set -uo pipefail
C="${TRMNL_LARAPAPER_CONTAINER:-larapaper-app-1}"
docker exec -i -e DEVICE_ID="${TRMNL_DEVICE_ID:-1}" "$C" php <<'PHP'
<?php
require '/var/www/html/vendor/autoload.php';
$app = require '/var/www/html/bootstrap/app.php';
$app->make(Illuminate\Contracts\Console\Kernel::class)->bootstrap();
use Illuminate\Support\Facades\DB;
$id = (int) getenv('DEVICE_ID');
$row = DB::table('playlists as pl')
    ->join('playlist_items as pi', 'pi.playlist_id', '=', 'pl.id')
    ->join('plugins as p', 'p.id', '=', 'pi.plugin_id')
    ->where('pl.is_active', 1)
    ->where('pl.device_id', $id)
    ->where('pi.is_active', 1)
    ->orderBy('pi.id')
    ->select('p.current_image as img')
    ->first();
if (!$row || !$row->img) { fwrite(STDERR, "reconcile: no active playlist item for device $id\n"); exit(0); }
$cur = DB::table('devices')->where('id', $id)->value('current_screen_image');
if ($cur === $row->img) { exit(0); }
DB::table('devices')->where('id', $id)->update(['current_screen_image' => $row->img, 'updated_at' => now()]);
fwrite(STDOUT, "reconciled device $id: $cur -> $row->img\n");
PHP
