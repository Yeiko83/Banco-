<?php

declare(strict_types=1);

return [
    'app_id'               => env('META_APP_ID', ''),
    'app_secret'           => (string) env('META_APP_SECRET', ''),
    'webhook_verify_token' => (string) env('META_WEBHOOK_VERIFY_TOKEN', ''),
    'graph_version'        => env('META_GRAPH_VERSION', 'v21.0'),
    'graph_base_url'       => 'https://graph.facebook.com',
    // Ventana de servicio al cliente de Meta: fuera de ella sólo se permiten plantillas (WA)
    // o etiquetas de mensaje (IG/FB).
    'customer_service_window_hours' => 24,
];
