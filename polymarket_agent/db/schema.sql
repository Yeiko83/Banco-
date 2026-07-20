-- ============================================================
--  Esquema de base de datos del Agente de Polymarket
--  Ejecutar una sola vez:  mysql -u USUARIO -p polymarket < db/schema.sql
-- ============================================================

CREATE DATABASE IF NOT EXISTS polymarket
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE polymarket;

-- Cada fila = una operacion (compra + su cierre).
CREATE TABLE IF NOT EXISTS operaciones_polymarker (
  id_operacion      BIGINT AUTO_INCREMENT PRIMARY KEY,
  modo              ENUM('SIM','LIVE') NOT NULL DEFAULT 'SIM',
  mercado           VARCHAR(255)   NOT NULL,           -- pregunta / titulo del mercado
  token_id          VARCHAR(120)   NULL,               -- id del outcome (YES/NO) en la CLOB
  lado              ENUM('BUY','SELL') NOT NULL DEFAULT 'BUY',

  precio_compra     DECIMAL(10,4)  NOT NULL,           -- precio de entrada (0-1)
  precio_venta      DECIMAL(10,4)  NULL,               -- precio de salida (0-1), NULL si abierta
  tamano_usdc       DECIMAL(12,4)  NOT NULL,           -- capital comprometido
  cantidad          DECIMAL(14,4)  NOT NULL,           -- shares compradas

  utilidad_bruta    DECIMAL(12,4)  NULL,               -- ganancia antes de comision
  comision          DECIMAL(12,4)  NOT NULL DEFAULT 0, -- comision_polymarker estimada/real
  utilidad_neta     DECIMAL(12,4)  NULL,               -- bruta - comision

  motivo_cierre     ENUM('TAKE_PROFIT','STOP_LOSS','TIMEOUT','MANUAL','ABIERTA')
                    NOT NULL DEFAULT 'ABIERTA',
  estado            ENUM('ABIERTA','CERRADA') NOT NULL DEFAULT 'ABIERTA',

  abierta_en        DATETIME       NOT NULL,
  cerrada_en        DATETIME       NULL,
  creada_en         TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP,

  INDEX idx_estado (estado),
  INDEX idx_fecha  (abierta_en),
  INDEX idx_modo   (modo)
) ENGINE=InnoDB;
