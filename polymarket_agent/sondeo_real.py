"""
================================================================
  SONDA DE DATOS REALES v2 - Polymarket (SOLO LECTURA, SIN DINERO)
================================================================
Ahora mira el LIBRO DE ORDENES real (precio 'ask', lo que de verdad
pagarias), no solo el precio de referencia. Para los mercados mas
liquidos, compara el ask de YES + el ask de NO. Si suman menos de $1,
ahi habria un arbitraje EJECUTABLE.

NO envia ordenes. NO usa tu wallet. NO arriesga nada.
No necesita instalar nada. Solo Python 3.
Como correrlo:   python3 sondeo_real.py
================================================================
"""
import json
import urllib.request
import urllib.error

GAMMA_URL = "https://gamma-api.polymarket.com/markets"
BOOK_URL = "https://clob.polymarket.com/book"
COSTO_TOTAL = 0.00     # el CLOB de Polymarket hoy no cobra fee de trading
MIN_EDGE = 0.005       # margen minimo (0.5%) para que valga la pena
N_MERCADOS = 40        # cuantos mercados (los mas liquidos) revisar a fondo


def http_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def traer_mercados_liquidos():
    """Trae mercados activos ordenados por liquidez (descendente)."""
    url = (f"{GAMMA_URL}?active=true&closed=false&limit={N_MERCADOS}"
           f"&order=liquidity&ascending=false")
    return http_get(url)


def token_ids(m):
    raw = m.get("clobTokenIds")
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            return None
    if isinstance(raw, list) and len(raw) == 2:
        return raw
    return None


def mejor_ask(token_id):
    """Devuelve el mejor (mas barato) precio de venta del libro, o None."""
    try:
        libro = http_get(f"{BOOK_URL}?token_id={token_id}")
    except Exception:
        return None
    asks = libro.get("asks") or []
    precios = []
    for a in asks:
        try:
            precios.append(float(a["price"]))
        except Exception:
            pass
    return min(precios) if precios else None


def main():
    print("=" * 66)
    print("  SONDA DE DATOS REALES v2 - LIBRO DE ORDENES (SOLO LECTURA)")
    print("  No se envia ninguna orden. No se arriesga dinero.")
    print("=" * 66)

    try:
        mercados = traer_mercados_liquidos()
    except urllib.error.URLError as e:
        print(f"\nNo se pudo conectar a Polymarket: {e}")
        return

    revisados = 0
    oportunidades = []
    print(f"Revisando el libro de ordenes de {len(mercados)} mercados liquidos...\n")

    for m in mercados:
        ids = token_ids(m)
        if not ids:
            continue
        ask_yes = mejor_ask(ids[0])
        ask_no = mejor_ask(ids[1])
        if ask_yes is None or ask_no is None:
            continue
        revisados += 1
        suma = ask_yes + ask_no
        edge = (1.0 - suma) - COSTO_TOTAL
        pregunta = (m.get("question") or "?")[:55]
        marca = "  <-- ARBITRAJE" if edge >= MIN_EDGE else ""
        print(f"  ask YES {ask_yes:.3f} + ask NO {ask_no:.3f} = {suma:.3f} "
              f"(margen {edge*100:+.2f}%) | {pregunta}{marca}")
        if edge >= MIN_EDGE:
            oportunidades.append({"mercado": pregunta, "suma": round(suma, 4),
                                  "edge": round(edge, 4)})

    print("\n" + "=" * 66)
    print(f"Mercados con libro revisado : {revisados}")
    print(f"ARBITRAJES EJECUTABLES      : {len(oportunidades)} "
          f"(margen >= {MIN_EDGE*100:.1f}%)")
    print("=" * 66)

    if oportunidades:
        print("Se encontraron oportunidades REALES ejecutables:")
        for o in sorted(oportunidades, key=lambda x: x["edge"], reverse=True):
            print(f"  margen {o['edge']*100:+.2f}% | suma {o['suma']:.3f} | {o['mercado']}")
        print("\nPERO: aparecen y desaparecen en milisegundos, compiten bots")
        print("profesionales con mucho mas capital y velocidad. Capturarlas")
        print("con 50 USDC desde un PC normal es MUY dificil. Sigue en SIM.")
    else:
        print("VEREDICTO: no hay arbitrajes ejecutables ahora mismo.")
        print("Los mercados liquidos estan bien valorados (ask YES + ask NO >= 1).")
        print("Esto es honesto y esperable: el 'dinero facil sin riesgo' no")
        print("esta disponible para un retail con 50 USDC. Conviene NO invertir")
        print("en este plan y, si quieres seguir, tratarlo como especulacion")
        print("de alto riesgo con dinero que puedas permitirte perder.")


if __name__ == "__main__":
    main()
