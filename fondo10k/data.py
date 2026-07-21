"""
data.py — Obtencion de precios.

Dos fuentes:
  1. fetch_ccxt()      -> velas reales de Binance (usar en el servidor Oracle Cloud).
  2. synthetic_pair()  -> par cointegrado simulado para probar el motor sin red.

Ambas devuelven un DataFrame con columnas ['A', 'B'] (precios de cierre alineados).
"""

import numpy as np
import pandas as pd

import config


def fetch_ccxt(symbol_a=None, symbol_b=None, timeframe=None, candles=None):
    """Baja OHLCV real de Binance via ccxt y devuelve los cierres alineados."""
    import ccxt

    symbol_a = symbol_a or config.SYMBOL_A
    symbol_b = symbol_b or config.SYMBOL_B
    timeframe = timeframe or config.TIMEFRAME
    candles = candles or config.CANDLES

    exchange = getattr(ccxt, config.EXCHANGE)({"enableRateLimit": True})

    def _closes(symbol):
        raw = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=candles)
        df = pd.DataFrame(raw, columns=["ts", "open", "high", "low", "close", "vol"])
        df["ts"] = pd.to_datetime(df["ts"], unit="ms")
        return df.set_index("ts")["close"]

    a = _closes(symbol_a)
    b = _closes(symbol_b)
    out = pd.concat([a, b], axis=1, keys=["A", "B"]).dropna()
    return out


def synthetic_pair(n=2000, beta=0.030, seed=42):
    """
    Genera un par cointegrado realista para probar el motor sin red.

    B: camino aleatorio (precio tipo BTC).
    A: A = beta*B + spread, donde spread es un proceso Ornstein-Uhlenbeck
       (reversion a la media) -> por construccion A y B estan cointegrados.
    """
    rng = np.random.default_rng(seed)

    # B: random walk que arranca alto (como BTC)
    b = 60000 + np.cumsum(rng.normal(0, 300, n))

    # spread: proceso de reversion a la media (Ornstein-Uhlenbeck)
    theta, sigma = 0.05, 8.0     # theta = fuerza de reversion, sigma = ruido
    spread = np.zeros(n)
    for t in range(1, n):
        spread[t] = spread[t - 1] + theta * (0 - spread[t - 1]) + rng.normal(0, sigma)

    a = beta * b + 1500 + spread   # A tipo ETH, cointegrado con B

    idx = pd.date_range("2025-01-01", periods=n, freq="h")
    return pd.DataFrame({"A": a, "B": b}, index=idx)


def load_prices():
    """Selecciona la fuente segun config.DATA_MODE."""
    if config.DATA_MODE == "ccxt":
        return fetch_ccxt()
    elif config.DATA_MODE == "synthetic":
        return synthetic_pair(n=config.CANDLES)
    else:
        raise ValueError(f"DATA_MODE desconocido: {config.DATA_MODE}")


if __name__ == "__main__":
    df = load_prices()
    print(f"Fuente: {config.DATA_MODE} | filas: {len(df)}")
    print(df.head())
    print(df.tail())
