<?php
require '/var/www/html/vendor/autoload.php';
$app = require '/var/www/html/bootstrap/app.php';

use Symfony\Component\Yaml\Yaml;
use Illuminate\Contracts\Console\Kernel;
use Illuminate\Support\Facades\DB;

$app->make(Kernel::class)->bootstrap();
$data = Yaml::parseFile('/tmp/trmnl-calendar-dayview-settings.yml');
$custom = $data['custom_fields'] ?? [];
$current = json_decode(DB::table('plugins')->where('id', 27)->value('configuration') ?: '{}', true);
if (!is_array($current)) {
    $current = [];
}
$current['theme'] = $current['theme'] ?? 'dark';
$current['layout'] = $current['layout'] ?? 'featured';
$current['nango_base_url'] = $current['nango_base_url'] ?? 'https://nango.example.com';

$strategy = $data['strategy'] ?? 'polling';
DB::table('plugins')->where('id', 27)->update([
    'configuration_template' => json_encode(['custom_fields' => $custom]),
    'configuration' => json_encode($current),
    'data_strategy' => $strategy,
]);
echo "seeded day view plugin\n";
