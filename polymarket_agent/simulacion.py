"""
================================================================
  PRUEBA DE FUEGO - Agente de Polymarket (SIN INVERTIR NADA)
================================================================
Version 2: estrategia de ARBITRAJE de bajo riesgo.

En vez de apostar a que el precio suba (direccional = arriesgado),
el agente busca mercados donde comprar YES + NO cueste MENOS de $1.
Como al resolverse el mercado uno de los dos SIEMPRE vale $1, esa
diferencia queda "bloqueada" como ganancia casi sin riesgo.

Se modela tambien el RIESGO REAL de que solo una pata se ejecute
(fill parcial): ahi si quedas expuesto y puedes perder. Por eso NO
es "ganar sin perder nada" -> es "ganar con riesgo controlado".

Corre una simulacion de varios dias con dinero FICTICIO.
Como correrlo:   python3 simulacion.py
================================================================
"""
import random
import csv
import os
from datetime import datetime

# ------------------ PARAMETROS (edita a tu gusto) ------------------
CAPITAL_USDC        = 50.0     # ~200.000 COP
POSITION_SIZE_USDC  = 1.5      # ~6.000 COP por par (YES+NO)
MIN_BALANCE_USDC    = 1.5      # si el saldo baja de esto, se pausa
MAX_TRADES_PER_DAY  = 30       # tope de operaciones/dia
MERCADOS_POR_DIA    = 300      # cuantos mercados escanea el agente al dia
MIN_EDGE            = 0.012    # umbral de entrada: la ineficiencia debe superar 1.2%
COSTO_POR_OPERACION = 0.005    # comision+slippage estimado por pata (0.5%)
PROB_AMBAS_PATAS    = 0.80     # prob. de que se ejecuten las 2 patas (arbitraje ok)
DIAS                = 30       # dias a simular
SEMILLA             = None     # pon un numero (ej: 42) para resultados repetibles
# -------------------------------------------------------------------

if SEMILLA is not None:
    random.seed(SEMILLA)


def escanear_mercados(n):
    """Genera mercados realistas.

    Los mercados suelen ser eficientes: YES+NO ~ 1 (o un poco mas por el
    spread). De vez en cuando aparece una ineficiencia (YES+NO < 1) que es
    la oportunidad de arbitraje.
    """
    mercados = []
    for i in range(n):
        # suma centrada un poco por encima de 1 (mercado eficiente con spread),
        # con cola ocasional por debajo de 1 (la oportunidad).
        suma = 1.0 + random.gauss(0.012, 0.02)
        yes = round(random.uniform(0.15, 0.85), 3)
        no = round(max(0.01, suma - yes), 3)
        mercados.append({"mercado": f"Mkt-{i+1}", "yes": yes, "no": no,
                         "liquidez": random.uniform(200, 8000)})
    mercados.sort(key=lambda m: m["liquidez"], reverse=True)  # prioriza liquidez
    return mercados


def buscar_arbitrajes(mercados):
    """Devuelve las oportunidades de arbitraje ordenadas por margen."""
    ops = []
    for m in mercados:
        suma = m["yes"] + m["no"]
        edge = 1.0 - suma                    # margen bruto si compro ambas patas
        edge_neto = edge - 2 * COSTO_POR_OPERACION
        if edge_neto >= MIN_EDGE:
            ops.append({"mercado": m["mercado"], "yes": m["yes"], "no": m["no"],
                        "edge": round(edge_neto, 4)})
    ops.sort(key=lambda o: o["edge"], reverse=True)
    return ops


def ejecutar(op, size):
    """Ejecuta una oportunidad. Devuelve (utilidad_neta, motivo).

    - Si ambas patas se ejecutan: ganancia bloqueada = edge * size.
    - Si solo una se ejecuta (fill parcial): quedas direccional -> ~50/50,
      puede ganar o perder. Este es el riesgo real del arbitraje.
    """
    if random.random() < PROB_AMBAS_PATAS:
        neta = op["edge"] * size            # arbitraje logrado
        return round(neta, 4), "ARBITRAJE"
    # Fill parcial: exposicion direccional. Resultado incierto.
    if random.random() < 0.5:
        neta = random.uniform(0.005, 0.03) * size
        return round(neta, 4), "FILL_PARCIAL_OK"
    neta = -random.uniform(0.01, 0.05) * size
    return round(neta, 4), "FILL_PARCIAL_PERDIDA"


