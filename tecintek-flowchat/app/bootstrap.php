<?php

declare(strict_types=1);

/**
 * Arranque común para HTTP (public/index.php) y CLI (bin/cron_worker.php).
 */

use App\Core\Autoloader;
use App\Core\Config;
use App\Core\Env;
use App\Core\Logger;

define('BASE_PATH', dirname(__DIR__));
define('FC_START', microtime(true));

// 1) Autoload: Composer si existe; si no, PSR-4 propio (hosting sin Composer).
$composer = BASE_PATH . '/vendor/autoload.php';
if (is_file($composer)) {
    require $composer;
} else {
    require BASE_PATH . '/app/Core/Autoloader.php';
    Autoloader::register('App', BASE_PATH . '/app');
    require BASE_PATH . '/app/Core/helpers.php';
}

// 2) Entorno. Si no hay .env y no estamos en el instalador, aborta con mensaje claro.
$envFile = BASE_PATH . '/.env';
if (is_file($envFile)) {
    Env::load($envFile);
} elseif (!defined('FC_INSTALLER')) {
    http_response_code(503);
    exit(PHP_SAPI === 'cli'
        ? "Falta el archivo .env. Copia .env.example a .env\n"
        : 'Tecintek FlowChat no está instalado todavía.');
}

Config::init(BASE_PATH . '/config');

// 3) PHP runtime
date_default_timezone_set('UTC');           // la lógica interna trabaja en UTC
mb_internal_encoding('UTF-8');
error_reporting(E_ALL);
ini_set('display_errors', Config::get('app.debug') ? '1' : '0');
ini_set('log_errors', '1');
ini_set('error_log', BASE_PATH . '/storage/logs/php-errors.log');

// 4) Errores => excepciones; excepciones no capturadas => log + respuesta genérica.
set_error_handler(static function (int $severity, string $message, string $file, int $line): bool {
    if (!(error_reporting() & $severity)) {
        return false;
    }
    throw new ErrorException($message, 0, $severity, $file, $line);
});

set_exception_handler(static function (Throwable $e): void {
    Logger::exception($e);
    if (PHP_SAPI === 'cli') {
        fwrite(STDERR, '[FlowChat] ' . $e->getMessage() . PHP_EOL);
        exit(1);
    }
    if (!headers_sent()) {
        http_response_code(500);
        header('Content-Type: application/json; charset=utf-8');
    }
    echo json_encode(Config::get('app.debug')
        ? ['error' => $e->getMessage(), 'file' => $e->getFile() . ':' . $e->getLine()]
        : ['error' => 'Error interno del servidor']);
});
