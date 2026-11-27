<?php

declare(strict_types=1);

namespace App\Core;

/**
 * Envoltura inmutable de la petición HTTP actual.
 * Conserva el body crudo: imprescindible para validar X-Hub-Signature-256 de Meta.
 */
final class Request
{
    private ?array $json = null;

    /** @param array<string,string> $routeParams */
    private function __construct(
        public readonly string $method,
        public readonly string $path,
        public readonly array $query,
        public readonly array $post,
        public readonly array $headers,
        public readonly string $rawBody,
        public readonly array $files,
        public readonly string $ip,
        public array $routeParams = [],
        public array $attributes = [],   // datos añadidos por middleware (user, workspace, token)
    ) {}

    public static function capture(): self
    {
        $uri = (string) ($_SERVER['REQUEST_URI'] ?? '/');
        $path = '/' . trim((string) parse_url($uri, PHP_URL_PATH), '/');

        $headers = [];
        foreach ($_SERVER as $key => $value) {
            if (str_starts_with($key, 'HTTP_')) {
                $headers[strtolower(str_replace('_', '-', substr($key, 5)))] = (string) $value;
            }
        }
        foreach (['CONTENT_TYPE' => 'content-type', 'CONTENT_LENGTH' => 'content-length'] as $k => $h) {
            if (isset($_SERVER[$k])) {
                $headers[$h] = (string) $_SERVER[$k];
            }
        }
        // LiteSpeed/Apache a veces no exponen Authorization como HTTP_AUTHORIZATION
        if (!isset($headers['authorization']) && isset($_SERVER['REDIRECT_HTTP_AUTHORIZATION'])) {
            $headers['authorization'] = (string) $_SERVER['REDIRECT_HTTP_AUTHORIZATION'];
        }

        $method = strtoupper((string) ($_SERVER['REQUEST_METHOD'] ?? 'GET'));
        if ($method === 'POST' && isset($_POST['_method'])) {
            $override = strtoupper((string) $_POST['_method']);
            if (in_array($override, ['PUT', 'PATCH', 'DELETE'], true)) {
                $method = $override;
            }
        }

        return new self(
            method: $method,
            path: $path,
            query: $_GET,
            post: $_POST,
            headers: $headers,
            rawBody: (string) file_get_contents('php://input'),
            files: $_FILES,
            ip: (string) ($_SERVER['REMOTE_ADDR'] ?? '0.0.0.0'),
        );
    }

    public function header(string $name, ?string $default = null): ?string
    {
        return $this->headers[strtolower($name)] ?? $default;
    }

    public function bearerToken(): ?string
    {
        $auth = $this->header('authorization', '');
        return preg_match('/^Bearer\s+(\S+)$/i', (string) $auth, $m) ? $m[1] : null;
    }

    public function isJson(): bool
    {
        return str_contains((string) $this->header('content-type', ''), 'application/json');
    }

    public function json(): array
    {
        if ($this->json === null) {
            $decoded = json_decode($this->rawBody, true);
            $this->json = is_array($decoded) ? $decoded : [];
        }
        return $this->json;
    }

    /** Busca en JSON, POST y querystring (en ese orden). */
    public function input(string $key, mixed $default = null): mixed
    {
        $source = $this->isJson() ? $this->json() : $this->post;
        return $source[$key] ?? $this->query[$key] ?? $default;
    }

    public function param(string $key, ?string $default = null): ?string
    {
        return $this->routeParams[$key] ?? $default;
    }
}
