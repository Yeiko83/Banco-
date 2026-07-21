# Fondo 10K — Backtester de Pairs Trading (Arbitraje Estadístico)

Motor para **validar** una estrategia market-neutral de reversión a la media
entre dos activos correlacionados (pairs trading), **con las comisiones reales
descontadas**, antes de arriesgar un solo peso.

> Regla de oro del fondo: no se opera en vivo hasta que el backtest demuestre,
> sobre datos reales y en varios periodos, que la estrategia sobrevive a las
> comisiones. Un par que se ve bonito pero deja de revertir arruina la cuenta.

## Estructura

| Archivo | Qué hace |
|---|---|
| `config.py` | Todos los parámetros: par, timeframe, comisiones, umbrales. |
| `data.py` | Baja datos reales de Binance (`ccxt`) o genera un par simulado. |
| `cointegration.py` | Test de cointegración (Engle-Granger + ADF), hedge ratio, z-score. |
| `backtest.py` | Simula la estrategia operación por operación, con comisiones. |
| `run.py` | Orquesta todo e imprime el reporte. |

## Instalación

```bash
pip install -r requirements.txt
```

## Uso rápido (sin red — para probar el motor)

En `config.py` deja `DATA_MODE = "synthetic"` y corre:

```bash
python run.py
```

Usa un par cointegrado simulado. Sirve solo para comprobar que el motor
funciona; **no** dice nada sobre la rentabilidad real.

## Uso real (en tu servidor Oracle Cloud, donde Binance es alcanzable)

1. En `config.py` cambia:
   ```python
   DATA_MODE = "ccxt"
   ```
2. (Opcional) ajusta el par:
   ```python
   SYMBOL_A = "ETH/USDT"
   SYMBOL_B = "BTC/USDT"
   ```
3. Corre:
   ```bash
   python run.py
   ```

> Nota: este entorno de desarrollo tiene bloqueado el acceso a las APIs de
> exchanges (política de red). Por eso `DATA_MODE = "synthetic"` viene por
> defecto. El modo `ccxt` está pensado para correr en tu VPS.

## Cómo leer el reporte

- **p-valor Engle-Granger / ADF < 0.05** → el par está cointegrado (revierte).
  Si no, `run.py` se niega a operar.
- **Rentabilidad** → ya tiene las comisiones descontadas. Si es negativa, la
  estrategia no sirve con ese par/parámetros/capital.
- **Comisiones totales** → con 50 USDT, este número es grande en proporción.
  Es el principal enemigo de una cuenta pequeña.

## Advertencia honesta

Un backtest positivo **no garantiza** ganancias futuras (sobreajuste, cambio de
régimen, slippage, funding de cortos). Los próximos pasos serios son:
validación walk-forward, out-of-sample, y luego **paper trading** en vivo antes
de tocar dinero real. Con ~50 USDT el objetivo realista de esta fase es
**aprender y validar el sistema**, no generar ingresos.
