<?php

declare(strict_types=1);

namespace App\Core;

final class Response
{
    /** @param array<string,string> $headers */
    public function __construct(
        private string $body = '',
        private int $status = 200,
        private array $headers = [],
    ) {}

    public static function json(mixed $data, int $status = 200, array $headers = []): self
    {
        return new self(
            json_encode($data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR),
            $status,
            ['Content-Type' => 'application/json; charset=utf-8'] + $headers
        );
    }

    public static function text(string $text, int $status = 200): self
    {
        return new self($text, $status, ['Content-Type' => 'text/plain; charset=utf-8']);
    }

    public static function html(string $html, int $status = 200): self
    {
        return new self($html, $status, ['Content-Type' => 'text/html; charset=utf-8']);
    }

    public static function redirect(string $url, int $status = 302): self
    {
        return new self('', $status, ['Location' => $url]);
    }

    public static function noContent(): self
    {
        return new self('', 204);
    }

    public function withHeader(string $name, string $value): self
    {
        $clone = clone $this;
        $clone->headers[$name] = $value;
        return $clone;
    }

    public function status(): int
    {
        return $this->status;
    }

    public function send(): void
    {
        if (!headers_sent()) {
            http_response_code($this->status);
            $defaults = [
                'X-Content-Type-Options' => 'nosniff',
                'X-Frame-Options'        => 'SAMEORIGIN',
                'Referrer-Policy'        => 'strict-origin-when-cross-origin',
            ];
            foreach ($this->headers + $defaults as $name => $value) {
                header($name . ': ' . $value, true);
            }
        }
        echo $this->body;
    }

    /**
     * Envía la respuesta y cierra la conexión con el cliente para seguir procesando
     * en segundo plano dentro del mismo request (clave para webhooks de Meta:
     * responder 200 en < 1s y luego ejecutar el flujo).
     */
    public function sendAndFinish(): void
    {
        ignore_user_abort(true);
        $this->send();
        if (function_exists('litespeed_finish_request')) {
            litespeed_finish_request();          // LiteSpeed (Hostinger)
        } elseif (function_exists('fastcgi_finish_request')) {
            fastcgi_finish_request();            // PHP-FPM
        } else {
            @ob_end_flush();
            flush();
        }
    }
}
