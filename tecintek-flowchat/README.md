# Tecintek FlowChat

Plataforma self-hosted de automatización conversacional (WhatsApp Cloud API, Instagram, Messenger y Webchat) que reemplaza a ManyChat y corre en **hosting compartido Hostinger Business** (LiteSpeed + PHP 8.3 + MariaDB 10.5). No necesita VPS, Node.js en segundo plano ni Redis.

## Estado

| Fase | Contenido | Estado |
|------|-----------|--------|
| 1 | Estructura, `schema.sql`, configuración, PDO, autoloader, router | ✅ |
| 2 | Motor de flujos (máquina de estados) | ⏳ |
| 3 | Webhooks de Meta + `cron_worker.php` | ⏳ |
| 4 | Flow Builder, Live Chat Inbox, Contactos/Tags, `widget.js` | ⏳ |
| 5 | Instalador web y guía de despliegue en hPanel | ⏳ |

## Estructura

```
tecintek-flowchat/
├── .env.example          # plantilla de configuración (copiar a .env; nunca a Git)
├── .htaccess             # salvavidas: si todo queda en public_html, redirige a /public y bloquea el resto
├── composer.json         # PSR-4 App\ => app/ (opcional: hay autoloader de respaldo)
├── app/                  # código PHP: NO accesible desde la web
│   ├── bootstrap.php     # arranque común HTTP + CLI (env, config, errores, UTC)
│   ├── routes.php        # tabla de rutas
│   ├── Core/             # mini framework propio (~1.000 líneas, sin dependencias)
│   │   ├── Autoloader.php    PSR-4 de respaldo si no hay vendor/
│   │   ├── Env.php           lector de .env
│   │   ├── Config.php        config('database.host')
│   │   ├── Database.php      PDO singleton, prepared statements, reconexión, transacciones
│   │   ├── Crypto.php        libsodium para tokens de Meta + validación X-Hub-Signature-256
│   │   ├── Logger.php        logs JSON diarios con redacción de secretos
│   │   ├── Request.php       conserva el body crudo (firma de Meta), Bearer token
│   │   ├── Response.php      sendAndFinish() => litespeed_finish_request()
│   │   ├── Router.php        rutas con parámetros, grupos y middleware
│   │   └── helpers.php
│   ├── Controllers/      # (Fase 3-4) Webhook, Inbox, Flow, Contact, Api\V1\...
│   ├── Middleware/       # (Fase 4) Auth, Csrf, ApiToken, RateLimit
│   ├── Models/           # (Fase 2+) repositorios finos sobre Database
│   ├── Engine/           # (Fase 2) FlowEngine, NodeHandlers/, ConditionEvaluator, VariableResolver
│   ├── Services/
│   │   └── Channels/     # (Fase 3) WhatsAppClient, MessengerClient, InstagramClient, WebchatChannel
│   └── Views/            # plantillas PHP del panel
├── bin/                  # scripts CLI (bloqueados a la web)
│   ├── keygen.php        # genera APP_KEY
│   └── cron_worker.php   # (Fase 3) procesa scheduled_jobs cada minuto
├── config/               # app.php, database.php, meta.php, queue.php
├── database/
│   ├── schema.sql        # esquema completo MariaDB 10.5
│   └── migrations/       # cambios futuros versionados
├── public/               # ⇦ DocumentRoot (lo único expuesto)
│   ├── index.php         # front controller
│   ├── .htaccess         # HTTPS, Authorization header, rewrite, caché
│   ├── assets/           # css/js/img del panel
│   └── dist/             # (Fase 4) Flow Builder compilado + widget.js
└── storage/              # escribible por PHP, denegado a la web
    ├── logs/  cache/  uploads/  tmp/  sessions/
```

## Decisiones de arquitectura

- **Sin framework pesado**: un núcleo propio pequeño mantiene el consumo de RAM bajo en hosting compartido y evita depender de Composer en el servidor.
- **Webhooks rápidos**: cada evento de Meta se guarda en `webhook_inbox` (idempotente por `sha256` del body), se responde `200` y se procesa tras `litespeed_finish_request()`. Si algo falla, el cron reprocesa lo pendiente.
- **Cola en MariaDB**: `scheduled_jobs` con `unique_key` (deduplicación), `priority`, reintentos con backoff y bloqueo `locked_by/locked_at`. El worker toma trabajos con `SELECT ... FOR UPDATE SKIP LOCKED` (MariaDB 10.6+) o, en 10.5, con un `UPDATE ... WHERE status='pending' LIMIT n` atómico que reclama trabajos por `locked_by`.
- **Una sola sesión de flujo viva por contacto y canal**: lo garantiza la BD con la columna generada `contact_sessions.active_lock` + índice único (no depende del código).
- **Triggers indexados**: al publicar un flujo, sus disparadores se copian a `flow_triggers`; el webhook resuelve qué flujo arrancar con una consulta indexada, sin leer el JSON del grafo.
- **Versionado de flujos**: `draft_graph` (lo que editas) vs `published_graph` + `flow_versions`; las sesiones en curso guardan `flow_version` y no se rompen al republicar.
- **Ventana de 24h de Meta**: `contacts.last_inbound_at` y `contact_channels.last_inbound_at` deciden si se puede enviar mensaje libre o hace falta plantilla.
- **Secretos cifrados**: los access tokens de Meta se guardan en `channels.credentials_enc` cifrados con libsodium usando `APP_KEY`.
- **Fechas en UTC** en BD; la zona del workspace (`America/Bogota` por defecto) se aplica al mostrar y en las condiciones de horario laboral.

## Prueba local rápida

```bash
cp .env.example .env            # completar DB_*
php bin/keygen.php --write
mysql -u USER -p DB < database/schema.sql
php -S 127.0.0.1:8080 -t public public/index.php
curl http://127.0.0.1:8080/health
```
