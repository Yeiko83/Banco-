"""
================================================================
  SONDA DE DATOS REALES - Polymarket (SOLO LECTURA, SIN DINERO)
================================================================
Se conecta a la API PUBLICA de Polymarket, descarga mercados
activos y cuenta cuantas oportunidades de ARBITRAJE existen de
verdad AHORA MISMO (donde comprar YES + NO cuesta menos de $1).

NO envia ordenes. NO usa tu wallet. NO arriesga nada.
Sirve para comprobar si la estrategia del agente tiene sentido
con datos reales, antes de siquiera pensar en dinero real.

No necesita instalar nada. Solo Python 3.
Como correrlo:   python3 sondeo_real.py

Nota: usa el precio publico (mid/last) de cada resultado. La
ejecucion real exige mirar el "ask" del libro de ordenes de ambas
patas; este sondeo es un primer termometro, no una garantia.
================================================================
"""
import json
import urllib.request
import urllib.error

GAMMA_URL = "https://gamma-api.polymarket.com/markets"
COSTO_TOTAL = 0.01     # costo estimado ida y vuelta (2 patas x 0.5%)
MIN_EDGE = 0.012       # ineficiencia minima para considerarla oportunidad
PAGINAS = 5            # cuantas paginas de 100 mercados revisar
POR_PAGINA = 100


def traer_pagina(offset):
    url = f"{GAMMA_URL}?active=true&closed=false&limit={POR_PAGINA}&offset={offset}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def parse_precios(m):
    """Devuelve la lista de precios de los resultados, o None."""
    raw = m.get("outcomePrices")
    if raw is None:
        return None
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            return None
    try:
        return [float(x) for x in raw]
    except Exception:
        return None


def main():
    print("=" * 64)
    print("  SONDA DE DATOS REALES DE POLYMARKET (SOLO LECTURA)")
    print("  No se envia ninguna orden. No se arriesga dinero.")
    print("=" * 64)

    total = 0
    con_dos = 0
    oportunidades = []

    try:
        for p in range(PAGINAS):
            mercados = traer_pagina(p * POR_PAGINA)
            if not mercados:
                break
            for m in mercados:
                total += 1
                precios = parse_precios(m)
                if not precios or len(precios) != 2:
                    continue
                con_dos += 1
                suma = sum(precios)
                edge = (1.0 - suma) - COSTO_TOTAL
                if edge >= MIN_EDGE:
                    oportunidades.append({
                        "mercado": (m.get("question") or "?")[:60],
                        "yes": precios[0], "no": precios[1],
                        "suma": round(suma, 4), "edge_neto": round(edge, 4),
                        "liquidez": m.get("liquidity"),
                    })
    except urllib.error.URLError as e:
        print(f"\nNo se pudo conectar a Polymarket: {e}")
        print("Revisa tu conexion a internet. (En algunos servidores el")
        print("firewall bloquea la salida; prueba en tu PC o en Hostinger.)")
        return

    oportunidades.sort(key=lambda o: o["edge_neto"], reverse=True)

    print(f"\nMercados revisados          : {total}")
    print(f"Mercados binarios (YES/NO)  : {con_dos}")
    print(f"OPORTUNIDADES de arbitraje  : {len(oportunidades)} "
          f"(edge neto >= {MIN_EDGE*100:.1f}%)")
    print("=" * 64)

    if oportunidades:
        print("Top oportunidades encontradas AHORA:")
        for o in oportunidades[:15]:
            print(f"  edge {o['edge_neto']*100:+.2f}% | suma {o['suma']:.3f} | "
                  f"{o['mercado']}")
    else:
        print("Ahora mismo NO hay arbitrajes claros con estos precios publicos.")
        print("Es lo esperable: los mercados suelen ser eficientes y los bots")
        print("rapidos cierran las diferencias en segundos. Esto CONFIRMA que")
        print("hay que ser realista con las expectativas de ganancia.")

    print("\nRecuerda: precio publico != precio ejecutable. Para operar de")
    print("verdad hay que mirar el 'ask' del libro de ordenes de ambas patas.")


if __name__ == "__main__":
    main()
