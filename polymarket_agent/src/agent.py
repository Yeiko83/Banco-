"""Bucle principal del agente de Polymarket.

Flujo por operacion:
  1. Chequeo de riesgo (balance check + tope diario).
  2. Escanea mercados (prioriza liquidez).
  3. Busca una entrada con edge >= MIN_EDGE.
  4. Abre posicion, la registra en MySQL.
  5. Vigila hasta take-profit / stop-loss / timeout de 30 min.
  6. Cierra, actualiza MySQL y hace re-entrada inmediata (<5s).

Ejecutar:
  python -m src.agent            # una pasada
  python -m src.agent --loop     # ciclo continuo
"""
import sys
import time
from datetime import datetime

from .config import Config
from .polymarket_client import make_client
from .risk import RiskManager
from . import strategy, db


def _log(msg):
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def vigilar_posicion(client, id_op, precio_compra, token_id, cantidad):
    """Vigila una posicion abierta hasta que toque cerrarla."""
    abierta = time.time()
    while True:
        precio_actual = client.get_price(token_id)
        minutos = (time.time() - abierta) / 60.0
        cerrar, motivo = strategy.decidir_cierre(precio_compra, precio_actual, minutos)
        if cerrar:
            client.place_order(token_id, "SELL", precio_actual, cantidad * precio_actual)
            bruta = (precio_actual - precio_compra) * cantidad
            comision = Config.FEE_ESTIMATE * cantidad * precio_actual
            db.cerrar_operacion(id_op, precio_actual, round(bruta, 4),
                                round(comision, 4), motivo)
            _log(f"  cierre {motivo}: compra={precio_compra} venta={precio_actual} "
                 f"neto={bruta - comision:+.4f} USDC")
            return
        time.sleep(2 if Config.is_live() else 0.2)


def una_operacion(client, risk):
    ok, motivo = risk.puede_operar()
    if not ok:
        _log(f"PAUSA: {motivo}")
        return False

    mercados = client.get_markets(limit=20)
    entrada = strategy.buscar_entrada(mercados)
    if not entrada:
        _log("Sin oportunidad con edge suficiente. Reintentando...")
        return True  # sigue el ciclo, solo que no encontro entrada

    size = risk.tamano_posicion()
    precio = entrada["precio_compra"]
    cantidad = round(size / precio, 4) if precio > 0 else 0
    if cantidad <= 0:
        return True

    client.place_order(entrada["token_id"], "BUY", precio, size)
    id_op = db.insertar_operacion({
        "modo": Config.MODE,
        "mercado": entrada["market"],
        "token_id": entrada["token_id"],
        "lado": "BUY",
        "precio_compra": precio,
        "tamano_usdc": round(size, 4),
        "cantidad": cantidad,
        "comision": 0,
        "abierta_en": datetime.now(),
    })
    _log(f"ABRE #{id_op} {entrada['market']} @ {precio} (edge {entrada['edge']}) size {size:.2f}")
    vigilar_posicion(client, id_op, precio, entrada["token_id"], cantidad)
    return True


def main():
    Config.guard_live()
    banner = "REAL (dinero real)" if Config.is_live() else "SIMULACION (dinero ficticio)"
    _log(f"=== Agente Polymarket | MODO: {banner} ===")
    if Config.is_live():
        _log("!! Operando con DINERO REAL. Ctrl+C para detener. !!")

    client = make_client()
    risk = RiskManager(client)

    loop = "--loop" in sys.argv
    while True:
        try:
            sigue = una_operacion(client, risk)
        except KeyboardInterrupt:
            _log("Detenido por el usuario.")
            break
        except Exception as e:
            _log(f"ERROR: {e}")
            sigue = True
        if not loop or not sigue:
            break
        time.sleep(5 if Config.is_live() else 0.5)  # re-entrada inmediata


if __name__ == "__main__":
    main()
