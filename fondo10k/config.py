"""
config.py — Parametros centrales del backtester de pairs trading.
Todo lo ajustable vive aqui: el par, el timeframe, las comisiones y los umbrales.
"""

# ------------------------------------------------------------------
# 1. EXCHANGE Y PAR A OPERAR
# ------------------------------------------------------------------
EXCHANGE = "binance"          # exchange de ccxt del que se bajan los datos
SYMBOL_A = "ETH/USDT"         # activo A (pata larga/corta segun la senal)
SYMBOL_B = "BTC/USDT"         # activo B (pata contraria, correlacionada)
TIMEFRAME = "1h"              # velas de 1 hora
CANDLES = 2000                # cuantas velas historicas bajar (2000h ~ 83 dias)

# ------------------------------------------------------------------
# 2. COMISIONES Y CAPITAL (LO QUE MATA O SALVA LA ESTRATEGIA)
# ------------------------------------------------------------------
FEE_RATE = 0.001              # 0.10% por fill (taker spot Binance). Se cobra en cada pata.
CAPITAL = 50.0               # capital de trabajo en USDT (~200.000 COP). Solo para escala.
COP_PER_USD = 4000            # tasa aproximada COP/USD, solo para reportar en pesos

# ------------------------------------------------------------------
# 3. PARAMETROS DE LA ESTRATEGIA (REVERSION A LA MEDIA)
# ------------------------------------------------------------------
Z_WINDOW = 100                # ventana (en velas) para media y desviacion del spread
ENTRY_Z = 2.0                 # abrir posicion cuando |z-score| supera este umbral
EXIT_Z = 0.5                  # cerrar cuando |z-score| vuelve por debajo de este umbral
STOP_Z = 3.5                  # stop: cerrar si |z-score| se dispara mas alla (spread roto)

# ------------------------------------------------------------------
# 4. MODO DE DATOS
# ------------------------------------------------------------------
# "ccxt"      -> baja datos reales de Binance (usar en tu servidor Oracle Cloud)
# "synthetic" -> genera un par cointegrado simulado (para probar el motor sin red)
DATA_MODE = "synthetic"
