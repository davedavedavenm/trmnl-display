<?php
require '/var/www/html/vendor/autoload.php';
$app = require '/var/www/html/bootstrap/app.php';
$app->make(Illuminate\Contracts\Console\Kernel::class)->bootstrap();

$id = 16;
$full = file_get_contents('/home/dave/full.liquid');
$half = file_get_contents('/home/dave/half_horizontal.liquid');
$quad = file_get_contents('/home/dave/quadrant.liquid');

$updated = DB::table('plugins')->where('id', $id)->update([
    'full_liquid' => $full,
    'half_horizontal_liquid' => $half,
    'quadrant_liquid' => $quad,
    'updated_at' => now(),
]);

echo json_encode(['updated' => $updated]);
