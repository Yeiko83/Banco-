<?php

declare(strict_types=1);

/**
 * Front controller único. LiteSpeed reescribe todo lo que no sea un archivo
 * estático hacia aquí (ver public/.htaccess).
 */

require dirname(__DIR__) . '/app/bootstrap.php';

use App\Core\Request;
use App\Core\Router;

$router = new Router();
(require BASE_PATH . '/app/routes.php')($router);

$router->dispatch(Request::capture())->send();
