<?php

declare(strict_types=1);

namespace App\Core;

/**
 * Autoloader PSR-4 de respaldo.
 *
 * Si existe vendor/autoload.php (composer install / composer dump-autoload) se usa ese.
 * Si no (hosting sin acceso a Composer), este cargador mapea App\ => /app sin dependencias.
 */
final class Autoloader
{
    /** @var array<string, string> prefijo => directorio base */
    private static array $prefixes = [];

    public static function register(string $prefix, string $baseDir): void
    {
        $prefix = trim($prefix, '\\') . '\\';
        self::$prefixes[$prefix] = rtrim($baseDir, DIRECTORY_SEPARATOR) . DIRECTORY_SEPARATOR;

        static $registered = false;
        if (!$registered) {
            spl_autoload_register([self::class, 'load'], true, true);
            $registered = true;
        }
    }

    public static function load(string $class): void
    {
        foreach (self::$prefixes as $prefix => $baseDir) {
            if (!str_starts_with($class, $prefix)) {
                continue;
            }
            $relative = substr($class, strlen($prefix));
            // Evita path traversal con nombres de clase manipulados
            if (str_contains($relative, '..')) {
                return;
            }
            $file = $baseDir . str_replace('\\', DIRECTORY_SEPARATOR, $relative) . '.php';
            if (is_file($file)) {
                require $file;
            }
            return;
        }
    }
}
