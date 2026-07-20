"""Capa de acceso a MySQL para las operaciones del agente."""
import pymysql
from datetime import datetime
from .config import Config


def get_connection():
    return pymysql.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )


def insertar_operacion(op):
    """Inserta una operacion recien abierta y devuelve su id_operacion."""
    sql = """
        INSERT INTO operaciones_polymarker
          (modo, mercado, token_id, lado, precio_compra, tamano_usdc,
           cantidad, comision, estado, motivo_cierre, abierta_en)
        VALUES
          (%(modo)s, %(mercado)s, %(token_id)s, %(lado)s, %(precio_compra)s,
           %(tamano_usdc)s, %(cantidad)s, %(comision)s, 'ABIERTA', 'ABIERTA',
           %(abierta_en)s)
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, op)
            return cur.lastrowid
    finally:
        conn.close()


def cerrar_operacion(id_op, precio_venta, utilidad_bruta, comision, motivo):
    utilidad_neta = utilidad_bruta - comision
    sql = """
        UPDATE operaciones_polymarker
           SET precio_venta = %s,
               utilidad_bruta = %s,
               comision = %s,
               utilidad_neta = %s,
               motivo_cierre = %s,
               estado = 'CERRADA',
               cerrada_en = %s
         WHERE id_operacion = %s
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (precio_venta, utilidad_bruta, comision,
                              utilidad_neta, motivo, datetime.now(), id_op))
    finally:
        conn.close()


def contar_operaciones_hoy():
    sql = """SELECT COUNT(*) AS n FROM operaciones_polymarker
             WHERE DATE(abierta_en) = CURDATE()"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            return cur.fetchone()["n"]
    finally:
        conn.close()
