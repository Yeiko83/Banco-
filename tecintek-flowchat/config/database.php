<?php

declare(strict_types=1);

return [
    'host'      => env('DB_HOST', 'localhost'),
    'port'      => (int) env('DB_PORT', 3306),
    'database'  => env('DB_DATABASE', ''),
    'username'  => env('DB_USERNAME', ''),
    'password'  => (string) env('DB_PASSWORD', ''),
    'charset'   => env('DB_CHARSET', 'utf8mb4'),
    'collation' => env('DB_COLLATION', 'utf8mb4_unicode_ci'),
];
