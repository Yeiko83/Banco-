"""
Estrategia de generación de señales.

Combina tres análisis honestos y bien definidos sobre datos reales:
  - Momentum: cambio de precio normalizado por volatilidad reciente.
  - Reversión a la media: entradas contrarias tras sobre-reacciones.
  - Valor de spread/liquidez: penaliza mercados caros de operar.

Devuelve un score 0-100 y la dirección (buy/sell del outcome YES).
No promete predecir el futuro: es un motor de reglas transparente.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import mean, pstdev
from typing import List, Optional


@dataclass
class Signal:
    market_id: str
    token_id: str
    side: str          # "buy" (apostar a YES) | "sell" (apostar a NO)
    score: float       # 0-100
    confianza: float   # 0-1
    estrategia: str
    motivo: str
    precio: float


def _retornos(hist: List[float]) -> List[float]:
    out = []
    for a, b in zip(hist[:-1], hist[1:]):
        if a > 0:
            out.append((b - a) / a)
    return out


def momentum_score(hist: List[float], ventana: int) -> float:
    """Momentum reciente normalizado por volatilidad. Rango ~[-1, 1]."""
    h = hist[-(ventana + 1):]
    if len(h) < 3:
        return 0.0
    rets = _retornos(h)
    if not rets:
        return 0.0
    vol = pstdev(rets) or 1e-6
    m = mean(rets) / vol
    return max(-1.0, min(1.0, m / 3.0))   # aplana colas


def reversion_score(hist: List[float], ventana: int) -> float:
    """Detecta sobre-reacción: fuerte desviación vs media -> señal contraria."""
    h = hist[-(ventana + 1):]
    if len(h) < 5:
        return 0.0
    base = mean(h[:-1])
    actual = h[-1]
    desv = (actual - base) / (base or 1e-6)
    # Sobre-reacción marcada (>12%) sugiere reversión.
    if abs(desv) < 0.12:
        return 0.0
    return max(-1.0, min(1.0, -desv))     # signo contrario al movimiento


def evaluar_mercado(mk, cfg) -> Optional[Signal]:
    """Combina las señales en un único Signal si supera el umbral."""
    hist = mk.historial
    if len(hist) < 3:
        return None

    mom = momentum_score(hist, cfg.ventana)          # [-1,1]
    rev = reversion_score(hist, cfg.ventana)          # [-1,1]

    # Ponderación: momentum manda, reversión modula.
    combinado = 0.7 * mom + 0.3 * rev                 # [-1,1]

    # Penalización por spread alto (caro de operar) y baja liquidez.
    pen_spread = min(1.0, mk.spread_pct / max(cfg.spread_max_pct, 1e-6))
    factor_liq = 1.0 if mk.liquidez >= 1000 else 0.6

    direccion = "buy" if combinado >= 0 else "sell"
    fuerza = abs(combinado) * (1 - 0.5 * pen_spread) * factor_liq  # 0-1

    score = round(100 * fuerza, 1)
    if score < cfg.umbral_entrada:
        return None

    if abs(mom) >= abs(rev):
        estrategia, motivo = "momentum", f"momentum={mom:+.2f} vol-normalizado"
    else:
        estrategia, motivo = "reversion", f"reversion={rev:+.2f} tras sobre-reacción"

    return Signal(
        market_id=mk.id,
        token_id=mk.token_id,
        side=direccion,
        score=score,
        confianza=round(fuerza, 3),
        estrategia=estrategia,
        motivo=f"{motivo}; spread={mk.spread_pct:.1%}; liq=${mk.liquidez:,.0f}",
        precio=mk.price,
    )


def evaluar_todos(mercados, cfg) -> List[Signal]:
    señales = [s for s in (evaluar_mercado(m, cfg) for m in mercados) if s]
    señales.sort(key=lambda s: s.score, reverse=True)
    return señales
