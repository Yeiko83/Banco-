"""
walkforward.py — La prueba de fuego: validacion FUERA DE MUESTRA (out-of-sample).

Idea:
  - Parte la historia en dos: ENTRENAMIENTO (mitad vieja) y PRUEBA (mitad nueva).
  - Confirma la cointegracion y calcula beta SOLO con el entrenamiento.
  - Opera SOLO en el periodo de prueba, que el sistema nunca vio.
  Si gana ahi (tras comisiones), el edge es real. Si pierde, era espejismo.

Uso:
  1) pip install ccxt pandas numpy statsmodels
  2) python walkforward.py
"""

import sys

SYMBOL_A   = "XRP/USDT"
SYMBOL_B   = "NEAR/USDT"
TIMEFRAME  = "1h"
TOTAL      = 3000        # velas totales (~125 dias a 1h). Se parten en train/test.
TRAIN_FRAC = 0.60        # 60% para entrenar, 40% para probar

FEE_RATE = 0.001; CAPITAL = 50.0
Z_WINDOW = 100; ENTRY_Z = 2.0; EXIT_Z = 0.5; STOP_Z = 3.5


def fetch_history(symbol):
    import ccxt, pandas as pd
    ex = ccxt.binance({"enableRateLimit": True})
    tf_ms = ex.parse_timeframe(TIMEFRAME) * 1000
    since = ex.milliseconds() - TOTAL * tf_ms
    rows = []
    while len(rows) < TOTAL:
        batch = ex.fetch_ohlcv(symbol, timeframe=TIMEFRAME, since=since, limit=1000)
        if not batch:
            break
        rows += batch
        since = batch[-1][0] + tf_ms
        if len(batch) < 1000:
            break
    df = pd.DataFrame(rows, columns=["ts", "o", "h", "l", "close", "v"]).drop_duplicates("ts")
    df["ts"] = pd.to_datetime(df["ts"], unit="ms")
    return df.set_index("ts")["close"]


def coint_pvalue(a, b):
    import statsmodels.api as sm
    from statsmodels.tsa.stattools import adfuller, coint
    beta = float(sm.OLS(a.values, sm.add_constant(b.values)).fit().params[1])
    spread = a - beta * b
    _, eg_p, _ = coint(a, b)
    adf_p = adfuller(spread.dropna())[1]
    return eg_p, adf_p, beta


def backtest(a_s, b_s, beta, spread):
    """Backtest sobre el tramo dado (spread ya calculado con beta de train)."""
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
        if np.isnan(zi):
            continue
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
        import pandas as pd
    except ImportError:
        print("Corre:  pip install ccxt pandas numpy statsmodels"); sys.exit(1)

    print(f"Bajando historia de {SYMBOL_A} y {SYMBOL_B} ({TOTAL} velas {TIMEFRAME})...")
    a = fetch_history(SYMBOL_A); b = fetch_history(SYMBOL_B)
    df = pd.concat([a, b], axis=1, keys=["A", "B"]).dropna()
    print(f"Alineadas: {len(df)} velas.\n")

    cut = int(len(df) * TRAIN_FRAC)
    train = df.iloc[:cut]; test = df.iloc[cut:]

    # --- Entrenamiento: confirmar cointegracion y sacar beta ---
    eg_tr, adf_tr, beta = coint_pvalue(train["A"], train["B"])
    print("=" * 60)
    print("  ENTRENAMIENTO (mitad vieja)")
    print("=" * 60)
    print(f"  Velas..................... {len(train)}")
    print(f"  p-valor Engle-Granger..... {eg_tr:.4f}  (<0.05 = cointegrado)")
    print(f"  Hedge ratio (beta)........ {beta:.6f}")
    train_ok = eg_tr < 0.05 and adf_tr < 0.05
    print(f"  Cointegrado en train?..... {'SI' if train_ok else 'NO'}")
    print("=" * 60 + "\n")

    if not train_ok:
        print("No estaba cointegrado ni en el entrenamiento. Descartar el par.")
        return

    # --- Prueba: operar en el tramo nuevo con beta fija de train ---
    # spread con beta de TRAIN, calculado sobre la serie completa para el warmup
    # del z-score, pero backtesteando solo el tramo de prueba.
    full_spread = df["A"] - beta * df["B"]
    test_spread = full_spread.iloc[cut - Z_WINDOW:]        # incluye warmup del z
    test_a = df["A"].iloc[cut - Z_WINDOW:]
    test_b = df["B"].iloc[cut - Z_WINDOW:]
    ret, ntr, fees, dd = backtest(test_a, test_b, beta, test_spread)

    # p-valor de cointegracion tambien en el tramo de prueba (informativo)
    eg_te, adf_te, _ = coint_pvalue(test["A"], test["B"])

    print("=" * 60)
    print("  PRUEBA FUERA DE MUESTRA (mitad nueva, nunca vista)")
    print("=" * 60)
    print(f"  Velas..................... {len(test)}")
    print(f"  p-valor Engle-Granger..... {eg_te:.4f}  (informativo)")
    print(f"  Rentabilidad (con fees)... {ret:+.2f}%")
    print(f"  Operaciones............... {ntr}")
    print(f"  Comisiones................ {fees:.2f} USDT")
    print(f"  Maximo drawdown........... {dd:.2f}%")
    print("=" * 60)
    if ret > 0 and eg_te < 0.10:
        print("  VEREDICTO: SOBREVIVIO fuera de muestra. Candidato REAL.")
        print("  Siguiente: paper trading en vivo antes de dinero real.")
    else:
        print("  VEREDICTO: NO sobrevivio fuera de muestra.")
        print("  El +4.98% original era espejismo (sobreajuste). Descartar.")
    print("=" * 60)


if __name__ == "__main__":
    main()