def simular_dia(dia):
    saldo_ops = []
    mercados = escanear_mercados(MERCADOS_POR_DIA)
    oportunidades = buscar_arbitrajes(mercados)[:MAX_TRADES_PER_DAY]
    for i, op in enumerate(oportunidades, 1):
        neta, motivo = ejecutar(op, POSITION_SIZE_USDC)
        saldo_ops.append({"dia": dia, "id": i, "mercado": op["mercado"],
                          "yes": op["yes"], "no": op["no"], "edge": op["edge"],
                          "utilidad_neta": neta, "motivo": motivo})
    return saldo_ops


def main():
    print("=" * 66)
    print("  PRUEBA DE FUEGO v2 - ARBITRAJE DE BAJO RIESGO (SIMULACION)")
    print("  Dinero FICTICIO. No se arriesga ni un peso.")
    print("=" * 66)
    print(f"Capital inicial: {CAPITAL_USDC:.2f} USDC (~200.000 COP)")
    print(f"Simulando {DIAS} dias...\n")

    saldo = CAPITAL_USDC
    todas = []
    resumen_dias = []

    for dia in range(1, DIAS + 1):
        ops = simular_dia(dia)
        neta_dia = sum(o["utilidad_neta"] for o in ops)
        saldo += neta_dia
        todas.extend(ops)
        resumen_dias.append((dia, len(ops), neta_dia, saldo))
        signo = "+" if neta_dia >= 0 else ""
        print(f"Dia {dia:2d} | {len(ops):2d} ops | neto {signo}{neta_dia:.4f} USDC "
              f"| saldo {saldo:.2f}")
        if saldo < MIN_BALANCE_USDC:
            print(f"\n[PAUSA] Saldo por debajo del minimo. Agente detenido.")
            break

    total_neta = saldo - CAPITAL_USDC
    n = len(todas)
    ganadoras = sum(1 for o in todas if o["utilidad_neta"] > 0)
    arbs = sum(1 for o in todas if o["motivo"] == "ARBITRAJE")
    perdidas = sum(1 for o in todas if o["utilidad_neta"] < 0)

    print("\n" + "=" * 66)
    print(f"  RESUMEN DE {DIAS} DIAS (SIMULADO)")
    print("=" * 66)
    print(f"Operaciones totales     : {n}")
    print(f"  - Arbitrajes logrados : {arbs}")
    print(f"  - Con perdida         : {perdidas}")
    print(f"Tasa de acierto         : {(ganadoras/n*100 if n else 0):.1f}%")
    print(f"UTILIDAD NETA TOTAL     : {total_neta:+.4f} USDC")
    print(f"Saldo final             : {saldo:.2f} USDC (inicio {CAPITAL_USDC:.2f})")
    pct = (total_neta / CAPITAL_USDC * 100) if CAPITAL_USDC else 0
    print(f"Rendimiento {DIAS} dias    : {pct:+.2f}%")
    if DIAS:
        print(f"Promedio por dia        : {total_neta/DIAS:+.4f} USDC "
              f"(~{total_neta/DIAS*4000:+.0f} COP/dia aprox.)")
    print("=" * 66)
    print("HONESTIDAD: el arbitraje reduce el riesgo pero NO lo elimina.")
    print("Las oportunidades reales son escasas y hay bots mas rapidos.")
    print("Estos numeros son un MODELO, no una promesa. La cifra real que")
    print("importa siempre es la utilidad NETA despues de comisiones.")

    os.makedirs("reports/out", exist_ok=True)
    ruta = f"reports/out/simulacion_{datetime.now():%Y%m%d_%H%M%S}.csv"
    if todas:
        with open(ruta, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(todas[0].keys()))
            w.writeheader()
            w.writerows(todas)
        print(f"\nCSV con el detalle guardado en: {ruta}")


if __name__ == "__main__":
    main()
