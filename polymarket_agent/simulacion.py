"""
================================================================
  PRUEBA DE FUEGO - Agente de Polymarket (SIN INVERTIR NADA)
================================================================
Este archivo NO necesita instalar nada ni conexion ni MySQL.
Corre una simulacion completa de un dia de trading con dinero
FICTICIO, aplicando la MISMA logica del agente real:

  - Capital inicial (200k COP ~ 50 USDC)
  - 30 operaciones al dia
  - Tamano por operacion (6k COP ~ 1.5 USDC)
  - Umbral de entrada (edge) del 1.2%
  - Take-profit, stop-loss y timeout de 30 min
  - Balance check (se pausa si no alcanza el saldo)
  - Un costo por operacion (comision/slippage) REALISTA

Al final imprime un reporte honesto: utilidad BRUTA, COMISIONES
y utilidad NETA (la unica que importa).

Como correrlo:   python3 simulacion.py
================================================================
"""
import random
import csv
import os
from datetime import datetime

# ------------------ PARAMETROS (edita a tu gusto) ------------------
CAPITAL_USDC        = 50.0     # ~200.000 COP
POSITION_SIZE_USDC  = 1.5      # ~6.000 COP por operacion
MIN_BALANCE_USDC    = 1.5      # si el saldo baja de esto, se pausa
MAX_TRADES_PER_DAY  = 30       # objetivo de operaciones/dia
MIN_EDGE            = 0.012    # umbral de entrada: 1.2%
TAKE_PROFIT         = 0.02     # objetivo +2% por operacion
STOP_LOSS           = 0.03     # corte de perdida -3% (el "escudo")
POSITION_TIMEOUT_MIN= 30       # cierre forzado a los 30 min
COSTO_POR_OPERACION = 0.005    # comision+slippage estimado por lado (0.5%)
SEMILLA             = None     # pon un numero (ej: 42) para resultados repetibles
# -------------------------------------------------------------------

if SEMILLA is not None:
    random.seed(SEMILLA)


def escanear_mercados(n=20):
    """Genera mercados ficticios pero plausibles (precios entre 0 y 1)."""
    mercados = []
    for i in range(n):
        yes = round(random.uniform(0.30, 0.70), 3)
        # A veces aparece una ineficiencia: YES + NO < 1 (margen aprovechable).
        no = round(1 - yes - random.uniform(-0.06, 0.06), 3)
        mercados.append({
            "mercado": f"Mercado #{i+1}",
            "yes": yes, "no": max(0.01, no),
            "liquidez": random.uniform(500, 5000),
        })
    mercados.sort(key=lambda m: m["liquidez"], reverse=True)  # prioriza liquidez
    return mercados


def buscar_entrada(mercados):
    """Busca el mejor mercado con edge >= MIN_EDGE (neto de costos)."""
    mejor, mejor_edge = None, MIN_EDGE
    for m in mercados:
        suma = m["yes"] + m["no"]
        edge = (1.0 - suma) if suma < 1.0 else 0.0
        edge_neto = edge - 2 * COSTO_POR_OPERACION
        if edge_neto > mejor_edge:
            mejor_edge = edge_neto
            lado = "YES" if m["yes"] <= m["no"] else "NO"
            precio = m["yes"] if lado == "YES" else m["no"]
            mejor = {"mercado": m["mercado"], "lado": lado,
                     "precio_compra": precio, "edge": round(edge_neto, 4)}
    return mejor


def simular_salida(precio_compra):
    """Simula la evolucion del precio hasta que se cierre la posicion."""
    precio = precio_compra
    for minuto in range(1, POSITION_TIMEOUT_MIN + 1):
        precio = max(0.01, min(0.99, precio + random.uniform(-0.02, 0.022)))
        cambio = (precio - precio_compra) / precio_compra
        if cambio >= TAKE_PROFIT:
            return precio, minuto, "TAKE_PROFIT"
        if cambio <= -STOP_LOSS:
            return precio, minuto, "STOP_LOSS"
    return precio, POSITION_TIMEOUT_MIN, "TIMEOUT"


