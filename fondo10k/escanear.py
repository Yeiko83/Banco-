"""
escanear.py — Escanea muchos pares y encuentra los que SI estan cointegrados,
luego les corre el backtest CON comisiones y los ordena por rentabilidad.

Uso:
  1) pip install ccxt pandas numpy statsmodels
  2) python escanear.py
"""

import sys
from itertools import combinations

# ---- Lista de activos liquidos a cruzar (todos contra USDT) ----
SYMBOLS = [
    "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT",
    "ADA/USDT", "AVAX/USDT", "DOT/USDT", "LINK/USDT", "LTC/USDT",
    "BCH/USDT", "ATOM/USDT", "NEAR/USDT", "UNI/USDT", "AAVE/USDT",
]

TIMEFRAME = "1h"
CANDLES   = 1000
FEE_RATE  = 0.001
CAPITAL   = 50.0
Z_WINDOW  = 100
ENTRY_Z   = 2.0
EXIT_Z    = 0.5
STOP_Z    = 3.5


def bajar_todo():
    try:
        import ccxt
    except ImportError:
        print("Falta ccxt. Corre:  pip install ccxt pandas numpy statsmodels")
        sys.exit(1)
    import pandas as pd
    ex = ccxt.binance({"enableRateLimit": True})
    series = {}
    for s in SYMBOLS:
        try:
            raw = ex.fetch_ohlcv(s, timeframe=TIMEFRAME, limit=CANDLES)
            df = pd.DataFrame(raw, columns=["ts", "o", "h", "l", "close", "v"])
            df["ts"] = pd.to_datetime(df["ts"], unit="ms")
            series[s] = df.set_index("ts")["close"]
            print(f"  ok  {s}")
        except Exception as e:
            print(f"  falla {s}: {str(e)[:50]}")
    return series


def test_coint(a, b):
    import statsmodels.api as sm
    from statsmodels.tsa.stattools import adfuller, coint
    beta = float(sm.OLS(a.values, sm.add_constant(b.values)).fit().params[1])
    spread = a - beta * b
    _, eg_p, _ = coint(a, b)
    adf_p = adfuller(spread.dropna())[1]
    ok = (eg_p < 0.05) and (adf_p < 0.05)
    return ok, beta, spread, eg_p, adf_p


def backtest(a_s, b_s, beta, spread):
    import numpy as np, pandas as pd
    a = a_s.values; b = b_s.values
    mean = spread.rolling(Z_WINDOW).mean(); std = spread.rolling(Z_WINDOW).std()
    z = ((spread - mean) / std).values
    n = len(a)
    pos = 0; ua = ub = 0.0; cash = 0.0; fees = 0.0
    trades = []; tpnl = 0.0; eqf = CAPITAL
    peak = CAPITAL; maxdd = 0.0
    for i in range(1, n):
        if pos != 0:
            cash += pos * (ua*(a[i]-a[i-1]) - ub*(b[i]-b[i-1])); tpnl = cash  # aprox
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
        eqf = CAPITAL + cash
        peak = max(peak, eqf); maxdd = min(maxdd, (eqf-peak)/peak)
    ret = (eqf/CAPITAL - 1)*100
    return ret, len(trades), fees, maxdd*100


def main():
    print("Bajando datos de Binance...")
    series = bajar_todo()
    import pandas as pd
    print(f"\nProbando {len(list(combinations(series, 2)))} combinaciones de pares...\n")

    resultados = []
    for s1, s2 in combinations(series, 2):
        df = pd.concat([series[s1], series[s2]], axis=1, keys=["A", "B"]).dropna()
        if len(df) < Z_WINDOW + 50:
            continue
        ok, beta, spread, eg_p, adf_p = test_coint(df["A"], df["B"])
        if ok:
            ret, ntr, fees, dd = backtest(df["A"], df["B"], beta, spread)
            resultados.append((f"{s1} / {s2}", eg_p, ret, ntr, fees, dd))

    print("=" * 74)
    print("  PARES COINTEGRADOS (ordenados por rentabilidad tras comisiones)")
    print("=" * 74)
    if not resultados:
        print("  Ningun par resulto cointegrado en esta ventana.")
        print("  Es un resultado normal y honesto: hoy no hay edge claro aqui.")
        print("  Prueba mas tarde, otro timeframe (cambia TIMEFRAME) o mas velas.")
    else:
        resultados.sort(key=lambda r: r[2], reverse=True)
        print(f"  {'PAR':<22}{'EG p-val':>10}{'Rent%':>9}{'Trades':>8}{'Fees':>9}{'MaxDD%':>9}")
        print("  " + "-" * 70)
        for par, egp, ret, ntr, fees, dd in resultados:
            print(f"  {par:<22}{egp:>10.4f}{ret:>+9.2f}{ntr:>8}{fees:>9.2f}{dd:>9.2f}")
        print("  " + "-" * 70)
        print("  Rent% YA tiene las comisiones descontadas. Positivo = candidato.")
        print("  Aun asi: un solo periodo NO prueba nada. Sigue el walk-forward.")
    print("=" * 74)


if __name__ == "__main__":
    main()
