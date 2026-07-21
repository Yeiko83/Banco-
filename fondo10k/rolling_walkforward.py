"""
rolling_walkforward.py — La prueba DEFINITIVA de robustez.

En vez de un solo train/test, desliza MUCHAS ventanas consecutivas:
  ventana 1: entrena en [0:1200], prueba en [1200:1500]
  ventana 2: entrena en [300:1500], prueba en [1500:1800]
  ... y asi sucesivamente.

Para cada ventana: confirma cointegracion en train, saca beta, y opera
SOLO en el test de esa ventana (con comisiones). Al final cuenta en cuantas
ventanas gano. Un edge real gana en la MAYORIA; el azar gana ~la mitad o menos.

Uso:
  1) pip install ccxt pandas numpy statsmodels
  2) python rolling_walkforward.py
"""

import sys

SYMBOL_A  = "BNB/USDT"       # el candidato que paso el filtro anterior
SYMBOL_B  = "NEAR/USDT"
TIMEFRAME = "1h"
TOTAL     = 5000             # ~208 dias a 1h
TRAIN_LEN = 1200             # velas de entrenamiento por ventana
TEST_LEN  = 300              # velas de prueba por ventana
STEP      = 300              # cuanto avanza cada ventana

FEE_RATE = 0.001; CAPITAL = 50.0
Z_WINDOW = 100; ENTRY_Z = 2.0; EXIT_Z = 0.5; STOP_Z = 3.5


def fetch_history(ex, symbol):
    import pandas as pd
    tf_ms = ex.parse_timeframe(TIMEFRAME) * 1000
    since = ex.milliseconds() - TOTAL * tf_ms; rows = []
    while len(rows) < TOTAL:
        batch = ex.fetch_ohlcv(symbol, timeframe=TIMEFRAME, since=since, limit=1000)
        if not batch: break
        rows += batch; since = batch[-1][0] + tf_ms
        if len(batch) < 1000: break
    df = pd.DataFrame(rows, columns=["ts","o","h","l","close","v"]).drop_duplicates("ts")
    df["ts"] = pd.to_datetime(df["ts"], unit="ms")
    return df.set_index("ts")["close"]


def coint_pvalue(a, b):
    import statsmodels.api as sm
    from statsmodels.tsa.stattools import adfuller, coint
    beta = float(sm.OLS(a.values, sm.add_constant(b.values)).fit().params[1])
    spread = a - beta * b
    _, eg_p, _ = coint(a, b); adf_p = adfuller(spread.dropna())[1]
    return eg_p, adf_p, beta


def backtest(a_s, b_s, beta, spread):
    import numpy as np
    a = a_s.values; b = b_s.values
    mean = spread.rolling(Z_WINDOW).mean(); std = spread.rolling(Z_WINDOW).std()
    z = ((spread - mean) / std).values; n = len(a)
    pos = 0; ua = ub = 0.0; cash = 0.0; fees = 0.0
    trades = []; eqf = CAPITAL; peak = CAPITAL; maxdd = 0.0
    for i in range(1, n):
        if pos != 0:
            cash += pos * (ua*(a[i]-a[i-1]) - ub*(b[i]-b[i-1]))
        zi = z[i]
        if np.isnan(zi): continue
        if pos != 0 and (abs(zi) < EXIT_Z or abs(zi) > STOP_Z):
            fee = FEE_RATE*(ua*a[i]+ub*b[i]); cash -= fee; fees += fee
            trades.append(1); pos, ua, ub = 0, 0.0, 0.0
        elif pos == 0 and abs(zi) >= ENTRY_Z:
            ua = CAPITAL/(a[i]+beta*b[i]); ub = beta*ua
            pos = -1 if zi > 0 else 1
            fee = FEE_RATE*(ua*a[i]+ub*b[i]); cash -= fee; fees += fee
        eqf = CAPITAL + cash; peak = max(peak, eqf); maxdd = min(maxdd, (eqf-peak)/peak)
    return (eqf/CAPITAL - 1)*100, len(trades), fees, maxdd*100


def main():
    try:
        import ccxt, pandas as pd
    except ImportError:
        print("Corre:  pip install ccxt pandas numpy statsmodels"); sys.exit(1)
    ex = ccxt.binance({"enableRateLimit": True})
    print(f"Bajando {SYMBOL_A} y {SYMBOL_B} ({TOTAL} velas {TIMEFRAME})...")
    a = fetch_history(ex, SYMBOL_A); b = fetch_history(ex, SYMBOL_B)
    df = pd.concat([a, b], axis=1, keys=["A","B"]).dropna()
    print(f"Alineadas: {len(df)} velas.\n")

    print("=" * 74)
    print(f"  WALK-FORWARD RODANTE:  {SYMBOL_A} / {SYMBOL_B}")
    print("=" * 74)
    print(f"  {'Ventana':<9}{'CointTrain':>12}{'OOS %':>10}{'Trades':>9}{'MaxDD%':>10}")
    print("  " + "-" * 66)

    fold = 0; ganadoras = 0; total_oos = 0.0; validas = 0
    start = 0
    while start + TRAIN_LEN + TEST_LEN <= len(df):
        fold += 1
        train = df.iloc[start:start+TRAIN_LEN]
        eg_tr, adf_tr, beta = coint_pvalue(train["A"], train["B"])
        coint_ok = eg_tr < 0.05 and adf_tr < 0.05

        t0 = start + TRAIN_LEN
        seg = df.iloc[t0 - Z_WINDOW : t0 + TEST_LEN]
        full_spread = seg["A"] - beta * seg["B"]
        ret, ntr, fees, dd = backtest(seg["A"], seg["B"], beta, full_spread)

        marca = "SI" if coint_ok else "no"
        print(f"  #{fold:<8}{marca:>12}{ret:>+10.2f}{ntr:>9}{dd:>10.2f}")
        if coint_ok:
            validas += 1
            total_oos += ret
            if ret > 0:
                ganadoras += 1
        start += STEP

    print("  " + "-" * 66)
    print("=" * 74)
    print("  RESUMEN")
    print("=" * 74)
    print(f"  Ventanas cointegradas en train... {validas}")
    print(f"  De esas, ganadoras fuera muestra. {ganadoras}")
    if validas:
        pct = ganadoras / validas * 100
        print(f"  % de ventanas ganadoras.......... {pct:.0f}%")
        print(f"  OOS promedio por ventana......... {total_oos/validas:+.2f}%")
        print("-" * 74)
        if pct >= 65:
            print("  VEREDICTO: ROBUSTO. Gana en la mayoria de epocas.")
            print("  Candidato serio para paper trading.")
        elif pct >= 50:
            print("  VEREDICTO: DUDOSO. Cerca de una moneda al aire. No arriesgar.")
        else:
            print("  VEREDICTO: NO robusto. El +14.6% anterior fue suerte de una epoca.")
    else:
        print("  No hubo ventanas cointegradas. Descartar el par.")
    print("=" * 74)


if __name__ == "__main__":
    main()
