<?php

declare(strict_types=1);

use App\Core\Config;
use App\Core\Env;

if (!function_exists('env')) {
    function env(string $key, mixed $default = null): mixed
    {
        return Env::get($key, $default);
    }
}

if (!function_exists('config')) {
    function config(string $key, mixed $default = null): mixed
    {
        return Config::get($key, $default);
    }
}

if (!function_exists('base_path')) {
    function base_path(string $path = ''): string
    {
        return BASE_PATH . ($path !== '' ? '/' . ltrim($path, '/') : '');
    }
}

if (!function_exists('storage_path')) {
    function storage_path(string $path = ''): string
    {
        return base_path('storage' . ($path !== '' ? '/' . ltrim($path, '/') : ''));
    }
}

if (!function_exists('url')) {
    function url(string $path = ''): string
    {
        return rtrim((string) config('app.url'), '/') . '/' . ltrim($path, '/');
    }
}

if (!function_exists('e')) {
    /** Escape HTML para vistas. */
    function e(mixed $value): string
    {
        return htmlspecialchars((string) $value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
    }
}

if (!function_exists('now_utc')) {
    /** Fecha actual en UTC con formato DATETIME de MariaDB. */
    function now_utc(string $modifier = ''): string
    {
        $dt = new DateTimeImmutable('now', new DateTimeZone('UTC'));
        if ($modifier !== '') {
            $dt = $dt->modify($modifier);
        }
        return $dt->format('Y-m-d H:i:s');
    }
}

if (!function_exists('json_out')) {
    function json_out(mixed $data): string
    {
        return json_encode($data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR);
    }
}
