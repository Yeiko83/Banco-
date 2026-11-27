-- =============================================================================
--  Tecintek FlowChat — Esquema de base de datos
--  Motor objetivo: MariaDB 10.5+ (InnoDB, utf8mb4)
--  Convenciones:
--    * Todas las fechas se guardan en UTC (la conexión PDO fija time_zone='+00:00').
--    * JSON en MariaDB es alias de LONGTEXT con CHECK(JSON_VALID) automático.
--    * Soft-delete sólo donde aporta valor (contacts, flows).
--    * Multi-workspace: todo dato de negocio cuelga de workspace_id.
-- =============================================================================

SET NAMES utf8mb4;
SET time_zone = '+00:00';
SET FOREIGN_KEY_CHECKS = 0;

-- -----------------------------------------------------------------------------
-- 0. Control de versiones del esquema
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS schema_migrations (
    version     VARCHAR(64)  NOT NULL,
    applied_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (version)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================================================
-- 1. IDENTIDAD, WORKSPACES Y ACCESO
-- =============================================================================

CREATE TABLE IF NOT EXISTS workspaces (
    id                   INT UNSIGNED  NOT NULL AUTO_INCREMENT,
    name                 VARCHAR(120)  NOT NULL,
    slug                 VARCHAR(120)  NOT NULL,
    timezone             VARCHAR(64)   NOT NULL DEFAULT 'America/Bogota',
    locale               VARCHAR(10)   NOT NULL DEFAULT 'es',
    -- {"mon":[["08:00","18:00"]],"tue":[...],...,"holidays":["2026-12-25"]}
    business_hours       JSON          NULL,
    -- Horas para reactivar el bot automáticamente tras pasar a modo humano
    human_takeover_hours SMALLINT UNSIGNED NOT NULL DEFAULT 24,
    settings             JSON          NULL,
    created_at           DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at           DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_workspaces_slug (slug)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS users (
    id               INT UNSIGNED  NOT NULL AUTO_INCREMENT,
    name             VARCHAR(120)  NOT NULL,
    email            VARCHAR(190)  NOT NULL,
    password_hash    VARCHAR(255)  NOT NULL,            -- password_hash(PASSWORD_ARGON2ID | BCRYPT)
    is_superadmin    TINYINT(1)    NOT NULL DEFAULT 0,
    avatar_url       VARCHAR(500)  NULL,
    totp_secret      VARCHAR(255)  NULL,                -- cifrado (Crypto::encrypt)
    status           ENUM('active','disabled') NOT NULL DEFAULT 'active',
    last_login_at    DATETIME      NULL,
    last_seen_at     DATETIME      NULL,                -- presencia en Inbox (polling)
    remember_token   CHAR(64)      NULL,                -- sha256 del token
    created_at       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_users_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS workspace_users (
    workspace_id INT UNSIGNED NOT NULL,
    user_id      INT UNSIGNED NOT NULL,
    role         ENUM('owner','admin','editor','agent','viewer') NOT NULL DEFAULT 'agent',
    created_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (workspace_id, user_id),
    KEY idx_wu_user (user_id),
    CONSTRAINT fk_wu_workspace FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
    CONSTRAINT fk_wu_user      FOREIGN KEY (user_id)      REFERENCES users(id)      ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tokens Bearer para la API REST propia. Sólo se guarda el hash SHA-256.
CREATE TABLE IF NOT EXISTS api_tokens (
    id            INT UNSIGNED  NOT NULL AUTO_INCREMENT,
    workspace_id  INT UNSIGNED  NOT NULL,
    created_by    INT UNSIGNED  NULL,
    name          VARCHAR(120)  NOT NULL,
    token_prefix  CHAR(8)       NOT NULL,                -- primeros 8 chars visibles en UI
    token_hash    CHAR(64)      NOT NULL,                -- hash('sha256', token)
    abilities     JSON          NULL,                    -- ["contacts:write","flows:trigger"]
    last_used_at  DATETIME      NULL,
    last_used_ip  VARCHAR(45)   NULL,
    expires_at    DATETIME      NULL,
    revoked_at    DATETIME      NULL,
    created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_api_tokens_hash (token_hash),
    KEY idx_api_tokens_ws (workspace_id),
    CONSTRAINT fk_api_tokens_ws   FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
    CONSTRAINT fk_api_tokens_user FOREIGN KEY (created_by)   REFERENCES users(id)      ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS login_attempts (
    id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    email       VARCHAR(190)    NOT NULL,
    ip          VARCHAR(45)     NOT NULL,
    success     TINYINT(1)      NOT NULL DEFAULT 0,
    created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_login_email_time (email, created_at),
    KEY idx_login_ip_time (ip, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================================================
-- 2. CANALES (WhatsApp Cloud API, Instagram, Messenger, Webchat)
-- =============================================================================

CREATE TABLE IF NOT EXISTS channels (
    id                  INT UNSIGNED  NOT NULL AUTO_INCREMENT,
    workspace_id        INT UNSIGNED  NOT NULL,
    type                ENUM('whatsapp','instagram','messenger','webchat') NOT NULL,
    name                VARCHAR(120)  NOT NULL,
    -- WA: phone_number_id | FB: page_id | IG: ig_business_account_id | Web: public widget key
    external_id         VARCHAR(64)   NOT NULL,
    display_identifier  VARCHAR(120)  NULL,               -- +57 300..., @usuario, nombre de página
    waba_id             VARCHAR(64)   NULL,               -- WhatsApp Business Account ID (templates)
    -- Access token, app secret, etc. SIEMPRE cifrados con Crypto::encrypt (libsodium)
    credentials_enc     TEXT          NULL,
    graph_api_version   VARCHAR(10)   NOT NULL DEFAULT 'v21.0',
    status              ENUM('active','disconnected','error') NOT NULL DEFAULT 'active',
    last_error          VARCHAR(500)  NULL,
    -- Webchat: colores, saludo, dominios permitidos (CORS), etc.
    settings            JSON          NULL,
    -- Límite de envío para broadcasts (mensajes/minuto)
    rate_limit_per_min  SMALLINT UNSIGNED NOT NULL DEFAULT 60,
    created_at          DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_channels_type_ext (type, external_id),
    KEY idx_channels_ws (workspace_id),
    CONSTRAINT fk_channels_ws FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Plantillas de WhatsApp sincronizadas desde Meta
CREATE TABLE IF NOT EXISTS message_templates (
    id            INT UNSIGNED  NOT NULL AUTO_INCREMENT,
    workspace_id  INT UNSIGNED  NOT NULL,
    channel_id    INT UNSIGNED  NOT NULL,
    meta_id       VARCHAR(64)   NULL,
    name          VARCHAR(512)  NOT NULL,
    language      VARCHAR(15)   NOT NULL,
    category      ENUM('MARKETING','UTILITY','AUTHENTICATION') NOT NULL DEFAULT 'UTILITY',
    status        VARCHAR(30)   NOT NULL DEFAULT 'PENDING',   -- APPROVED, REJECTED, PAUSED...
    components    JSON          NOT NULL,
    synced_at     DATETIME      NULL,
    created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_tpl_channel_name_lang (channel_id, name(191), language),
    KEY idx_tpl_ws (workspace_id),
    CONSTRAINT fk_tpl_ws      FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
    CONSTRAINT fk_tpl_channel FOREIGN KEY (channel_id)   REFERENCES channels(id)   ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================================================
-- 3. CRM: CONTACTOS, TAGS Y CUSTOM FIELDS
-- =============================================================================

CREATE TABLE IF NOT EXISTS contacts (
    id                   BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    workspace_id         INT UNSIGNED    NOT NULL,
    first_name           VARCHAR(120)    NULL,
    last_name            VARCHAR(120)    NULL,
    phone                VARCHAR(32)     NULL,               -- E.164 sin '+': 573001234567
    email                VARCHAR(190)    NULL,
    avatar_url           VARCHAR(1000)   NULL,
    locale               VARCHAR(10)     NULL,
    timezone             VARCHAR(64)     NULL,
    gender               ENUM('male','female','other','unknown') NOT NULL DEFAULT 'unknown',
    status               ENUM('active','unsubscribed','blocked') NOT NULL DEFAULT 'active',
    -- Live Chat Handover
    bot_paused           TINYINT(1)      NOT NULL DEFAULT 0,
    bot_paused_until     DATETIME        NULL,                -- reactivación automática
    assigned_user_id     INT UNSIGNED    NULL,
    -- Atribución / growth tools
    source               VARCHAR(40)     NULL,                -- whatsapp|instagram|messenger|webchat|api|import
    first_ref            VARCHAR(120)    NULL,
    last_ref             VARCHAR(120)    NULL,
    -- Actividad
    last_inbound_at      DATETIME        NULL,                -- base de la ventana de 24h de Meta
    last_outbound_at     DATETIME        NULL,
    last_interaction_at  DATETIME        NULL,
    opted_in_at          DATETIME        NULL,
    created_at           DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at           DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at           DATETIME        NULL,
    PRIMARY KEY (id),
    KEY idx_contacts_ws_phone (workspace_id, phone),
    KEY idx_contacts_ws_email (workspace_id, email),
    KEY idx_contacts_ws_last (workspace_id, last_interaction_at),
    KEY idx_contacts_bot_until (bot_paused, bot_paused_until),
    KEY idx_contacts_assigned (assigned_user_id),
    FULLTEXT KEY ft_contacts_name (first_name, last_name, email, phone),
    CONSTRAINT fk_contacts_ws   FOREIGN KEY (workspace_id)     REFERENCES workspaces(id) ON DELETE CASCADE,
    CONSTRAINT fk_contacts_user FOREIGN KEY (assigned_user_id) REFERENCES users(id)      ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Identidad omnicanal: un contacto puede tener wa_id, PSID (FB), IGSID e ID de visitante web.
CREATE TABLE IF NOT EXISTS contact_channels (
    id                BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    contact_id        BIGINT UNSIGNED NOT NULL,
    channel_id        INT UNSIGNED    NOT NULL,
    external_user_id  VARCHAR(128)    NOT NULL,     -- wa_id | PSID | IGSID | visitor uuid
    username          VARCHAR(120)    NULL,          -- @usuario de IG
    profile           JSON            NULL,          -- datos crudos del perfil devueltos por Meta
    last_inbound_at   DATETIME        NULL,          -- ventana 24h por canal
    created_at        DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at        DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_cc_channel_user (channel_id, external_user_id),
    KEY idx_cc_contact (contact_id),
    CONSTRAINT fk_cc_contact FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE CASCADE,
    CONSTRAINT fk_cc_channel FOREIGN KEY (channel_id) REFERENCES channels(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS tags (
    id            INT UNSIGNED  NOT NULL AUTO_INCREMENT,
    workspace_id  INT UNSIGNED  NOT NULL,
    name          VARCHAR(80)   NOT NULL,
    color         CHAR(7)       NOT NULL DEFAULT '#6366F1',
    created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_tags_ws_name (workspace_id, name),
    CONSTRAINT fk_tags_ws FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS contact_tags (
    contact_id  BIGINT UNSIGNED NOT NULL,
    tag_id      INT UNSIGNED    NOT NULL,
    added_by    ENUM('flow','agent','api','import','broadcast') NOT NULL DEFAULT 'flow',
    created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (contact_id, tag_id),
    KEY idx_ct_tag (tag_id, contact_id),                     -- segmentación por tag (broadcasts)
    CONSTRAINT fk_ct_contact FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE CASCADE,
    CONSTRAINT fk_ct_tag     FOREIGN KEY (tag_id)     REFERENCES tags(id)     ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS custom_fields (
    id             INT UNSIGNED  NOT NULL AUTO_INCREMENT,
    workspace_id   INT UNSIGNED  NOT NULL,
    field_key      VARCHAR(64)   NOT NULL,          -- usado en {{custom.empresa}}
    label          VARCHAR(120)  NOT NULL,
    type           ENUM('text','number','email','phone','date','datetime','boolean','url','file','json') NOT NULL DEFAULT 'text',
    default_value  TEXT          NULL,
    description    VARCHAR(255)  NULL,
    created_at     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_cf_ws_key (workspace_id, field_key),
    CONSTRAINT fk_cf_ws FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Valores tipados (EAV). value_number / value_date permiten comparar en nodos Condición.
CREATE TABLE IF NOT EXISTS contact_field_values (
    contact_id    BIGINT UNSIGNED NOT NULL,
    field_id      INT UNSIGNED    NOT NULL,
    value_text    TEXT            NULL,
    value_number  DECIMAL(20,6)   NULL,
    value_date    DATETIME        NULL,
    updated_at    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (contact_id, field_id),
    KEY idx_cfv_field_num (field_id, value_number),
    KEY idx_cfv_field_date (field_id, value_date),
    CONSTRAINT fk_cfv_contact FOREIGN KEY (contact_id) REFERENCES contacts(id)      ON DELETE CASCADE,
    CONSTRAINT fk_cfv_field   FOREIGN KEY (field_id)   REFERENCES custom_fields(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS contact_notes (
    id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    contact_id  BIGINT UNSIGNED NOT NULL,
    user_id     INT UNSIGNED    NULL,
    body        TEXT            NOT NULL,
    created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_notes_contact (contact_id, created_at),
    CONSTRAINT fk_notes_contact FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE CASCADE,
    CONSTRAINT fk_notes_user    FOREIGN KEY (user_id)    REFERENCES users(id)    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================================================
-- 4. LIVE CHAT INBOX: CONVERSACIONES Y MENSAJES
-- =============================================================================

CREATE TABLE IF NOT EXISTS conversations (
    id                    BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    workspace_id          INT UNSIGNED    NOT NULL,
    contact_id            BIGINT UNSIGNED NOT NULL,
    channel_id            INT UNSIGNED    NOT NULL,
    status                ENUM('open','pending','closed') NOT NULL DEFAULT 'open',
    assigned_user_id      INT UNSIGNED    NULL,
    unread_count          INT UNSIGNED    NOT NULL DEFAULT 0,
    needs_human           TINYINT(1)      NOT NULL DEFAULT 0,      -- marcado por nodo "Handover"
    last_message_id       BIGINT UNSIGNED NULL,
    last_message_at       DATETIME        NULL,
    last_message_preview  VARCHAR(255)    NULL,
    created_at            DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at            DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_conv_contact_channel (contact_id, channel_id),
    -- Listado del Inbox ordenado y polling por "updated_at > :since"
    KEY idx_conv_inbox (workspace_id, status, last_message_at),
    KEY idx_conv_ws_updated (workspace_id, updated_at),
    KEY idx_conv_assigned (assigned_user_id, status),
    CONSTRAINT fk_conv_ws      FOREIGN KEY (workspace_id)     REFERENCES workspaces(id) ON DELETE CASCADE,
    CONSTRAINT fk_conv_contact FOREIGN KEY (contact_id)       REFERENCES contacts(id)   ON DELETE CASCADE,
    CONSTRAINT fk_conv_channel FOREIGN KEY (channel_id)       REFERENCES channels(id)   ON DELETE CASCADE,
    CONSTRAINT fk_conv_user    FOREIGN KEY (assigned_user_id) REFERENCES users(id)      ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS messages (
    id               BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    workspace_id     INT UNSIGNED    NOT NULL,
    conversation_id  BIGINT UNSIGNED NOT NULL,
    contact_id       BIGINT UNSIGNED NOT NULL,
    channel_id       INT UNSIGNED    NOT NULL,
    direction        ENUM('in','out') NOT NULL,
    sender_type      ENUM('contact','bot','agent','system','api','broadcast') NOT NULL,
    user_id          INT UNSIGNED    NULL,                         -- agente que respondió
    type             ENUM('text','image','audio','video','document','sticker','location','contacts',
                          'interactive_buttons','interactive_list','button_reply','list_reply',
                          'template','comment','reaction','system','unsupported') NOT NULL DEFAULT 'text',
    body             TEXT            NULL,                          -- texto plano / caption
    payload          JSON            NULL,                          -- estructura completa (botones, media, etc.)
    media_id         BIGINT UNSIGNED NULL,
    external_id      VARCHAR(191)    NULL,                          -- wamid / mid de Meta
    reply_to_id      BIGINT UNSIGNED NULL,
    status           ENUM('queued','sent','delivered','read','failed','received') NOT NULL DEFAULT 'queued',
    error_code       VARCHAR(32)     NULL,
    error_message    VARCHAR(500)    NULL,
    flow_id          INT UNSIGNED    NULL,                          -- trazabilidad del motor
    node_id          VARCHAR(64)     NULL,
    broadcast_id     INT UNSIGNED    NULL,
    sent_at          DATETIME        NULL,
    delivered_at     DATETIME        NULL,
    read_at          DATETIME        NULL,
    created_at       DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    -- Polling del chat abierto: WHERE conversation_id=? AND id > :last_id
    KEY idx_msg_conv_id (conversation_id, id),
    KEY idx_msg_ws_id (workspace_id, id),
    KEY idx_msg_contact (contact_id, created_at),
    UNIQUE KEY uq_msg_channel_external (channel_id, external_id),  -- idempotencia de webhooks
    KEY idx_msg_broadcast (broadcast_id),
    CONSTRAINT fk_msg_ws      FOREIGN KEY (workspace_id)    REFERENCES workspaces(id)    ON DELETE CASCADE,
    CONSTRAINT fk_msg_conv    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    CONSTRAINT fk_msg_contact FOREIGN KEY (contact_id)      REFERENCES contacts(id)      ON DELETE CASCADE,
    CONSTRAINT fk_msg_channel FOREIGN KEY (channel_id)      REFERENCES channels(id)      ON DELETE CASCADE,
    CONSTRAINT fk_msg_user    FOREIGN KEY (user_id)         REFERENCES users(id)         ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS media_files (
    id             BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    workspace_id   INT UNSIGNED    NOT NULL,
    original_name  VARCHAR(255)    NULL,
    mime_type      VARCHAR(120)    NOT NULL,
    size_bytes     INT UNSIGNED    NOT NULL DEFAULT 0,
    storage_path   VARCHAR(500)    NULL,          -- relativo a /storage/uploads (no público)
    public_token   CHAR(40)        NULL,          -- URL firmada /media/{token} para Meta
    sha256         CHAR(64)        NULL,
    -- Caché de IDs de media subidos a Meta: {"<channel_id>":{"id":"...","expires":"..."}}
    meta_ids       JSON            NULL,
    source         ENUM('upload','inbound','flow','api') NOT NULL DEFAULT 'upload',
    created_at     DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_media_token (public_token),
    KEY idx_media_ws_sha (workspace_id, sha256),
    CONSTRAINT fk_media_ws FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS canned_responses (
    id            INT UNSIGNED  NOT NULL AUTO_INCREMENT,
    workspace_id  INT UNSIGNED  NOT NULL,
    shortcut      VARCHAR(40)   NOT NULL,          -- "/precios"
    title         VARCHAR(120)  NOT NULL,
    body          TEXT          NOT NULL,
    created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_canned_ws_short (workspace_id, shortcut),
    CONSTRAINT fk_canned_ws FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================================================
-- 5. MOTOR DE FLUJOS
-- =============================================================================

CREATE TABLE IF NOT EXISTS flow_folders (
    id            INT UNSIGNED NOT NULL AUTO_INCREMENT,
    workspace_id  INT UNSIGNED NOT NULL,
    name          VARCHAR(120) NOT NULL,
    created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_ff_ws (workspace_id),
    CONSTRAINT fk_ff_ws FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS flows (
    id                 INT UNSIGNED  NOT NULL AUTO_INCREMENT,
    workspace_id       INT UNSIGNED  NOT NULL,
    folder_id          INT UNSIGNED  NULL,
    name               VARCHAR(150)  NOT NULL,
    description        VARCHAR(500)  NULL,
    status             ENUM('draft','published','paused','archived') NOT NULL DEFAULT 'draft',
    draft_graph        JSON          NULL,            -- export de Drawflow mientras se edita
    published_graph    JSON          NULL,            -- grafo normalizado que ejecuta el motor
    published_version  INT UNSIGNED  NOT NULL DEFAULT 0,
    -- Métricas rápidas
    runs_count         INT UNSIGNED  NOT NULL DEFAULT 0,
    completed_count    INT UNSIGNED  NOT NULL DEFAULT 0,
    created_by         INT UNSIGNED  NULL,
    published_at       DATETIME      NULL,
    created_at         DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at         DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at         DATETIME      NULL,
    PRIMARY KEY (id),
    KEY idx_flows_ws_status (workspace_id, status),
    CONSTRAINT fk_flows_ws     FOREIGN KEY (workspace_id) REFERENCES workspaces(id)   ON DELETE CASCADE,
    CONSTRAINT fk_flows_folder FOREIGN KEY (folder_id)    REFERENCES flow_folders(id) ON DELETE SET NULL,
    CONSTRAINT fk_flows_user   FOREIGN KEY (created_by)   REFERENCES users(id)        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Historial inmutable de publicaciones (rollback y sesiones que corren sobre versión antigua)
CREATE TABLE IF NOT EXISTS flow_versions (
    id            INT UNSIGNED  NOT NULL AUTO_INCREMENT,
    flow_id       INT UNSIGNED  NOT NULL,
    version       INT UNSIGNED  NOT NULL,
    graph         JSON          NOT NULL,
    published_by  INT UNSIGNED  NULL,
    created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_fv_flow_version (flow_id, version),
    CONSTRAINT fk_fv_flow FOREIGN KEY (flow_id)      REFERENCES flows(id) ON DELETE CASCADE,
    CONSTRAINT fk_fv_user FOREIGN KEY (published_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Índice desnormalizado de disparadores. Se regenera al publicar un flujo
-- para que el webhook resuelva el trigger con una consulta indexada (sin parsear JSON).
CREATE TABLE IF NOT EXISTS flow_triggers (
    id            INT UNSIGNED  NOT NULL AUTO_INCREMENT,
    workspace_id  INT UNSIGNED  NOT NULL,
    flow_id       INT UNSIGNED  NOT NULL,
    node_id       VARCHAR(64)   NOT NULL,               -- nodo trigger dentro del grafo
    type          ENUM('keyword','comment','first_message','ref','webhook','default_reply','api','story_reply') NOT NULL,
    channel_type  ENUM('any','whatsapp','instagram','messenger','webchat') NOT NULL DEFAULT 'any',
    channel_id    INT UNSIGNED  NULL,                   -- NULL = todos los canales del tipo
    match_type    ENUM('exact','contains','starts_with','regex','any') NOT NULL DEFAULT 'exact',
    keyword       VARCHAR(191)  NULL,                   -- normalizado: minúsculas, sin tildes, trim
    post_id       VARCHAR(64)   NULL,                   -- comment-to-DM: ID de post/reel (NULL = cualquiera)
    ref_code      VARCHAR(120)  NULL,                   -- wa.me/?text=ref / m.me/?ref=
    webhook_key   CHAR(32)      NULL,                   -- /hooks/in/{webhook_key}
    -- Config adicional: respuesta pública al comentario, ventanas, etc.
    config        JSON          NULL,
    priority      SMALLINT      NOT NULL DEFAULT 100,   -- menor = se evalúa primero
    is_active     TINYINT(1)    NOT NULL DEFAULT 1,
    created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_ft_lookup (workspace_id, is_active, type, match_type, keyword),
    KEY idx_ft_comment (workspace_id, type, post_id),
    UNIQUE KEY uq_ft_ref (workspace_id, ref_code),
    UNIQUE KEY uq_ft_webhook (webhook_key),
    KEY idx_ft_flow (flow_id),
    CONSTRAINT fk_ft_ws      FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
    CONSTRAINT fk_ft_flow    FOREIGN KEY (flow_id)      REFERENCES flows(id)      ON DELETE CASCADE,
    CONSTRAINT fk_ft_channel FOREIGN KEY (channel_id)   REFERENCES channels(id)   ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Estado de la máquina de estados por contacto.
-- Sólo puede existir UNA sesión viva por contacto+canal (garantizado por active_lock).
CREATE TABLE IF NOT EXISTS contact_sessions (
    id               BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    workspace_id     INT UNSIGNED    NOT NULL,
    contact_id       BIGINT UNSIGNED NOT NULL,
    channel_id       INT UNSIGNED    NOT NULL,
    flow_id          INT UNSIGNED    NOT NULL,
    flow_version     INT UNSIGNED    NOT NULL,
    current_node_id  VARCHAR(64)     NULL,
    status           ENUM('running','waiting_input','waiting_delay','completed','cancelled','expired','error') NOT NULL DEFAULT 'running',
    -- Nodo User Input pendiente: {"node_id":"..","field":"email","validation":"email","retries":1,"max_retries":3}
    waiting_for      JSON            NULL,
    -- Variables de ejecución ({{flow.xxx}}, respuestas de webhooks, etc.)
    context          JSON            NULL,
    steps_executed   INT UNSIGNED    NOT NULL DEFAULT 0,   -- protección contra bucles infinitos
    trigger_id       INT UNSIGNED    NULL,
    expires_at       DATETIME        NULL,                 -- timeout del input (p. ej. 24h)
    last_error       VARCHAR(500)    NULL,
    started_at       DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at       DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    ended_at         DATETIME        NULL,
    active_lock      TINYINT AS (IF(status IN ('running','waiting_input','waiting_delay'), 1, NULL)) PERSISTENT,
    PRIMARY KEY (id),
    UNIQUE KEY uq_cs_one_active (contact_id, channel_id, active_lock),
    KEY idx_cs_status_expires (status, expires_at),
    KEY idx_cs_flow (flow_id, status),
    CONSTRAINT fk_cs_ws      FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
    CONSTRAINT fk_cs_contact FOREIGN KEY (contact_id)   REFERENCES contacts(id)   ON DELETE CASCADE,
    CONSTRAINT fk_cs_channel FOREIGN KEY (channel_id)   REFERENCES channels(id)   ON DELETE CASCADE,
    CONSTRAINT fk_cs_flow    FOREIGN KEY (flow_id)      REFERENCES flows(id)      ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Traza de ejecución nodo a nodo (debug del builder y analítica por nodo)
CREATE TABLE IF NOT EXISTS flow_run_logs (
    id           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    session_id   BIGINT UNSIGNED NOT NULL,
    flow_id      INT UNSIGNED    NOT NULL,
    node_id      VARCHAR(64)     NOT NULL,
    node_type    VARCHAR(32)     NOT NULL,
    outcome      VARCHAR(32)     NOT NULL DEFAULT 'ok',   -- ok|true|false|timeout|error|button:<id>
    detail       JSON            NULL,
    created_at   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_frl_session (session_id),
    KEY idx_frl_flow_node (flow_id, node_id, created_at),
    CONSTRAINT fk_frl_session FOREIGN KEY (session_id) REFERENCES contact_sessions(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================================================
-- 6. COLA DE TRABAJOS (reemplazo de Redis/Workers) — procesada por bin/cron_worker.php
-- =============================================================================

CREATE TABLE IF NOT EXISTS scheduled_jobs (
    id             BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    workspace_id   INT UNSIGNED    NULL,
    -- flow_resume | broadcast_batch | sequence_step | bot_reactivate | send_message |
    -- webhook_out | input_timeout | template_sync | cleanup
    type           VARCHAR(40)     NOT NULL,
    payload        JSON            NOT NULL,
    run_at         DATETIME        NOT NULL,
    priority       TINYINT UNSIGNED NOT NULL DEFAULT 5,          -- 1 = máxima
    status         ENUM('pending','processing','done','failed','cancelled') NOT NULL DEFAULT 'pending',
    attempts       TINYINT UNSIGNED NOT NULL DEFAULT 0,
    max_attempts   TINYINT UNSIGNED NOT NULL DEFAULT 3,
    -- Deduplicación: p. ej. "resume:session:123:node:abc". NULL = sin restricción.
    unique_key     VARCHAR(191)    NULL,
    locked_by      VARCHAR(64)     NULL,                         -- id del proceso worker
    locked_at      DATETIME        NULL,
    last_error     TEXT            NULL,
    -- Referencias para cancelar jobs en bloque (p. ej. al cerrar una sesión)
    contact_id     BIGINT UNSIGNED NULL,
    session_id     BIGINT UNSIGNED NULL,
    created_at     DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at   DATETIME        NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_jobs_unique_key (unique_key),
    -- Consulta del worker: WHERE status='pending' AND run_at<=NOW() ORDER BY priority, run_at
    KEY idx_jobs_pick (status, run_at, priority),
    KEY idx_jobs_locked (status, locked_at),
    KEY idx_jobs_session (session_id, status),
    KEY idx_jobs_contact (contact_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Mutex a nivel de BD (evita que dos ejecuciones del cron se solapen)
CREATE TABLE IF NOT EXISTS system_locks (
    name          VARCHAR(64)  NOT NULL,
    owner         VARCHAR(64)  NOT NULL,
    locked_until  DATETIME     NOT NULL,
    PRIMARY KEY (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS cron_runs (
    id             BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    started_at     DATETIME        NOT NULL,
    finished_at    DATETIME        NULL,
    jobs_processed INT UNSIGNED    NOT NULL DEFAULT 0,
    jobs_failed    INT UNSIGNED    NOT NULL DEFAULT 0,
    peak_memory_kb INT UNSIGNED    NULL,
    note           VARCHAR(255)    NULL,
    PRIMARY KEY (id),
    KEY idx_cron_started (started_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================================================
-- 7. BROADCASTS Y SECUENCIAS
-- =============================================================================

CREATE TABLE IF NOT EXISTS broadcasts (
    id                 INT UNSIGNED  NOT NULL AUTO_INCREMENT,
    workspace_id       INT UNSIGNED  NOT NULL,
    channel_id         INT UNSIGNED  NOT NULL,
    name               VARCHAR(150)  NOT NULL,
    -- Contenido: un flujo a disparar O un mensaje/plantilla directo
    flow_id            INT UNSIGNED  NULL,
    template_id        INT UNSIGNED  NULL,
    template_params    JSON          NULL,                  -- variables mapeadas {{1}} => {{first_name}}
    message            JSON          NULL,                  -- mensaje libre (sólo dentro de ventana 24h)
    -- Segmentación: {"tags_any":[1,2],"tags_all":[],"tags_none":[5],"fields":[...]}
    audience_filter    JSON          NOT NULL,
    status             ENUM('draft','scheduled','preparing','running','paused','completed','cancelled','failed') NOT NULL DEFAULT 'draft',
    scheduled_at       DATETIME      NULL,
    batch_size         SMALLINT UNSIGNED NOT NULL DEFAULT 50,
    total_recipients   INT UNSIGNED  NOT NULL DEFAULT 0,
    sent_count         INT UNSIGNED  NOT NULL DEFAULT 0,
    delivered_count    INT UNSIGNED  NOT NULL DEFAULT 0,
    read_count         INT UNSIGNED  NOT NULL DEFAULT 0,
    failed_count       INT UNSIGNED  NOT NULL DEFAULT 0,
    created_by         INT UNSIGNED  NULL,
    started_at         DATETIME      NULL,
    completed_at       DATETIME      NULL,
    created_at         DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at         DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_bc_ws_status (workspace_id, status),
    KEY idx_bc_scheduled (status, scheduled_at),
    CONSTRAINT fk_bc_ws       FOREIGN KEY (workspace_id) REFERENCES workspaces(id)        ON DELETE CASCADE,
    CONSTRAINT fk_bc_channel  FOREIGN KEY (channel_id)   REFERENCES channels(id)          ON DELETE CASCADE,
    CONSTRAINT fk_bc_flow     FOREIGN KEY (flow_id)      REFERENCES flows(id)             ON DELETE SET NULL,
    CONSTRAINT fk_bc_template FOREIGN KEY (template_id)  REFERENCES message_templates(id) ON DELETE SET NULL,
    CONSTRAINT fk_bc_user     FOREIGN KEY (created_by)   REFERENCES users(id)             ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Snapshot de la audiencia: el worker procesa lotes con
-- WHERE broadcast_id=? AND status='pending' ORDER BY id LIMIT :batch
CREATE TABLE IF NOT EXISTS broadcast_recipients (
    id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    broadcast_id  INT UNSIGNED    NOT NULL,
    contact_id    BIGINT UNSIGNED NOT NULL,
    status        ENUM('pending','sent','delivered','read','failed','skipped') NOT NULL DEFAULT 'pending',
    message_id    BIGINT UNSIGNED NULL,
    error         VARCHAR(500)    NULL,
    sent_at       DATETIME        NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_br_bc_contact (broadcast_id, contact_id),
    KEY idx_br_batch (broadcast_id, status, id),
    CONSTRAINT fk_br_bc      FOREIGN KEY (broadcast_id) REFERENCES broadcasts(id) ON DELETE CASCADE,
    CONSTRAINT fk_br_contact FOREIGN KEY (contact_id)   REFERENCES contacts(id)   ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS sequences (
    id            INT UNSIGNED  NOT NULL AUTO_INCREMENT,
    workspace_id  INT UNSIGNED  NOT NULL,
    name          VARCHAR(150)  NOT NULL,
    is_active     TINYINT(1)    NOT NULL DEFAULT 1,
    -- Si el contacto responde, ¿se cancela la secuencia? (ej. recordatorio de cotización)
    stop_on_reply TINYINT(1)    NOT NULL DEFAULT 1,
    created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_seq_ws (workspace_id),
    CONSTRAINT fk_seq_ws FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS sequence_steps (
    id            INT UNSIGNED  NOT NULL AUTO_INCREMENT,
    sequence_id   INT UNSIGNED  NOT NULL,
    position      SMALLINT UNSIGNED NOT NULL,
    delay_value   INT UNSIGNED  NOT NULL DEFAULT 1,
    delay_unit    ENUM('minutes','hours','days') NOT NULL DEFAULT 'days',
    flow_id       INT UNSIGNED  NOT NULL,                  -- cada paso ejecuta un flujo
    -- Ventana de envío opcional: {"from":"09:00","to":"19:00","days":[1,2,3,4,5]}
    send_window   JSON          NULL,
    is_active     TINYINT(1)    NOT NULL DEFAULT 1,
    PRIMARY KEY (id),
    UNIQUE KEY uq_ss_seq_pos (sequence_id, position),
    CONSTRAINT fk_ss_seq  FOREIGN KEY (sequence_id) REFERENCES sequences(id) ON DELETE CASCADE,
    CONSTRAINT fk_ss_flow FOREIGN KEY (flow_id)     REFERENCES flows(id)     ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS contact_sequences (
    id             BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    contact_id     BIGINT UNSIGNED NOT NULL,
    sequence_id    INT UNSIGNED    NOT NULL,
    channel_id     INT UNSIGNED    NOT NULL,
    next_position  SMALLINT UNSIGNED NOT NULL DEFAULT 1,
    status         ENUM('active','completed','stopped') NOT NULL DEFAULT 'active',
    next_run_at    DATETIME        NULL,
    subscribed_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ended_at       DATETIME        NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_cseq_contact_seq (contact_id, sequence_id),
    KEY idx_cseq_due (status, next_run_at),
    CONSTRAINT fk_cseq_contact FOREIGN KEY (contact_id)  REFERENCES contacts(id)  ON DELETE CASCADE,
    CONSTRAINT fk_cseq_seq     FOREIGN KEY (sequence_id) REFERENCES sequences(id) ON DELETE CASCADE,
    CONSTRAINT fk_cseq_channel FOREIGN KEY (channel_id)  REFERENCES channels(id)  ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================================================
-- 8. GROWTH TOOLS
-- =============================================================================

-- Links wa.me / m.me / ig.me con parámetro ref que disparan un flujo concreto
CREATE TABLE IF NOT EXISTS growth_links (
    id             INT UNSIGNED  NOT NULL AUTO_INCREMENT,
    workspace_id   INT UNSIGNED  NOT NULL,
    channel_id     INT UNSIGNED  NOT NULL,
    flow_id        INT UNSIGNED  NOT NULL,
    name           VARCHAR(150)  NOT NULL,
    ref_code       VARCHAR(120)  NOT NULL,
    prefilled_text VARCHAR(500)  NULL,                    -- WhatsApp: texto que incluye el ref
    short_slug     VARCHAR(40)   NULL,                    -- /go/{slug} redirección con conteo
    clicks         INT UNSIGNED  NOT NULL DEFAULT 0,
    conversions    INT UNSIGNED  NOT NULL DEFAULT 0,
    is_active      TINYINT(1)    NOT NULL DEFAULT 1,
    created_at     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_gl_ws_ref (workspace_id, ref_code),
    UNIQUE KEY uq_gl_slug (short_slug),
    CONSTRAINT fk_gl_ws      FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
    CONSTRAINT fk_gl_channel FOREIGN KEY (channel_id)   REFERENCES channels(id)   ON DELETE CASCADE,
    CONSTRAINT fk_gl_flow    FOREIGN KEY (flow_id)      REFERENCES flows(id)      ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Comment-to-DM: evita responder dos veces el mismo comentario (Meta reintenta webhooks)
CREATE TABLE IF NOT EXISTS comment_replies (
    id               BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    workspace_id     INT UNSIGNED    NOT NULL,
    channel_id       INT UNSIGNED    NOT NULL,
    comment_id       VARCHAR(64)     NOT NULL,
    post_id          VARCHAR(64)     NULL,
    commenter_id     VARCHAR(64)     NULL,
    contact_id       BIGINT UNSIGNED NULL,
    flow_id          INT UNSIGNED    NULL,
    comment_text     TEXT            NULL,
    public_reply_id  VARCHAR(64)     NULL,
    dm_sent          TINYINT(1)      NOT NULL DEFAULT 0,
    created_at       DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_cr_channel_comment (channel_id, comment_id),
    KEY idx_cr_post (post_id),
    CONSTRAINT fk_cr_ws      FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
    CONSTRAINT fk_cr_channel FOREIGN KEY (channel_id)   REFERENCES channels(id)   ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Sesiones del widget web (token opaco en localStorage del visitante)
CREATE TABLE IF NOT EXISTS webchat_sessions (
    id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    channel_id    INT UNSIGNED    NOT NULL,
    contact_id    BIGINT UNSIGNED NOT NULL,
    token_hash    CHAR(64)        NOT NULL,
    origin        VARCHAR(255)    NULL,
    user_agent    VARCHAR(255)    NULL,
    ip            VARCHAR(45)     NULL,
    last_seen_at  DATETIME        NULL,
    created_at    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_ws_token (token_hash),
    KEY idx_wcs_contact (contact_id),
    CONSTRAINT fk_wcs_channel FOREIGN KEY (channel_id) REFERENCES channels(id) ON DELETE CASCADE,
    CONSTRAINT fk_wcs_contact FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================================================
-- 9. INTEGRACIONES, LOGS Y SEGURIDAD
-- =============================================================================

-- Bandeja de entrada cruda de webhooks: se responde 200 a Meta de inmediato y se procesa
-- después (mismo request tras litespeed_finish_request() o en el cron como respaldo).
CREATE TABLE IF NOT EXISTS webhook_inbox (
    id               BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    source           ENUM('whatsapp','instagram','messenger','webchat','external') NOT NULL,
    channel_id       INT UNSIGNED    NULL,
    event_hash       CHAR(64)        NOT NULL,                 -- sha256(body) para idempotencia
    signature_valid  TINYINT(1)      NOT NULL DEFAULT 0,
    payload          LONGTEXT        NOT NULL,
    status           ENUM('pending','processing','processed','failed','ignored') NOT NULL DEFAULT 'pending',
    attempts         TINYINT UNSIGNED NOT NULL DEFAULT 0,
    error            VARCHAR(1000)   NULL,
    received_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    processed_at     DATETIME        NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_wi_hash (event_hash),
    KEY idx_wi_status (status, received_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Log de webhooks HTTP salientes (nodo Acción → Activepieces / api.tecintek.com)
CREATE TABLE IF NOT EXISTS http_request_logs (
    id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    workspace_id    INT UNSIGNED    NULL,
    session_id      BIGINT UNSIGNED NULL,
    flow_id         INT UNSIGNED    NULL,
    node_id         VARCHAR(64)     NULL,
    method          VARCHAR(10)     NOT NULL,
    url             VARCHAR(1000)   NOT NULL,
    request_body    MEDIUMTEXT      NULL,
    response_code   SMALLINT        NULL,
    response_body   MEDIUMTEXT      NULL,
    duration_ms     INT UNSIGNED    NULL,
    error           VARCHAR(500)    NULL,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_hrl_ws_time (workspace_id, created_at),
    KEY idx_hrl_session (session_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Rate limiting sin Redis (API REST, widget, login)
CREATE TABLE IF NOT EXISTS rate_limits (
    bucket        VARCHAR(191)  NOT NULL,        -- "api:token:12" | "webchat:ip:1.2.3.4"
    window_start  DATETIME      NOT NULL,
    hits          INT UNSIGNED  NOT NULL DEFAULT 0,
    PRIMARY KEY (bucket, window_start)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS audit_logs (
    id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    workspace_id  INT UNSIGNED    NULL,
    user_id       INT UNSIGNED    NULL,
    action        VARCHAR(80)     NOT NULL,          -- flow.published, contact.deleted, token.created
    entity_type   VARCHAR(40)     NULL,
    entity_id     VARCHAR(64)     NULL,
    meta          JSON            NULL,
    ip            VARCHAR(45)     NULL,
    created_at    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_audit_ws_time (workspace_id, created_at),
    KEY idx_audit_entity (entity_type, entity_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS settings (
    workspace_id  INT UNSIGNED  NOT NULL DEFAULT 0,   -- 0 = ajuste global del sistema
    setting_key   VARCHAR(100)  NOT NULL,
    value         TEXT          NULL,
    updated_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (workspace_id, setting_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;

INSERT IGNORE INTO schema_migrations (version) VALUES ('2026_11_27_000001_initial_schema');
