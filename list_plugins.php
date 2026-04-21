<?php
require '/var/www/html/vendor/autoload.php';
$app = require '/var/www/html/bootstrap/app.php';
$app->make(Illuminate\Contracts\Console\Kernel::class)->bootstrap();
$plugins = DB::table('plugins')->get(['id', 'name', 'uuid']);
echo json_encode($plugins);
