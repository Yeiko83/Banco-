"""
run.py — Orquestador del backtester del "Fondo 10K".

Flujo:
  1. Carga precios (Binance real o par simulado, segun config.DATA_MODE).
  2. Prueba cointegracion. Si NO esta cointegrado -> se detiene (no opera).
  3. Calcula el z-score del spread.
  4. Corre el backtest CON comisiones.
  5. Imprime el reporte.

Uso:
    python run.py
Ajusta el par, comisiones y umbrales en config.py.
"""

import config
import data
import cointegration as coint
import backtest as bt


def main():
    print(f"\n[1/4] Cargando precios (modo: {config.DATA_MODE}) ...")
    df = data.load_prices()
    print(f"      {len(df)} velas de {config.SYMBOL_A} vs {config.SYMBOL_B} "
          f"({config.TIMEFRAME})")

    print("\n[2/4] Probando cointegracion ...")
    res = coint.summary(df["A"], df["B"])

    if not res["cointegrado"]:
        print("\nEl par NO esta cointegrado en esta ventana. "
              "Disciplina de hierro: NO se opera. Prueba otro par.\n")
        return

    print("\n[3/4] Calculando z-score del spread ...")
    zscore = coint.spread_zscore(res["spread"], config.Z_WINDOW)

    print("[4/4] Corriendo backtest con comisiones ...\n")
    result = bt.run_backtest(df, res["beta"], zscore)
    bt.print_report(result)


if __name__ == "__main__":
    main()
