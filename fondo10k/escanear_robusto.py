"""
escanear_robusto.py — Escaner con validacion fuera de muestra INTEGRADA.

Combina escanear + walkforward:
  Para cada par:
    1. Baja historia larga y la parte en train (vieja) y test (nueva).
    2. Exige cointegracion en TRAIN (si no, descarta).
    3. Saca beta de train y opera SOLO en test (out-of-sample), con comisiones.
    4. Solo sobreviven los pares con rentabilidad POSITIVA fuera de muestra.

Es mucho mas estricto que escanear.py. Es NORMAL que devuelva 0 pares:
eso significa que hoy no hay un edge robusto aqui, y es una respuesta honesta.

Uso:
  1) pip install ccxt pandas numpy statsmodels
  2) python escanear_robusto.py
"""

import sys
from itertools import combinations

SYMBOLS = [
    "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT",
    "ADA/USDT", "AVAX/USDT", "DOT/USDT", "LINK/USDT", "LTC/USDT",
    "BCH/USDT", "ATOM/USDT", "NEAR/USDT", "UNI/USDT", "AAVE/USDT",
]
TIMEFRAME  = "1h"
TOTAL      = 3000
TRAIN_FRAC = 0.60
FEE_RATE = 0.001; CAPITAL = 50.0
Z_WINDOW = 100; ENTRY_Z = 2.0; EXIT_Z = 0.5; STOP_Z = 3.5


def fetch_history(ex, symbol):
    import pandas as pd
    tf_ms = ex.parse_timeframe(TIMEFRAME) * 1000
    since = ex.milliseconds() - TOTAL * tf_ms
    rows = []
    while len(rows) < TOTAL:
        batch = ex.fetch_ohlcv(symbol, timeframe=TIMEFRAME, since=since, limit=1000)
        if not batch:
            break
        rows += batch; since = batch[-1][0] + tf_ms
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
        import ccxt, pandas as pd
    except ImportError:
        print("Corre:  pip install ccxt pandas numpy statsmodels"); sys.exit(1)

    ex = ccxt.binance({"enableRateLimit": True})
    print(f"Bajando historia larga ({TOTAL} velas {TIMEFRAME}) de {len(SYMBOLS)} activos...")
    series = {}
    for s in SYMBOLS:
        try:
            series[s] = fetch_history(ex, s); print(f"  ok  {s} ({len(series[s])})")
        except Exception as e:
            print(f"  falla {s}: {str(e)[:50]}")

    combos = list(combinations(series, 2))
    print(f"\nProbando {len(combos)} pares con validacion fuera de muestra...\n")

    sobrevivientes = []
    revisados = 0
    for s1, s2 in combos:
        df = pd.concat([series[s1], series[s2]], axis=1, keys=["A", "B"]).dropna()
        if len(df) < TOTAL * 0.8:
            continue
        cut = int(len(df) * TRAIN_FRAC)
        train, test = df.iloc[:cut], df.iloc[cut:]
        eg_tr, adf_tr, beta = coint_pvalue(train["A"], train["B"])
        if not (eg_tr < 0.05 and adf_tr < 0.05):
            continue                                  # no cointegrado en train -> fuera
        revisados += 1
        full_spread = df["A"] - beta * df["B"]
        ts = full_spread.iloc[cut - Z_WINDOW:]
        ta = df["A"].iloc[cut - Z_WINDOW:]; tb = df["B"].iloc[cut - Z_WINDOW:]
        ret, ntr, fees, dd = backtest(ta, tb, beta, ts)
        eg_te, _, _ = coint_pvalue(test["A"], test["B"])
        if ret > 0:                                   # gana fuera de muestra
            sobrevivientes.append((f"{s1} / {s2}", eg_tr, eg_te, ret, ntr, fees, dd))

    print("=" * 78)
    print("  PARES QUE SOBREVIVEN FUERA DE MUESTRA")
    print("=" * 78)
    print(f"  (cointegrados en train: {revisados} | probados en test: {len(sobrevivientes)} ganan)")
    print("-" * 78)
    if not sobrevivientes:
        print("  NINGUN par sobrevivio fuera de muestra.")
        print("  Es la respuesta honesta: hoy no hay edge robusto con estos activos,")
        print("  este timeframe y este capital. No se opera nada. No se pierde nada.")
    else:
        sobrevivientes.sort(key=lambda r: r[3], reverse=True)
        print(f"  {'PAR':<20}{'EGtrain':>9}{'EGtest':>9}{'OOS%':>8}{'Trades':>8}{'Fees':>8}{'DD%':>8}")
        print("  " + "-" * 72)
        for par, egtr, egte, ret, ntr, fees, dd in sobrevivientes:
            print(f"  {par:<20}{egtr:>9.4f}{egte:>9.4f}{ret:>+8.2f}{ntr:>8}{fees:>8.2f}{dd:>8.2f}")
        print("  " + "-" * 72)
        print("  OOS% = rentabilidad en datos NUNCA vistos, con comisiones.")
        print("  Estos SI son candidatos reales para paper trading.")
    print("=" * 78)


if __name__ == "__main__":
    main()
