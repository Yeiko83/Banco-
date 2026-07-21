"""
backtest.py — Motor de simulacion de la estrategia, CON comisiones.

Estrategia (reversion a la media sobre el spread):
  z > +ENTRY_Z   -> abrir CORTO en el spread (corto A, largo B)
  z < -ENTRY_Z   -> abrir LARGO en el spread (largo A, corto B)
  |z| < EXIT_Z   -> cerrar (tomar ganancia por reversion)
  |z| > STOP_Z   -> cerrar (stop: el spread se rompio)

Dimensionamiento beta-neutral: 1 unidad de A contra beta unidades de B,
escalado para que la exposicion bruta = CAPITAL.

Las comisiones (FEE_RATE por fill) se cobran en CADA apertura y CADA cierre,
sobre las dos patas. Ese es el costo que decide si la estrategia sobrevive.
"""

import numpy as np
import pandas as pd

import config


def run_backtest(df, beta, zscore,
                 entry_z=None, exit_z=None, stop_z=None,
                 fee_rate=None, capital=None):
    entry_z = config.ENTRY_Z if entry_z is None else entry_z
    exit_z = config.EXIT_Z if exit_z is None else exit_z
    stop_z = config.STOP_Z if stop_z is None else stop_z
    fee_rate = config.FEE_RATE if fee_rate is None else fee_rate
    capital = config.CAPITAL if capital is None else capital

    a = df["A"].values
    b = df["B"].values
    z = zscore.values
    n = len(df)

    pos = 0              # 0 flat, +1 largo spread, -1 corto spread
    units_a = 0.0
    units_b = 0.0
    cash_pnl = 0.0       # PnL realizado + comisiones acumuladas (negativas)
    equity = np.full(n, capital, dtype=float)

    total_fees = 0.0
    trades = []          # lista de (pnl_del_trade) para estadisticas
    trade_pnl = 0.0      # PnL acumulado del trade abierto

    def leg_notional(i):
        return units_a * a[i] + units_b * b[i]

    for i in range(1, n):
        # --- marca a mercado la posicion abierta ---
        if pos != 0:
            bar_pnl = pos * (units_a * (a[i] - a[i - 1]) - units_b * (b[i] - b[i - 1]))
            cash_pnl += bar_pnl
            trade_pnl += bar_pnl

        zi = z[i]
        if np.isnan(zi):
            equity[i] = capital + cash_pnl
            continue

        # --- logica de salida ---
        if pos != 0 and (abs(zi) < exit_z or abs(zi) > stop_z):
            fee = fee_rate * leg_notional(i)          # comision de cierre
            cash_pnl -= fee
            total_fees += fee
            trade_pnl -= fee
            trades.append(trade_pnl)
            pos, units_a, units_b, trade_pnl = 0, 0.0, 0.0, 0.0

        # --- logica de entrada (solo si estamos planos) ---
        elif pos == 0 and abs(zi) >= entry_z:
            units_a = capital / (a[i] + beta * b[i])   # escala beta-neutral
            units_b = beta * units_a
            pos = -1 if zi > 0 else 1                   # z alto -> corto spread
            fee = fee_rate * leg_notional(i)           # comision de apertura
            cash_pnl -= fee
            total_fees += fee
            trade_pnl -= fee

        equity[i] = capital + cash_pnl

    # --- metricas ---
    eq = pd.Series(equity, index=df.index)
    ret_pct = (eq.iloc[-1] / capital - 1) * 100
    running_max = eq.cummax()
    drawdown = (eq - running_max) / running_max
    max_dd = drawdown.min() * 100
    n_trades = len(trades)
    wins = sum(1 for t in trades if t > 0)
    win_rate = (wins / n_trades * 100) if n_trades else 0.0

    return {
        "equity": eq,
        "return_pct": ret_pct,
        "final_equity": eq.iloc[-1],
        "total_fees": total_fees,
        "n_trades": n_trades,
        "win_rate": win_rate,
        "max_drawdown_pct": max_dd,
        "trades": trades,
    }


def print_report(res, capital=None):
    capital = config.CAPITAL if capital is None else capital
    cop = config.COP_PER_USD
    print("=" * 55)
    print("  RESULTADO DEL BACKTEST (con comisiones)")
    print("=" * 55)
    print(f"  Capital inicial........... {capital:.2f} USDT  (~{capital*cop:,.0f} COP)")
    print(f"  Capital final............. {res['final_equity']:.2f} USDT  (~{res['final_equity']*cop:,.0f} COP)")
    print(f"  Rentabilidad.............. {res['return_pct']:+.2f}%")
    print(f"  Numero de operaciones..... {res['n_trades']}")
    print(f"  % operaciones ganadoras... {res['win_rate']:.1f}%")
    print(f"  Comisiones totales........ {res['total_fees']:.4f} USDT")
    print(f"  Maximo drawdown........... {res['max_drawdown_pct']:.2f}%")
    print("=" * 55)
    if res["return_pct"] <= 0:
        print("  VEREDICTO: la estrategia NO sobrevive a las comisiones con")
        print("  este par/parametros/capital. No poner dinero real todavia.")
    else:
        gross_hint = res["return_pct"]
        print(f"  VEREDICTO: positivo tras comisiones ({gross_hint:+.2f}%).")
        print("  Siguiente paso: validar en otros periodos (walk-forward).")
    print("=" * 55)