def main():
    print("=" * 60)
    print("  PRUEBA DE FUEGO - AGENTE POLYMARKET (SIMULACION)")
    print("  Dinero FICTICIO. No se arriesga ni un peso.")
    print("=" * 60)
    print(f"Capital inicial: {CAPITAL_USDC:.2f} USDC (~200.000 COP)\n")

    saldo = CAPITAL_USDC
    operaciones = []

    for n in range(1, MAX_TRADES_PER_DAY + 1):
        # --- Balance check (escudo anti-errores) ---
        if saldo < MIN_BALANCE_USDC:
            print(f"\n[PAUSA] Saldo {saldo:.2f} < minimo {MIN_BALANCE_USDC}. "
                  f"Agente pausado tras {n-1} operaciones.")
            break

        entrada = buscar_entrada(escanear_mercados())
        if not entrada:
            continue  # sin oportunidad con edge suficiente; reintenta

        size = min(POSITION_SIZE_USDC, saldo)
        cantidad = size / entrada["precio_compra"]
        precio_venta, minutos, motivo = simular_salida(entrada["precio_compra"])

        bruta = (precio_venta - entrada["precio_compra"]) * cantidad
        comision = COSTO_POR_OPERACION * size + COSTO_POR_OPERACION * (cantidad * precio_venta)
        neta = bruta - comision
        saldo += neta

        operaciones.append({
            "id": n, "mercado": entrada["mercado"], "lado": entrada["lado"],
            "precio_compra": round(entrada["precio_compra"], 3),
            "precio_venta": round(precio_venta, 3),
            "utilidad_bruta": round(bruta, 4),
            "comision": round(comision, 4),
            "utilidad_neta": round(neta, 4),
            "motivo": motivo, "minutos": minutos,
        })

        icono = "✅" if neta > 0 else "❌"
        print(f"{icono} Op #{n:2d} | {entrada['mercado']:12s} | "
              f"compra {entrada['precio_compra']:.3f} -> venta {precio_venta:.3f} | "
              f"{motivo:11s} | neto {neta:+.4f} | saldo {saldo:.2f}")

    # --------------------- REPORTE FINAL ---------------------
    total_bruta = sum(o["utilidad_bruta"] for o in operaciones)
    total_com   = sum(o["comision"] for o in operaciones)
    total_neta  = sum(o["utilidad_neta"] for o in operaciones)
    ganadoras   = sum(1 for o in operaciones if o["utilidad_neta"] > 0)

    print("\n" + "=" * 60)
    print("  REPORTE DEL DIA (SIMULADO)")
    print("=" * 60)
    print(f"Operaciones ejecutadas : {len(operaciones)}")
    print(f"Ganadoras / Perdedoras : {ganadoras} / {len(operaciones) - ganadoras}")
    print(f"Utilidad BRUTA         : {total_bruta:+.4f} USDC")
    print(f"Comisiones/slippage    : {total_com:.4f} USDC")
    print(f"-> UTILIDAD NETA        : {total_neta:+.4f} USDC")
    print(f"Saldo final            : {saldo:.2f} USDC "
          f"(inicio {CAPITAL_USDC:.2f})")
    pct = (total_neta / CAPITAL_USDC * 100) if CAPITAL_USDC else 0
    print(f"Rendimiento del dia     : {pct:+.2f}%")
    print("=" * 60)
    if total_neta > 0:
        print("Resultado positivo EN ESTA simulacion. Corre varias veces:")
        print("veras que a veces da negativo. Asi es el trading real.")
    else:
        print("Dia NEGATIVO. Esto es normal y por eso probamos sin invertir.")
    print("Nota: ningun bot gana siempre. La unica cifra real es la NETA.")

    # Guarda un CSV para revisar (igual que el reporte real).
    os.makedirs("reports/out", exist_ok=True)
    ruta = f"reports/out/simulacion_{datetime.now():%Y%m%d_%H%M%S}.csv"
    if operaciones:
        with open(ruta, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(operaciones[0].keys()))
            w.writeheader()
            w.writerows(operaciones)
        print(f"\nCSV guardado en: {ruta}")


if __name__ == "__main__":
    main()
