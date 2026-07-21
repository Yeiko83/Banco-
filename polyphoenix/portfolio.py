"""
Portafolio virtual y métricas.

Modela el capital, las posiciones abiertas y el PnL en modo simulación
(paper trading). Los precios de Polymarket son probabilidades (0-1); una
posición 'buy' compra shares del outcome YES a 'precio' y su valor sigue al
precio del mercado. 'sell' equivale a comprar NO (valor = 1 - precio).
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from statistics import mean, pstdev
from typing import Dict, List, Optional


@dataclass
class Posicion:
    id: str
    market_id: str
    token_id: str
    side: str            # buy | sell
    precio_entrada: float
    shares: float        # nº de shares
    costo: float         # capital comprometido (USD)
    estrategia: str
    motivo: str
    confianza: float
    stop_loss: float
    take_profit: float
    ts_apertura: float = field(default_factory=time.time)
    precio_max: float = 0.0   # para trailing stop (escudo 1)

    def valor_unitario(self, precio_mkt: float) -> float:
        """Precio efectivo de mi lado del mercado."""
        return precio_mkt if self.side == "buy" else (1.0 - precio_mkt)

    def valor(self, precio_mkt: float) -> float:
        return self.shares * self.valor_unitario(precio_mkt)

    def pnl(self, precio_mkt: float) -> float:
        return self.valor(precio_mkt) - self.costo


@dataclass
class Trade:
    ts: float
    market_id: str
    side: str
    precio_entrada: float
    precio_salida: float
    shares: float
    pnl: float
    retorno_pct: float
    estrategia: str
    motivo_entrada: str
    motivo_salida: str
    confianza: float


class Portfolio:
    def __init__(self, cfg):
        self.cfg = cfg
        self.cash = cfg.capital_inicial
        self.posiciones: Dict[str, Posicion] = {}
        self.historial: List[Trade] = []
        self._equity_curve: List[float] = [cfg.capital_inicial]
        self._contador = 0

    # ---- Estado --------------------------------------------------------- #
    @property
    def equity(self) -> float:  # valor total (cash + costo comprometido)
        return self.cash + sum(p.costo for p in self.posiciones.values())

    def valor_mercado(self, precios: Dict[str, float]) -> float:
        val = self.cash
        for p in self.posiciones.values():
            val += p.valor(precios.get(p.token_id, p.precio_entrada))
        return val

    def exposicion_en_mercado(self, market_id: str) -> float:
        return sum(p.costo for p in self.posiciones.values() if p.market_id == market_id)

    def tamano_objetivo(self, cfg, modo_conservador: bool) -> float:
        base = self.cash * cfg.tamano_posicion_pct
        if modo_conservador:                 # escudo 10
            base *= 0.4
        tope = self.equity * cfg.max_posicion_pct
        return max(0.0, min(base, tope))

    def volatilidad_portafolio(self) -> float:
        ec = self._equity_curve[-20:]
        if len(ec) < 3:
            return 0.0
        rets = [(b - a) / a for a, b in zip(ec[:-1], ec[1:]) if a > 0]
        return pstdev(rets) if len(rets) >= 2 else 0.0

    # ---- Operaciones ---------------------------------------------------- #
    def abrir(self, sig, tamano: float) -> Optional[Posicion]:
        if tamano <= 0 or tamano > self.cash:
            return None
        precio_lado = sig.precio if sig.side == "buy" else (1.0 - sig.precio)
        if precio_lado <= 0:
            return None
        shares = tamano / precio_lado
        self._contador += 1
        pos = Posicion(
            id=f"P{self._contador:06d}",
            market_id=sig.market_id,
            token_id=sig.token_id,
            side=sig.side,
            precio_entrada=sig.precio,
            shares=shares,
            costo=tamano,
            estrategia=sig.estrategia,
            motivo=sig.motivo,
            confianza=sig.confianza,
            stop_loss=self.cfg.stop_loss_pct,
            take_profit=self.cfg.take_profit_pct,
            precio_max=precio_lado,
        )
        self.cash -= tamano
        self.posiciones[pos.id] = pos
        return pos

    def cerrar(self, pos_id: str, precio_mkt: float, motivo: str) -> Optional[Trade]:
        pos = self.posiciones.pop(pos_id, None)
        if not pos:
            return None
        valor = pos.valor(precio_mkt)
        self.cash += valor
        pnl = valor - pos.costo
        ret = pnl / pos.costo if pos.costo else 0.0
        precio_salida = pos.valor_unitario(precio_mkt)
        trade = Trade(
            ts=time.time(),
            market_id=pos.market_id,
            side=pos.side,
            precio_entrada=pos.precio_entrada,
            precio_salida=round(precio_salida, 4),
            shares=round(pos.shares, 4),
            pnl=round(pnl, 4),
            retorno_pct=round(ret * 100, 3),
            estrategia=pos.estrategia,
            motivo_entrada=pos.motivo,
            motivo_salida=motivo,
            confianza=pos.confianza,
        )
        self.historial.append(trade)
        return trade

    def marcar(self, precios: Dict[str, float]) -> List[tuple]:
        """
        Gestiona posiciones abiertas: aplica ESCUDO 1 (trailing stop dinámico),
        stop-loss y take-profit. Devuelve lista de (trade, motivo) cerrados.
        """
        cerrados = []
        for pos_id, pos in list(self.posiciones.items()):
            pm = precios.get(pos.token_id)
            if pm is None:
                continue
            precio_lado = pos.valor_unitario(pm)
            entrada = pos.valor_unitario(pos.precio_entrada)
            pos.precio_max = max(pos.precio_max, precio_lado)

            ret = (precio_lado - entrada) / entrada if entrada else 0.0
            # Trailing stop (escudo 1): cae X% desde el máximo alcanzado.
            caida_desde_max = (pos.precio_max - precio_lado) / pos.precio_max if pos.precio_max else 0.0

            motivo = None
            if ret >= pos.take_profit:
                motivo = f"take-profit +{ret:.1%}"
            elif ret <= -pos.stop_loss:
                motivo = f"stop-loss {ret:.1%}"
            elif caida_desde_max >= pos.stop_loss and precio_lado > entrada:
                motivo = f"trailing-stop desde máx (-{caida_desde_max:.1%})"
            if motivo:
                tr = self.cerrar(pos_id, pm, motivo)
                if tr:
                    cerrados.append((tr, motivo))

        self._equity_curve.append(self.valor_mercado(precios))
        del self._equity_curve[:-500]
        return cerrados

    # ---- Métricas ------------------------------------------------------- #
    def win_rate(self) -> float:
        if not self.historial:
            return 0.0
        wins = sum(1 for t in self.historial if t.pnl > 0)
        return 100 * wins / len(self.historial)

    def sharpe(self) -> float:
        rets = [t.retorno_pct for t in self.historial]
        if len(rets) < 2:
            return 0.0
        s = pstdev(rets)
        return mean(rets) / s if s else 0.0

    def drawdown_maximo(self) -> float:
        pico, maxdd = self._equity_curve[0], 0.0
        for v in self._equity_curve:
            pico = max(pico, v)
            maxdd = max(maxdd, (pico - v) / pico if pico else 0.0)
        return maxdd * 100

    def factor_beneficio(self) -> float:
        g = sum(t.pnl for t in self.historial if t.pnl > 0)
        p = abs(sum(t.pnl for t in self.historial if t.pnl < 0))
        return g / p if p else (g if g else 0.0)
