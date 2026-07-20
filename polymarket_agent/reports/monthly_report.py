"""Reporte mensual. Suma las utilidades del mes en curso y envia un CSV.

Cron sugerido: el ultimo dia del mes a las 23:59, o el dia 1 del mes siguiente.
"""
import os
import sys
import csv
import smtplib
from datetime import date
from email.message import EmailMessage

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.config import Config
from src import db
from reports.daily_report import enviar_correo


def resumen_por_dia():
    sql = """
        SELECT DATE(abierta_en) AS dia,
               COUNT(*)                       AS operaciones,
               SUM(COALESCE(utilidad_bruta,0)) AS utilidad_bruta,
               SUM(COALESCE(comision,0))       AS comision,
               SUM(COALESCE(utilidad_neta,0))  AS utilidad_neta
          FROM operaciones_polymarker
         WHERE YEAR(abierta_en) = YEAR(CURDATE())
           AND MONTH(abierta_en) = MONTH(CURDATE())
         GROUP BY DATE(abierta_en)
         ORDER BY dia
    """
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            return cur.fetchall()
    finally:
        conn.close()


def main():
    filas = resumen_por_dia()
    mes = date.today().strftime("%Y-%m")
    ruta = os.path.join(os.path.dirname(__file__), "out", f"reporte_mensual_{mes}.csv")
    os.makedirs(os.path.dirname(ruta), exist_ok=True)

    campos = ["dia", "operaciones", "utilidad_bruta", "comision", "utilidad_neta"]
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        for r in filas:
            w.writerow({k: r[k] for k in campos})

    total_neta = sum(float(r["utilidad_neta"] or 0) for r in filas)
    total_ops = sum(int(r["operaciones"] or 0) for r in filas)
    resumen = (
        f"Reporte MENSUAL Polymarket - {mes}\n"
        f"Dias operados: {len(filas)}\n"
        f"Operaciones totales: {total_ops}\n"
        f"UTILIDAD NETA DEL MES: {total_neta:+.4f} USDC\n"
    )
    print(resumen)
    enviar_correo(f"Reporte MENSUAL Polymarket {mes}", resumen, ruta)


if __name__ == "__main__":
    main()
