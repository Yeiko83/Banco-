"""
validar.py — TODO EN UNO. Backtester de pairs trading (arbitraje estadistico).

Que hace, solo:
  1. Baja datos historicos REALES de Binance (publicos, SIN cuenta ni API keys).
  2. Mide si el par esta cointegrado (si el spread revierte a la media).
  3. Simula la estrategia operacion por operacion, CON comisiones descontadas.
  4. Imprime un reporte con el veredicto.

Como se usa:
  1) pip install ccxt pandas numpy statsmodels
  2) python validar.py
"""

import sys

# ------------------- PARAMETROS (cambia aqui si quieres) -------------------
SYMBOL_A  = "ETH/USDT"   # activo A
SYMBOL_B  = "BTC/USDT"   # activo B (correlacionado con A)
TIMEFRAME = "1h"          # velas de 1 hora
CANDLES   = 1000          # cuantas velas bajar (1000h ~ 41 dias)

FEE_RATE  = 0.001         # 0.10% por fill (comision taker Binance). Se cobra en cada pata.
CAPITAL   = 50.0          # capital en USDT (~200.000 COP). Solo escala el reporte.
COP_USD   = 4000          # tasa aprox COP/USD para mostrar en pesos

Z_WINDOW  = 100           # ventana para media/desviacion del spread
ENTRY_Z   = 2.0           # abrir cuando |z| supera esto
EXIT_Z    = 0.5           # cerrar cuando |z| baja de esto
STOP_Z    = 3.5           # cortar si |z| se dispara mas alla (spread roto)
# ---------------------------------------------------------------------------


def bajar_datos():
    """Baja los cierres reales de Binance. No requiere cuenta ni API key."""
    try:
        import ccxt
    except ImportError:
        print("Falta ccxt. Corre primero:  pip install ccxt pandas numpy statsmodels")
        sys.exit(1)
    import pandas as pd

    ex = ccxt.binance({"enableRateLimit": True})

    def cierres(sym):
        raw = ex.fetch_ohlcv(sym, timeframe=TIMEFRAME, limit=CANDLES)
        df = pd.DataFrame(raw, columns=["ts", "o", "h", "l", "close", "v"])
        df["ts"] = pd.to_datetime(df["ts"], unit="ms")
        return df.set_index("ts")["close"]

    print(f"Bajando {CANDLES} velas de {SYMBOL_A} y {SYMBOL_B} ({TIMEFRAME}) desde Binance...")
    a = cierres(SYMBOL_A)
    b = cierres(SYMBOL_B)
    df = pd.concat([a, b], axis=1, keys=["A", "B"]).dropna()
    print(f"Listo: {len(df)} velas alineadas.\n")
    return df


def analizar_cointegracion(df):
    """Engle-Granger + ADF + hedge ratio (beta)."""
    import statsmodels.api as sm
    from statsmodels.tsa.stattools import adfuller, coint

    a, b = df["A"], df["B"]
    beta = float(sm.OLS(a.values, sm.add_constant(b.values)).fit().params[1])
    spread = a - beta * b
    eg_t, eg_p, _ = coint(a, b)
    adf_stat, adf_p, *_ = adfuller(spread.dropna())
    cointegrado = (eg_p < 0.05) and (adf_p < 0.05)

    print("=" * 56)
    print("  ANALISIS DE COINTEGRACION")
    print("=" * 56)
    print(f"  Hedge ratio (beta)........ {beta:.6f}")
    print(f"  p-valor Engle-Granger..... {eg_p:.4f}   (<0.05 = bueno)")
    print(f"  p-valor ADF del spread.... {adf_p:.4f}   (<0.05 = bueno)")
    print(f"  Cointegrado?.............. {'SI (operar)' if cointegrado else 'NO (no operar)'}")
    print("=" * 56 + "\n")
    return beta, spread, cointegrado


def backtest(df, beta, spread):
    """Simula la estrategia con comisiones. Devuelve metricas."""
    import numpy as np

    a = df["A"].values
    b = df["B"].values
    mean = spread.rolling(Z_WINDOW).mean()
    std = spread.rolling(Z_WINDOW).std()
    z = ((spread - mean) / std).values
    n = len(df)

    pos = 0
    ua = ub = 0.0
    cash = 0.0
    fees = 0.0
    equity = np.full(n, CAPITAL, dtype=float)
    trades = []
    tpnl = 0.0

    for i in range(1, n):
        if pos != 0:
            bar = pos * (ua * (a[i] - a[i - 1]) - ub * (b[i] - b[i - 1]))
            cash += bar
            tpnl += bar

        zi = z[i]
        if np.isnan(zi):
            equity[i] = CAPITAL + cash
            continue

        if pos != 0 and (abs(zi) < EXIT_Z or abs(zi) > STOP_Z):        # cerrar
            fee = FEE_RATE * (ua * a[i] + ub * b[i])
            cash -= fee; fees += fee; tpnl -= fee
            trades.append(tpnl)
            pos, ua, ub, tpnl = 0, 0.0, 0.0, 0.0
        elif pos == 0 and abs(zi) >= ENTRY_Z:                          # abrir
            ua = CAPITAL / (a[i] + beta * b[i])
            ub = beta * ua
            pos = -1 if zi > 0 else 1
            fee = FEE_RATE * (ua * a[i] + ub * b[i])
            cash -= fee; fees += fee; tpnl -= fee

        equity[i] = CAPITAL + cash

    import pandas as pd
    eq = pd.Series(equity, index=df.index)
    ret = (eq.iloc[-1] / CAPITAL - 1) * 100
    dd = ((eq - eq.cummax()) / eq.cummax()).min() * 100
    wins = sum(1 for t in trades if t > 0)
    wr = (wins / len(trades) * 100) if trades else 0.0

    print("=" * 56)
    print("  RESULTADO DEL BACKTEST (con comisiones reales)")
    print("=" * 56)
    print(f"  Capital inicial........... {CAPITAL:.2f} USDT  (~{CAPITAL*COP_USD:,.0f} COP)")
    print(f"  Capital final............. {eq.iloc[-1]:.2f} USDT  (~{eq.iloc[-1]*COP_USD:,.0f} COP)")
    print(f"  Rentabilidad.............. {ret:+.2f}%")
    print(f"  Numero de operaciones..... {len(trades)}")
    print(f"  % ganadoras............... {wr:.1f}%")
    print(f"  Comisiones totales........ {fees:.4f} USDT")
    print(f"  Maximo drawdown........... {dd:.2f}%")
    print("=" * 56)
    if ret <= 0:
        print("  VEREDICTO: NO sobrevive a las comisiones con este par/capital.")
        print("  NO poner dinero real. Probar otro par o mas capital.")
    else:
        print(f"  VEREDICTO: positivo tras comisiones ({ret:+.2f}%).")
        print("  Siguiente paso: validar en otros periodos (walk-forward).")
    print("=" * 56)


def main():
    df = bajar_datos()
    beta, spread, cointegrado = analizar_cointegracion(df)
    if not cointegrado:
        print("El par NO esta cointegrado en esta ventana. Disciplina: NO se opera.")
        print("Prueba con otro par cambiando SYMBOL_A / SYMBOL_B arriba del archivo.")
        return
    backtest(df, beta, spread)


if __name__ == "__main__":
    main()
