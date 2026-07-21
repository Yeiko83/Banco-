"""Pruebas de sanidad: no dependen de red (usan feed sintético)."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from polyphoenix.config import Config
from polyphoenix.polymarket_client import SyntheticDataClient, Market
from polyphoenix.portfolio import Portfolio
from polyphoenix.risk import RiskManager, _corr
from polyphoenix.strategy import evaluar_todos, momentum_score, Signal


def test_synthetic_feed_produce_mercados():
    c = SyntheticDataClient(n_mercados=10)
    m = c.get_markets()
    assert len(m) == 10
    assert all(0 <= x.price <= 1 for x in m)


def test_momentum_signo():
    subida = [0.4, 0.42, 0.45, 0.48, 0.52]
    bajada = list(reversed(subida))
    assert momentum_score(subida, 12) > 0
    assert momentum_score(bajada, 12) < 0


def test_correlacion_perfecta():
    a = [0.1, 0.2, 0.3, 0.4]
    assert abs(_corr(a, a) - 1.0) < 1e-6
    assert _corr(a, list(reversed(a))) < 0


def test_portfolio_abrir_cerrar_pnl():
    cfg = Config()
    cfg.capital_inicial = 100.0
    pf = Portfolio(cfg)
    sig = Signal("m1", "T1", "buy", 80, 0.8, "momentum", "test", 0.50)
    pos = pf.abrir(sig, 10.0)
    assert pos is not None
    assert abs(pf.cash - 90.0) < 1e-9
    # precio sube 0.50 -> 0.60 : ganancia
    tr = pf.cerrar(pos.id, 0.60, "test")
    assert tr.pnl > 0
    assert pf.cash > 100.0


def test_escudo_spread_veta():
    cfg = Config()
    rm = RiskManager(cfg)
    pf = Portfolio(cfg)
    mk = Market("m1", "q", "T1", 0.5, 0.30, 0.70, 100000, 5000, [0.5] * 10)  # spread enorme
    sig = Signal("m1", "T1", "buy", 90, 0.9, "momentum", "x", 0.5)
    permitido, alertas = rm.evaluar(sig, mk, pf, [mk])
    assert not permitido
    assert any(a.escudo == 6 for a in alertas)


def test_escudo_ratio_rr():
    cfg = Config()
    cfg.take_profit_pct = 0.05
    cfg.stop_loss_pct = 0.10   # RR = 0.5 < 1.5 -> veta
    rm = RiskManager(cfg)
    pf = Portfolio(cfg)
    mk = Market("m1", "q", "T1", 0.5, 0.495, 0.505, 100000, 5000, [0.5] * 10)
    sig = Signal("m1", "T1", "buy", 90, 0.9, "momentum", "x", 0.5)
    permitido, alertas = rm.evaluar(sig, mk, pf, [mk])
    assert not permitido
    assert any(a.escudo == 14 for a in alertas)


def test_evaluar_todos_ordena_por_score():
    cfg = Config()
    cfg.umbral_entrada = 0
    c = SyntheticDataClient(n_mercados=20)
    for _ in range(15):        # acumular historial
        mercados = c.get_markets()
    señales = evaluar_todos(mercados, cfg)
    scores = [s.score for s in señales]
    assert scores == sorted(scores, reverse=True)
