<?php
require '/var/www/html/vendor/autoload.php';
$app = require '/var/www/html/bootstrap/app.php';

use Symfony\Component\Yaml\Yaml;
use Illuminate\Contracts\Console\Kernel;
use Illuminate\Support\Facades\DB;

$app->make(Kernel::class)->bootstrap();
$data = Yaml::parseFile('/tmp/trmnl-multi-calendar-settings.yml');
$custom = $data['custom_fields'] ?? [];
$current = json_decode(DB::table('plugins')->where('id', 16)->value('configuration') ?: '{}', true);
if (!is_array($current)) {
    $current = [];
}
$current['theme'] = $current['theme'] ?? 'dark';
DB::table('plugins')->where('id', 16)->update([
    'configuration_template' => json_encode(['custom_fields' => $custom]),
    'configuration' => json_encode($current),
]);
echo "seeded\n";
