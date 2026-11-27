<?php

declare(strict_types=1);

return [
    'name'      => env('APP_NAME', 'Tecintek FlowChat'),
    'env'       => env('APP_ENV', 'production'),
    'debug'     => (bool) env('APP_DEBUG', false),
    'url'       => rtrim((string) env('APP_URL', 'http://localhost'), '/'),
    'timezone'  => env('APP_TIMEZONE', 'America/Bogota'),
    'key'       => env('APP_KEY', ''),
    'log_level' => env('LOG_LEVEL', 'info'),
    'log_retention_days' => (int) env('LOG_RETENTION_DAYS', 14),

    'session' => [
        'name'     => env('SESSION_NAME', 'fc_session'),
        'lifetime' => (int) env('SESSION_LIFETIME', 720),
        'secure'   => (bool) env('SESSION_SECURE_COOKIE', true),
    ],

    'inbox' => [
        'poll_interval_ms' => (int) env('INBOX_POLL_INTERVAL_MS', 3000),
    ],

    'paths' => [
        'logs'     => BASE_PATH . '/storage/logs',
        'cache'    => BASE_PATH . '/storage/cache',
        'uploads'  => BASE_PATH . '/storage/uploads',
        'tmp'      => BASE_PATH . '/storage/tmp',
        'sessions' => BASE_PATH . '/storage/sessions',
        'views'    => BASE_PATH . '/app/Views',
    ],
];
