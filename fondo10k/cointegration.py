"""
cointegration.py — El nucleo estadistico.

- hedge_ratio(): calcula beta con OLS (cuantas unidades de B por 1 de A).
- test_cointegration(): Engle-Granger + ADF. Dice si el spread REVIERTE.
- spread_zscore(): serie de z-score que dispara las operaciones.

Regla de lectura: si el p-valor del test < 0.05, el par esta cointegrado
con 95% de confianza -> tiene sentido operarlo. Si no, NO se opera.
"""

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller, coint


def hedge_ratio(a: pd.Series, b: pd.Series) -> float:
    """OLS  A = alpha + beta*B.  Devuelve beta (el hedge ratio)."""
    x = sm.add_constant(b.values)
    model = sm.OLS(a.values, x).fit()
    return float(model.params[1])


def compute_spread(a: pd.Series, b: pd.Series, beta: float) -> pd.Series:
    """spread = A - beta*B."""
    return a - beta * b


def test_cointegration(a: pd.Series, b: pd.Series) -> dict:
    """
    Corre dos pruebas y devuelve un resumen:
      - coint (Engle-Granger) sobre las dos series.
      - ADF sobre el spread (raiz unitaria = NO revierte).
    """
    beta = hedge_ratio(a, b)
    spread = compute_spread(a, b, beta)

    # Engle-Granger
    eg_t, eg_p, _ = coint(a, b)

    # ADF sobre el spread
    adf_stat, adf_p, *_ = adfuller(spread.dropna())

    cointegrado = (eg_p < 0.05) and (adf_p < 0.05)

    return {
        "beta": beta,
        "eg_pvalue": eg_p,          # p-valor Engle-Granger
        "adf_pvalue": adf_p,        # p-valor ADF sobre el spread
        "cointegrado": cointegrado, # True/False segun 95% de confianza
        "spread": spread,
    }


def spread_zscore(spread: pd.Series, window: int) -> pd.Series:
    """z-score rodante del spread: (spread - media_movil) / desv_movil."""
    mean = spread.rolling(window).mean()
    std = spread.rolling(window).std()
    return (spread - mean) / std


def summary(a: pd.Series, b: pd.Series) -> dict:
    """Resumen listo para imprimir."""
    res = test_cointegration(a, b)
    veredicto = "SI (operar)" if res["cointegrado"] else "NO (no operar)"
    print("=" * 55)
    print("  ANALISIS DE COINTEGRACION")
    print("=" * 55)
    print(f"  Hedge ratio (beta)........ {res['beta']:.5f}")
    print(f"  p-valor Engle-Granger..... {res['eg_pvalue']:.4f}  (<0.05 = bueno)")
    print(f"  p-valor ADF del spread.... {res['adf_pvalue']:.4f}  (<0.05 = bueno)")
    print(f"  Cointegrado?.............. {veredicto}")
    print("=" * 55)
    return res


if __name__ == "__main__":
    import data
    df = data.load_prices()
    summary(df["A"], df["B"])
