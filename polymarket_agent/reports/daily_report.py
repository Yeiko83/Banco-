"""Reporte diario. Se ejecuta a las 23:59 (hora Colombia) por cron.

Lee las operaciones del dia desde MySQL, consolida:
  ID_Operacion, Mercado, Precio_Compra, Precio_Venta, Utilidad_Bruta, Comision
y envia un CSV por correo. Tambien deja el CSV en reports/out/.
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
from tabulate import tabulate

CAMPOS = ["id_operacion", "mercado", "precio_compra", "precio_venta",
          "utilidad_bruta", "comision", "utilidad_neta", "motivo_cierre"]


def obtener_operaciones_hoy():
    sql = f"""SELECT {', '.join(CAMPOS)} FROM operaciones_polymarker
              WHERE DATE(abierta_en) = CURDATE() ORDER BY id_operacion"""
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            return cur.fetchall()
    finally:
        conn.close()


def escribir_csv(filas, ruta):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        w.writeheader()
        w.writerows(filas)


def enviar_correo(asunto, cuerpo, adjunto):
    if not (Config.SMTP_HOST and Config.SMTP_USER and Config.REPORT_TO):
        print("[reporte] SMTP no configurado; se omite el envio por correo.")
        return
    msg = EmailMessage()
    msg["Subject"] = asunto
    msg["From"] = Config.SMTP_USER
    msg["To"] = Config.REPORT_TO
    msg.set_content(cuerpo)
    with open(adjunto, "rb") as f:
        msg.add_attachment(f.read(), maintype="text", subtype="csv",
                           filename=os.path.basename(adjunto))
    with smtplib.SMTP_SSL(Config.SMTP_HOST, Config.SMTP_PORT) as s:
        s.login(Config.SMTP_USER, Config.SMTP_PASSWORD)
        s.send_message(msg)
    print(f"[reporte] Correo enviado a {Config.REPORT_TO}")


def main():
    filas = obtener_operaciones_hoy()
    hoy = date.today().isoformat()
    ruta = os.path.join(os.path.dirname(__file__), "out", f"reporte_diario_{hoy}.csv")
    escribir_csv(filas, ruta)

    total_neta = sum(float(f["utilidad_neta"] or 0) for f in filas)
    total_bruta = sum(float(f["utilidad_bruta"] or 0) for f in filas)
    total_com = sum(float(f["comision"] or 0) for f in filas)

    resumen = (
        f"Reporte diario Polymarket - {hoy}\n"
        f"Operaciones: {len(filas)}\n"
        f"Utilidad bruta: {total_bruta:+.4f} USDC\n"
        f"Comisiones:     {total_com:.4f} USDC\n"
        f"Utilidad neta:  {total_neta:+.4f} USDC\n"
    )
    print(resumen)
    if filas:
        print(tabulate(filas, headers="keys", tablefmt="github"))
    enviar_correo(f"Reporte Polymarket {hoy}", resumen, ruta)


if __name__ == "__main__":
    main()
