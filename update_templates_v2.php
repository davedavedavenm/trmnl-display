<?php
require '/var/www/html/vendor/autoload.php';
$app = require '/var/www/html/bootstrap/app.php';
$app->make(Illuminate\Contracts\Console\Kernel::class)->bootstrap();

$id = 16;
$json = file_get_contents('php://stdin');
$data = json_decode($json, true);

if (!$data) {
    fwrite(STDERR, \"Invalid JSON input\n\");
    exit(1);
}

$updated = DB::table('plugins')->where('id', $id)->update([
    'full_liquid' => $data['full'],
    'half_horizontal_liquid' => $data['half'],
    'quadrant_liquid' => $data['quad'],
    'updated_at' => now(),
]);

echo json_encode(['updated' => $updated]);
