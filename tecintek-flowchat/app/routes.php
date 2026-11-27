<?php

declare(strict_types=1);

use App\Core\Database;
use App\Core\Request;
use App\Core\Response;
use App\Core\Router;

/**
 * Tabla de rutas. En fases siguientes se añaden:
 *  - Fase 3: /webhooks/meta (GET verify + POST eventos), /webhooks/webchat
 *  - Fase 4: /app/* (panel), /api/inbox/poll, /widget/*
 *  - Fase 5: /api/v1/* (REST con Bearer token)
 */
return static function (Router $router): void {

    // Health-check: útil para monitoreo (UptimeRobot) y para verificar la instalación.
    $router->get('/health', static function (Request $r): Response {
        $db = 'down';
        try {
            $db = Database::fetchValue('SELECT 1') == 1 ? 'up' : 'down';
        } catch (Throwable) {
            // no exponer detalles
        }
        $lastCron = null;
        try {
            $lastCron = Database::fetchValue('SELECT MAX(started_at) FROM cron_runs');
        } catch (Throwable) {
        }
        return Response::json([
            'app'      => config('app.name'),
            'status'   => $db === 'up' ? 'ok' : 'degraded',
            'database' => $db,
            'last_cron_run_utc' => $lastCron,
            'php'      => PHP_VERSION,
            'time_utc' => now_utc(),
        ], $db === 'up' ? 200 : 503);
    });

    $router->get('/', static fn (Request $r): Response => Response::redirect(url('/app')));
};
