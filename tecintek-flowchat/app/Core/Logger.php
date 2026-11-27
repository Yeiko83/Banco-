<?php

declare(strict_types=1);

namespace App\Core;

use Throwable;

/**
 * Logger a archivo diario en /storage/logs (formato JSON por línea, fácil de grep).
 * Canales: app, webhook, worker, flow, http.
 */
final class Logger
{
    private const LEVELS = ['debug' => 100, 'info' => 200, 'warning' => 300, 'error' => 400, 'critical' => 500];

    public static function debug(string $msg, array $ctx = [], string $channel = 'app'): void    { self::log('debug', $msg, $ctx, $channel); }
    public static function info(string $msg, array $ctx = [], string $channel = 'app'): void     { self::log('info', $msg, $ctx, $channel); }
    public static function warning(string $msg, array $ctx = [], string $channel = 'app'): void  { self::log('warning', $msg, $ctx, $channel); }
    public static function error(string $msg, array $ctx = [], string $channel = 'app'): void    { self::log('error', $msg, $ctx, $channel); }
    public static function critical(string $msg, array $ctx = [], string $channel = 'app'): void { self::log('critical', $msg, $ctx, $channel); }

    public static function exception(Throwable $e, array $ctx = [], string $channel = 'app'): void
    {
        self::error($e->getMessage(), $ctx + [
            'exception' => $e::class,
            'file'      => $e->getFile() . ':' . $e->getLine(),
            'trace'     => array_slice(explode("\n", $e->getTraceAsString()), 0, 12),
        ], $channel);
    }

    public static function log(string $level, string $message, array $context = [], string $channel = 'app'): void
    {
        $min = self::LEVELS[strtolower((string) Config::get('app.log_level', 'info'))] ?? 200;
        if ((self::LEVELS[$level] ?? 200) < $min) {
            return;
        }

        $channel = preg_replace('/[^a-z0-9_-]/i', '', $channel) ?: 'app';
        $dir = Config::get('app.paths.logs', BASE_PATH . '/storage/logs');
        $file = sprintf('%s/%s-%s.log', $dir, $channel, gmdate('Y-m-d'));

        $line = json_encode([
            'ts'      => gmdate('Y-m-d\TH:i:s\Z'),
            'level'   => $level,
            'msg'     => $message,
            'ctx'     => self::redact($context),
            'pid'     => getmypid(),
        ], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_PARTIAL_OUTPUT_ON_ERROR);

        @file_put_contents($file, $line . PHP_EOL, FILE_APPEND | LOCK_EX);
    }

    /** Evita escribir secretos en logs. */
    private static function redact(array $context): array
    {
        $sensitive = '/(token|secret|password|authorization|api_key|access_token)/i';
        array_walk_recursive($context, static function (&$value, $key) use ($sensitive) {
            if (is_string($key) && preg_match($sensitive, $key)) {
                $value = '***';
            }
        });
        return $context;
    }
}
