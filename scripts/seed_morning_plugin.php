<?php
require '/var/www/html/vendor/autoload.php';
$app = require '/var/www/html/bootstrap/app.php';

use Symfony\Component\Yaml\Yaml;
use Illuminate\Contracts\Console\Kernel;
use Illuminate\Support\Facades\DB;

$app->make(Kernel::class)->bootstrap();
$data = Yaml::parseFile('/tmp/trmnl-jen-morning-settings.yml');
$custom = $data['custom_fields'] ?? [];

$current = json_decode(DB::table('plugins')->where('id', 24)->value('configuration') ?: '{}', true);
if (!is_array($current)) {
    $current = [];
}
$current['layout_mode'] = $current['layout_mode'] ?? 'mashup';
$current['layout_variant'] = $current['layout_variant'] ?? 'automotive_hud';
$current['screen_label'] = $current['screen_label'] ?? 'Jen Morning';
$current['headline_fallback'] = $current['headline_fallback'] ?? 'Time To Work';
$current['colour_profile'] = $current['colour_profile'] ?? 'navy_blue';
$current['eta_label'] = $current['eta_label'] ?? 'DRIVE TIME';
$current['eta_unit_label'] = $current['eta_unit_label'] ?? 'min';
$current['show_distance'] = $current['show_distance'] ?? true;
$current['distance_unit_label'] = $current['distance_unit_label'] ?? 'km';

$strategy = $data['strategy'] ?? 'webhook';
DB::table('plugins')->where('id', 24)->update([
    'configuration_template' => json_encode(['custom_fields' => $custom]),
    'configuration' => json_encode($current),
    'data_strategy' => $strategy,
]);
echo "seeded jen morning plugin\n";
