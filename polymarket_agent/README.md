# Agente de Polymarket

Agente de trading automatizado para [Polymarket](https://polymarket.com) con
gestion de riesgo, persistencia en MySQL y reportes diario/mensual por correo.

> Construido con herramientas **gratuitas / open source**: Python,
> `py-clob-client` (API oficial de Polymarket), MySQL y cron.

---

## ⚠️ Lee esto antes de arriesgar un peso

1. **Ningun bot gana siempre.** No existe "comprar y vender sin perder nada".
   Este agente *gestiona* el riesgo (stop-loss, timeout, tope de posicion),
   no lo elimina. Si alguien te promete 0 perdidas, te esta engañando.
2. **Polymarket usa USDC sobre la red Polygon**, no pesos colombianos.
   200.000 COP ≈ 50 USDC (ajusta segun la tasa del dia).
3. **Las comisiones importan.** A 30 micro-operaciones diarias de ~1.5 USDC,
   las comisiones y el gas pueden dejarte en negativo aunque aciertes. Por eso
   el reporte separa **utilidad bruta**, **comision** y **utilidad neta**:
   la unica que importa es la neta.
4. **Revisa la legalidad y los Terminos de Servicio** de Polymarket para tu
   pais antes de operar con dinero real.
5. **Empieza SIEMPRE en modo `SIM`.** Solo pasa a `LIVE` cuando la simulacion
   demuestre, con tus propios numeros, que la estrategia gana neto.

---

## Instalacion

```bash
cd polymarket_agent
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # y edita tus valores
```

Crea la base de datos:

```bash
mysql -u TU_USUARIO -p < db/schema.sql
```

---

## Uso

**1) Modo simulacion (por defecto, sin riesgo):**

```bash
python -m src.agent --loop
```

Corre sin credenciales ni conexion: usa un feed de precios simulado y guarda
operaciones ficticias en MySQL para que pruebes toda la logica y los reportes.

**2) Modo real (cuando estes listo):** en el `.env` pon:

```
MODE=LIVE
LIVE_CONFIRM=SI_ENTIENDO_EL_RIESGO
POLY_PRIVATE_KEY=tu_clave_privada
```

Sin esa confirmacion exacta y sin clave, el agente **se niega a operar en real**
(ver `src/config.py -> guard_live`). Es un seguro anti-accidentes.

**3) Reportes manuales:**

```bash
python reports/daily_report.py     # consolida el dia
python reports/monthly_report.py   # suma el mes
```

---

## Parametros (en `.env`)

| Parametro | Por defecto | Que hace |
|---|---|---|
| `CAPITAL_USDC` | 50 | Capital total (~200k COP) |
| `POSITION_SIZE_USDC` | 1.5 | Tamano max por operacion (~6k COP) |
| `MIN_BALANCE_USDC` | 1.5 | Si el saldo baja de esto → **pausa** |
| `MAX_TRADES_PER_DAY` | 30 | Tope de operaciones diarias |
| `MIN_EDGE` | 0.012 | Umbral de entrada (1.2%) |
| `POSITION_TIMEOUT_MIN` | 30 | Cierre forzado por tiempo |
| `TAKE_PROFIT` | 0.02 | Objetivo de ganancia por operacion |
| `STOP_LOSS` | 0.03 | Corte de perdida (el "escudo") |

---

## Automatizacion en el servidor (Hostinger)

Ver `crontab.example`. Resumen:

- **Reporte diario** a las `23:59` hora Colombia.
- **Reporte mensual** el dia 1 a las `00:05`.
- Para el agente en si, se recomienda `systemd` o `pm2` en vez de cron, para
  reiniciarlo si se cae.

Verifica la zona horaria del servidor con `timedatectl` (debe ser
`America/Bogota` o ajusta las horas del cron).

---

## Estructura

```
polymarket_agent/
├── src/
│   ├── config.py            # carga .env + seguro de modo LIVE
│   ├── db.py                # acceso a MySQL
│   ├── polymarket_client.py # cliente real (CLOB) + cliente simulado
│   ├── risk.py              # balance check, tope diario, tamano de posicion
│   ├── strategy.py          # cuando entrar / cuando salir
│   └── agent.py             # bucle principal
├── reports/
│   ├── daily_report.py      # reporte diario 23:59 + CSV + correo
│   └── monthly_report.py    # reporte mensual + CSV + correo
├── db/schema.sql            # tabla operaciones_polymarker
├── crontab.example
├── .env.example
└── requirements.txt
```

---

## Aviso final

Este software se entrega "tal cual", con fines educativos y de automatizacion.
Operar en mercados de prediccion implica **riesgo real de perdida total** del
capital. Tu eres el unico responsable de las decisiones que tome tu cuenta.
Prueba en `SIM`, empieza con montos pequeños y nunca inviertas dinero que no
puedas permitirte perder.
