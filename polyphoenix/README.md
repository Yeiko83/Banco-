# 🔥 PolyPhoenix — Agente de trading para Polymarket

Agente que escanea **todos los mercados** de Polymarket 24/7, genera señales,
las filtra con **15 escudos de seguridad** y produce **reportes automáticos**
(CSV + Google Sheets opcional).

Arranca en **modo paper (simulación)** con dinero ficticio contra precios
**reales** de Polymarket. Así puedes ver el rendimiento honesto de la estrategia
sin arriesgar un solo peso.

---

## ⚠️ Lee esto antes de nada — expectativas realistas

Este proyecto nació de una petición de **20% de rentabilidad diaria**. Con todo
el respeto, y por tu propio bien financiero, hay que decirlo claro:

> **Un 20% diario es matemáticamente imposible de sostener.**

- 20% diario durante 1 mes = **×237** tu capital.
- 20% diario durante 1 año = más dinero del que existe en el planeta.
- El mejor fondo de la historia (Medallion, Renaissance Technologies) hace
  **~39% al AÑO**, no al día. Tu meta pedía eso cada dos días.

Cualquier sistema que te prometa 20% diario con dinero real te va a **hacer
perder todo tu capital**, normalmente en semanas. Este agente **no** persigue esa
meta; persigue algo honesto: una estrategia transparente, con gestión de riesgo
seria, que puedes **medir en simulación** antes de decidir nada.

**Objetivos realistas** para un buen sistema (y aun así, difíciles): del orden de
un dígito porcentual **mensual**, con rachas de pérdidas incluidas.

---

## 🏗️ Arquitectura

```
polyphoenix/
├── config.py             Configuración (variables de entorno / .env)
├── polymarket_client.py  Cliente SOLO LECTURA (Gamma + CLOB) + feed sintético
├── strategy.py           Señales: momentum + reversión + análisis de spread
├── risk.py               Los 15 escudos de seguridad (implementados de verdad)
├── portfolio.py          Portafolio virtual, posiciones, PnL, métricas
├── reporting.py          Reportes CSV + Google Sheets opcional
├── agent.py              Ciclo principal 24/7
└── tests/                Pruebas sin dependencia de red
```

## 🛡️ Los 15 escudos (todos activos, no son adorno)

| # | Escudo | Qué hace |
|---|--------|----------|
| 1 | Stop-loss dinámico | Trailing stop desde el máximo alcanzado por posición |
| 2 | Límite diario de pérdidas | Drawdown > 8% ⇒ pausa configurable |
| 3 | Control de posicionamiento | Máx. posiciones y % por mercado |
| 4 | Rebalanceo por volatilidad | Frena entradas si el portafolio se agita |
| 5 | Monitoreo de liquidez | No opera si la profundidad < 5× la posición |
| 6 | Filtro de spread | Veta mercados caros de operar |
| 7 | Detección de manipulación | Marca ratios volumen/liquidez anómalos |
| 8 | Control de frecuencia | Máx. operaciones por hora (anti-overtrading) |
| 9 | Sentimiento extremo | Evita seguir a la manada en precios extremos |
| 10 | Backup de estrategia | 3 pérdidas seguidas ⇒ modo conservador (sizing ×0.4) |
| 11 | Revisión de correlación | Veta posiciones muy correlacionadas (>0.7) |
| 12 | Timeout de seguridad | Sin datos ⇒ diagnóstico y reconexión |
| 13 | Validación de precios | Descarta precios incoherentes con el libro |
| 14 | Ratio riesgo/recompensa | Exige RR mínimo (TP/SL) antes de entrar |
| 15 | Auditoría continua | Cada decisión y alerta queda registrada |

## 🚀 Uso rápido

```bash
cd polyphoenix
pip install -r requirements.txt          # solo 'requests' para modo online

# Prueba rápida sin red (feed sintético), 20 ciclos:
OFFLINE=1 python -m polyphoenix.agent --cycles 20

# Contra datos REALES de Polymarket, en bucle 24/7 (Ctrl+C para parar):
python -m polyphoenix.agent
```

Los reportes aparecen en `reportes/`:
`resumen_diario.csv`, `operaciones.csv`, `metricas.csv`, `alertas.csv`.

## ⚙️ Configuración

Copia `.env.example` a `.env` y ajusta. Todo tiene valores por defecto sensatos.
Lo más importante: `MODE=paper` (seguro) y `CAPITAL` = lo que **realmente**
pondrías (200.000 COP ≈ 50 USD).

### Google Sheets (opcional)
1. Crea un proyecto en Google Cloud y habilita la Google Sheets API.
2. Crea una **service account**, descarga su JSON como `credentials.json`.
3. Crea una hoja con pestañas `RESUMEN_DIARIO`, `OPERACIONES`, `METRICAS`,
   `ALERTAS` y **compártela** con el email de la service account.
4. Pon `GOOGLE_SHEETS_ID` y `GOOGLE_CREDS` en tu `.env`.

## 🧪 Pruebas

```bash
python -m pytest polyphoenix/tests -q        # con pytest
# o sin instalar nada:
python -m polyphoenix.tests.test_core        # (ver run_tests.py)
```

## 💸 Sobre pasar a dinero real (modo live)

El cliente es **solo lectura** a propósito. La ejecución real de órdenes en
Polymarket requiere:
- Wallet en Polygon con USDC, y firma **EIP-712** de cada orden.
- Credenciales del CLOB (API key/secret/passphrase derivadas de la wallet).
- Cumplir los **términos y restricciones de jurisdicción** de Polymarket.

Ese módulo **no** está incluido y `MODE=live` sigue simulando hasta que lo
integres tú, conscientemente. Recomendación fuerte: corre semanas en paper,
mira los reportes reales, y solo entonces decide — con dinero que puedas
permitirte perder por completo.

## 📉 Descargo de responsabilidad

Software educativo. No es asesoría financiera. El trading en mercados de
predicción es de alto riesgo y puedes perder todo tu capital. Los resultados en
simulación **no** garantizan resultados futuros. Úsalo bajo tu responsabilidad.
