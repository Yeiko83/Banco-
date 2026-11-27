<?php

declare(strict_types=1);

return [
    'batch_size'           => (int) env('QUEUE_BATCH_SIZE', 50),
    'max_runtime'          => (int) env('QUEUE_MAX_RUNTIME', 50),   // < 60s: el cron corre cada minuto
    'lock_timeout'         => (int) env('QUEUE_LOCK_TIMEOUT', 300),
    'broadcast_batch_size' => (int) env('BROADCAST_BATCH_SIZE', 50),
    'flow_max_steps'       => (int) env('FLOW_MAX_STEPS', 60),
    // Backoff exponencial entre reintentos (segundos): intento 1, 2, 3...
    'retry_backoff'        => [30, 120, 600],
    'http' => [
        'timeout'           => (int) env('HTTP_TIMEOUT', 10),
        'allow_private_ips' => (bool) env('HTTP_ALLOW_PRIVATE_IPS', false),
    ],
];
