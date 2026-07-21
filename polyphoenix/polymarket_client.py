"""
Cliente de datos de Polymarket (SOLO LECTURA).

- En línea: consulta los endpoints públicos reales de Polymarket
  (Gamma API para mercados, CLOB API para libros de órdenes / precios).
  Estos endpoints son públicos y no requieren autenticación para leer.
- Offline: usa un feed sintético con caminata aleatoria para poder
  desarrollar y probar sin acceso a la red.

IMPORTANTE: este cliente NO envía órdenes. La ejecución real de órdenes en
Polymarket requiere firma EIP-712 en Polygon y credenciales del CLOB; se deja
deshabilitada a propósito hasta que el usuario active el modo 'live'
conscientemente. En modo 'paper' los fills se simulan localmente.
"""
from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

try:
    import requests  # opcional; solo necesario en modo online
except Exception:  # pragma: no cover
    requests = None


@dataclass
class Market:
    """Un mercado con su token de resultado 'YES' y su precio actual (0-1)."""
    id: str
    question: str
    token_id: str
    price: float                       # precio del outcome YES (probabilidad)
    best_bid: float
    best_ask: float
    liquidez: float                    # profundidad aproximada en USD
    volumen_24h: float
    historial: List[float] = field(default_factory=list)

    @property
    def spread(self) -> float:
        if self.best_ask <= 0:
            return 1.0
        return max(0.0, (self.best_ask - self.best_bid))

    @property
    def spread_pct(self) -> float:
        mid = (self.best_ask + self.best_bid) / 2 or 1e-9
        return self.spread / mid


# --------------------------------------------------------------------------- #
# Cliente en línea (datos reales de Polymarket)
# --------------------------------------------------------------------------- #
class PolymarketDataClient:
    def __init__(self, gamma_url: str, clob_url: str, timeout: int = 15):
        self.gamma_url = gamma_url.rstrip("/")
        self.clob_url = clob_url.rstrip("/")
        self.timeout = timeout
        self._hist: Dict[str, List[float]] = {}

    def _get(self, url: str, params: Optional[dict] = None) -> Optional[object]:
        if requests is None:
            raise RuntimeError("La librería 'requests' no está instalada (pip install requests)")
        resp = requests.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def get_markets(self, limite: int = 200) -> List[Market]:
        """Trae mercados abiertos de la Gamma API y arma objetos Market."""
        data = self._get(
            f"{self.gamma_url}/markets",
            params={"closed": "false", "active": "true", "limit": limite},
        )
        mercados: List[Market] = []
        for m in data or []:
            try:
                mk = self._parse_market(m)
                if mk is None:
                    continue
                # Mantener historial de precios entre llamadas
                h = self._hist.setdefault(mk.token_id, [])
                h.append(mk.price)
                del h[:-256]
                mk.historial = list(h)
                mercados.append(mk)
            except Exception:
                continue
        return mercados

    def _parse_market(self, m: dict) -> Optional[Market]:
        import json as _json

        toks = m.get("clobTokenIds")
        if isinstance(toks, str):
            try:
                toks = _json.loads(toks)
            except Exception:
                toks = None
        if not toks:
            return None
        token_id = toks[0]

        prices = m.get("outcomePrices")
        if isinstance(prices, str):
            try:
                prices = _json.loads(prices)
            except Exception:
                prices = None
        price = float(prices[0]) if prices else float(m.get("lastTradePrice") or 0.5)

        bid = float(m.get("bestBid") or max(0.0, price - 0.01))
        ask = float(m.get("bestAsk") or min(1.0, price + 0.01))
        liq = float(m.get("liquidityNum") or m.get("liquidity") or 0.0)
        vol = float(m.get("volume24hr") or m.get("volume24hrClob") or 0.0)

        return Market(
            id=str(m.get("id") or m.get("conditionId") or token_id),
            question=str(m.get("question") or m.get("slug") or "¿?")[:140],
            token_id=str(token_id),
            price=price,
            best_bid=bid,
            best_ask=ask,
            liquidez=liq,
            volumen_24h=vol,
        )


# --------------------------------------------------------------------------- #
# Feed sintético (offline / pruebas)
# --------------------------------------------------------------------------- #
class SyntheticDataClient:
    """Genera mercados con precios que evolucionan por caminata aleatoria."""

    def __init__(self, n_mercados: int = 40, seed: int = 42):
        self.rng = random.Random(seed)
        self._mercados: Dict[str, Market] = {}
        for i in range(n_mercados):
            p = round(self.rng.uniform(0.1, 0.9), 3)
            tok = f"SYNTH-{i:03d}"
            self._mercados[tok] = Market(
                id=f"m{i:03d}",
                question=f"Mercado sintético #{i} — ¿ocurrirá el evento {i}?",
                token_id=tok,
                price=p,
                best_bid=round(max(0.0, p - 0.01), 3),
                best_ask=round(min(1.0, p + 0.01), 3),
                liquidez=round(self.rng.uniform(500, 50000), 2),
                volumen_24h=round(self.rng.uniform(1000, 200000), 2),
                historial=[p],
            )

    def get_markets(self, limite: int = 200) -> List[Market]:
        salida: List[Market] = []
        for mk in self._mercados.values():
            # caminata aleatoria con reversión suave a 0.5 y algún shock
            drift = (0.5 - mk.price) * 0.02
            shock = self.rng.gauss(0, 0.02)
            if self.rng.random() < 0.03:            # evento sorpresa ocasional
                shock += self.rng.choice([-1, 1]) * self.rng.uniform(0.05, 0.15)
            p = min(0.99, max(0.01, mk.price + drift + shock))
            mk.price = round(p, 4)
            half = round(self.rng.uniform(0.005, 0.03), 4)
            mk.best_bid = round(max(0.0, p - half), 4)
            mk.best_ask = round(min(1.0, p + half), 4)
            mk.liquidez = round(max(100.0, mk.liquidez * self.rng.uniform(0.9, 1.1)), 2)
            mk.volumen_24h = round(max(100.0, mk.volumen_24h * self.rng.uniform(0.9, 1.15)), 2)
            mk.historial.append(mk.price)
            del mk.historial[:-256]
            salida.append(mk)
        return salida[:limite]


def crear_cliente(cfg) -> object:
    """Fábrica: online si hay red y no está forzado offline, si no sintético."""
    if cfg.offline:
        return SyntheticDataClient()
    if requests is None:
        print("[cliente] 'requests' no disponible -> feed sintético")
        return SyntheticDataClient()
    cliente = PolymarketDataClient(cfg.gamma_url, cfg.clob_url)
    # Prueba de conectividad: si falla, caemos a sintético con aviso claro.
    try:
        cliente._get(f"{cliente.gamma_url}/markets", params={"limit": 1})
        return cliente
    except Exception as e:
        print(f"[cliente] Sin acceso a Polymarket ({e}). Usando feed sintético offline.")
        return SyntheticDataClient()
