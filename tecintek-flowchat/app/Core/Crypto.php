<?php

declare(strict_types=1);

namespace App\Core;

use RuntimeException;

/**
 * Cifrado simétrico autenticado (XSalsa20-Poly1305 vía libsodium) para guardar en BD
 * access tokens de Meta, app secrets y secretos TOTP. Requiere APP_KEY de 32 bytes.
 */
final class Crypto
{
    private const PREFIX = 'v1:';

    private static function key(): string
    {
        $raw = (string) Config::get('app.key', '');
        if (str_starts_with($raw, 'base64:')) {
            $raw = base64_decode(substr($raw, 7), true) ?: '';
        }
        if (strlen($raw) !== SODIUM_CRYPTO_SECRETBOX_KEYBYTES) {
            throw new RuntimeException('APP_KEY inválida: debe ser base64 de 32 bytes. Ejecuta php bin/keygen.php');
        }
        return $raw;
    }

    public static function encrypt(string $plaintext): string
    {
        $nonce = random_bytes(SODIUM_CRYPTO_SECRETBOX_NONCEBYTES);
        $cipher = sodium_crypto_secretbox($plaintext, $nonce, self::key());
        return self::PREFIX . base64_encode($nonce . $cipher);
    }

    public static function decrypt(string $payload): string
    {
        if (!str_starts_with($payload, self::PREFIX)) {
            throw new RuntimeException('Formato de dato cifrado desconocido');
        }
        $bin = base64_decode(substr($payload, strlen(self::PREFIX)), true);
        if ($bin === false || strlen($bin) <= SODIUM_CRYPTO_SECRETBOX_NONCEBYTES) {
            throw new RuntimeException('Dato cifrado corrupto');
        }
        $nonce = substr($bin, 0, SODIUM_CRYPTO_SECRETBOX_NONCEBYTES);
        $cipher = substr($bin, SODIUM_CRYPTO_SECRETBOX_NONCEBYTES);
        $plain = sodium_crypto_secretbox_open($cipher, $nonce, self::key());
        if ($plain === false) {
            throw new RuntimeException('No se pudo descifrar (APP_KEY distinta o dato alterado)');
        }
        return $plain;
    }

    public static function encryptArray(array $data): string
    {
        return self::encrypt(json_encode($data, JSON_THROW_ON_ERROR));
    }

    public static function decryptArray(?string $payload): array
    {
        if ($payload === null || $payload === '') {
            return [];
        }
        return (array) json_decode(self::decrypt($payload), true, 512, JSON_THROW_ON_ERROR);
    }

    /** Token aleatorio URL-safe (API tokens, webhook keys, webchat). */
    public static function randomToken(int $bytes = 32): string
    {
        return rtrim(strtr(base64_encode(random_bytes($bytes)), '+/', '-_'), '=');
    }

    /** Validación de X-Hub-Signature-256 de Meta en tiempo constante. */
    public static function verifyMetaSignature(string $rawBody, ?string $header, string $appSecret): bool
    {
        if ($header === null || !str_starts_with($header, 'sha256=') || $appSecret === '') {
            return false;
        }
        $expected = 'sha256=' . hash_hmac('sha256', $rawBody, $appSecret);
        return hash_equals($expected, $header);
    }
}
