<?php

declare(strict_types=1);

/**
 * Genera una APP_KEY y (opcionalmente) la escribe en .env.
 *   php bin/keygen.php          -> imprime la clave
 *   php bin/keygen.php --write  -> la guarda en .env si APP_KEY está vacía
 */

if (PHP_SAPI !== 'cli') {
    http_response_code(403);
    exit('Sólo CLI');
}

$key = 'base64:' . base64_encode(random_bytes(32));
$envFile = dirname(__DIR__) . '/.env';

if (in_array('--write', $argv, true)) {
    if (!is_file($envFile)) {
        fwrite(STDERR, "No existe .env. Copia .env.example a .env primero.\n");
        exit(1);
    }
    $content = (string) file_get_contents($envFile);
    if (preg_match('/^APP_KEY=\S+/m', $content)) {
        fwrite(STDERR, "APP_KEY ya tiene valor. No se sobrescribe (perderías acceso a los tokens cifrados).\n");
        exit(1);
    }
    $content = preg_match('/^APP_KEY=.*$/m', $content)
        ? preg_replace('/^APP_KEY=.*$/m', 'APP_KEY=' . $key, $content)
        : $content . PHP_EOL . 'APP_KEY=' . $key . PHP_EOL;
    file_put_contents($envFile, $content);
    echo "APP_KEY escrita en .env\n";
    exit(0);
}

echo $key . PHP_EOL;
