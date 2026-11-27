<?php

declare(strict_types=1);

namespace App\Core;

use Closure;
use RuntimeException;

/**
 * Router ligero con parámetros ({id}, {id:\d+}), grupos con prefijo y middleware.
 * Handler: Closure(Request): Response | [ControllerClass::class, 'method'].
 * Middleware: clase con método handle(Request $r, Closure $next): Response.
 */
final class Router
{
    /** @var list<array{method:string, regex:string, params:list<string>, handler:mixed, middleware:list<string>}> */
    private array $routes = [];
    private string $groupPrefix = '';
    /** @var list<string> */
    private array $groupMiddleware = [];

    public function get(string $path, mixed $handler, array $mw = []): void    { $this->add('GET', $path, $handler, $mw); }
    public function post(string $path, mixed $handler, array $mw = []): void   { $this->add('POST', $path, $handler, $mw); }
    public function put(string $path, mixed $handler, array $mw = []): void    { $this->add('PUT', $path, $handler, $mw); }
    public function patch(string $path, mixed $handler, array $mw = []): void  { $this->add('PATCH', $path, $handler, $mw); }
    public function delete(string $path, mixed $handler, array $mw = []): void { $this->add('DELETE', $path, $handler, $mw); }

    public function group(string $prefix, array $middleware, Closure $routes): void
    {
        [$prevPrefix, $prevMw] = [$this->groupPrefix, $this->groupMiddleware];
        $this->groupPrefix .= '/' . trim($prefix, '/');
        $this->groupMiddleware = array_merge($this->groupMiddleware, $middleware);
        $routes($this);
        [$this->groupPrefix, $this->groupMiddleware] = [$prevPrefix, $prevMw];
    }

    private function add(string $method, string $path, mixed $handler, array $middleware): void
    {
        $full = '/' . trim($this->groupPrefix . '/' . trim($path, '/'), '/');
        $params = [];
        $regex = preg_replace_callback(
            '#\{([a-zA-Z_][a-zA-Z0-9_]*)(?::([^}]+))?\}#',
            static function (array $m) use (&$params): string {
                $params[] = $m[1];
                return '(' . ($m[2] ?? '[^/]+') . ')';
            },
            $full
        );
        $this->routes[] = [
            'method'     => $method,
            'regex'      => '#^' . $regex . '$#',
            'params'     => $params,
            'handler'    => $handler,
            'middleware' => array_merge($this->groupMiddleware, $middleware),
        ];
    }

    public function dispatch(Request $request): Response
    {
        $methodMismatch = false;
        $method = $request->method === 'HEAD' ? 'GET' : $request->method;

        foreach ($this->routes as $route) {
            if (!preg_match($route['regex'], $request->path, $matches)) {
                continue;
            }
            if ($route['method'] !== $method) {
                $methodMismatch = true;
                continue;
            }
            array_shift($matches);
            $request->routeParams = array_combine($route['params'], $matches) ?: [];

            $core = fn (Request $r): Response => $this->invoke($route['handler'], $r);
            $pipeline = array_reduce(
                array_reverse($route['middleware']),
                static fn (Closure $next, string $mw) => static fn (Request $r): Response => (new $mw())->handle($r, $next),
                $core
            );
            return $pipeline($request);
        }

        return $methodMismatch
            ? Response::json(['error' => 'Método no permitido'], 405)
            : Response::json(['error' => 'Ruta no encontrada'], 404);
    }

    private function invoke(mixed $handler, Request $request): Response
    {
        if ($handler instanceof Closure) {
            return $handler($request);
        }
        if (is_array($handler) && count($handler) === 2) {
            [$class, $action] = $handler;
            $controller = new $class();
            if (!method_exists($controller, $action)) {
                throw new RuntimeException("Acción {$class}::{$action} no existe");
            }
            return $controller->{$action}($request);
        }
        throw new RuntimeException('Handler de ruta inválido');
    }
}
