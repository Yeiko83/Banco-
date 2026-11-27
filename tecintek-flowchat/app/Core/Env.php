<?php

declare(strict_types=1);

namespace App\Core;

use RuntimeException;

/**
 * Lector minimalista de archivos .env (sin dependencias como vlucas/phpdotenv).
 * Soporta comentarios (#), comillas simples/dobles y comentarios en línea.
 * No sobrescribe variables ya definidas por el servidor.
 */
final class Env
{
    /** @var array<string, string> */
    private static array $values = [];

    public static function load(string $path): void
    {
        if (!is_file($path) || !is_readable($path)) {
            throw new RuntimeException("Archivo .env no encontrado o ilegible: {$path}");
        }

        $lines = file($path, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES) ?: [];
        foreach ($lines as $line) {
            $line = trim($line);
            if ($line === '' || $line[0] === '#') {
                continue;
            }
            if (str_starts_with($line, 'export ')) {
                $line = substr($line, 7);
            }
            $pos = strpos($line, '=');
            if ($pos === false) {
                continue;
            }

            $key = trim(substr($line, 0, $pos));
            if (!preg_match('/^[A-Z_][A-Z0-9_]*$/i', $key)) {
                continue;
            }
            $value = self::parseValue(trim(substr($line, $pos + 1)));

            if (getenv($key) !== false) {          // variables reales del servidor tienen prioridad
                self::$values[$key] = (string) getenv($key);
                continue;
            }
            self::$values[$key] = $value;
            $_ENV[$key] = $value;
        }
    }

    private static function parseValue(string $raw): string
    {
        if ($raw === '') {
            return '';
        }
        $quote = $raw[0];
        if ($quote === '"' || $quote === "'") {
            $end = strpos($raw, $quote, 1);
            $value = $end === false ? substr($raw, 1) : substr($raw, 1, $end - 1);
            return $quote === '"' ? stripcslashes($value) : $value;
        }
        // Comentario en línea: VALOR   # comentario
        $hash = strpos($raw, ' #');
        if ($hash !== false) {
            $raw = substr($raw, 0, $hash);
        }
        return trim($raw);
    }

    public static function get(string $key, mixed $default = null): mixed
    {
        $value = self::$values[$key] ?? (getenv($key) !== false ? getenv($key) : null);
        if ($value === null) {
            return $default;
        }

        return match (strtolower((string) $value)) {
            'true', '(true)'   => true,
            'false', '(false)' => false,
            'null', '(null)'   => null,
            'empty', '(empty)' => '',
            default            => $value,
        };
    }
}
