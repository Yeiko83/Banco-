"""Cliente de Polymarket.

En modo LIVE usa py-clob-client (API oficial CLOB) para leer mercados y
enviar ordenes reales. En modo SIM usa un feed de precios simulado, asi el
agente corre completo SIN conexion ni credenciales y sin arriesgar dinero.
"""
import random
import time
from .config import Config


class SimClient:
    """Feed simulado: genera mercados y precios ficticios pero plausibles."""

    def __init__(self):
        self._balance = Config.CAPITAL_USDC
        self._t = 0

    def get_balance(self):
        return self._balance

    def get_markets(self, limit=20):
        mercados = []
        for i in range(limit):
            yes = round(random.uniform(0.30, 0.70), 3)
            # A veces creamos una pequena ineficiencia (YES+NO < 1) para probar la logica.
            no = round(1 - yes - random.uniform(-0.02, 0.02), 3)
            mercados.append({
                "market": f"Mercado simulado #{i+1}",
                "token_yes": f"SIM-YES-{i+1}",
                "token_no": f"SIM-NO-{i+1}",
                "best_ask_yes": yes,
                "best_ask_no": no,
                "liquidity": random.uniform(500, 5000),
            })
        # Mas liquidez primero (el plan pide priorizar liquidez).
        mercados.sort(key=lambda m: m["liquidity"], reverse=True)
        return mercados

    def get_price(self, token_id):
        """Precio actual simulado con leve deriva aleatoria."""
        self._t += 1
        base = 0.5 + 0.1 * random.uniform(-1, 1)
        return round(min(0.99, max(0.01, base)), 3)

    def place_order(self, token_id, side, price, size_usdc):
        # En SIM no se envia nada real; se descuenta/repone el saldo ficticio.
        if side == "BUY":
            self._balance -= size_usdc
        else:
            self._balance += size_usdc
        return {"ok": True, "simulated": True, "token": token_id,
                "side": side, "price": price, "size": size_usdc}


class LiveClient:
    """Envuelve py-clob-client. Solo se instancia en modo LIVE."""

    def __init__(self):
        from py_clob_client.client import ClobClient
        self.client = ClobClient(
            host=Config.POLY_CLOB_HOST,
            key=Config.POLY_PRIVATE_KEY,
            chain_id=Config.POLY_CHAIN_ID,
        )
        # Deriva las credenciales de API a partir de la clave privada.
        self.client.set_api_creds(self.client.create_or_derive_api_creds())

    def get_balance(self):
        # La lectura de saldo USDC depende de tu integracion on-chain.
        # Devuelve el balance colateral disponible en la CLOB.
        try:
            bal = self.client.get_balance_allowance()
            return float(bal.get("balance", 0))
        except Exception:
            return 0.0

    def get_markets(self, limit=20):
        resp = self.client.get_markets()
        data = resp.get("data", resp) if isinstance(resp, dict) else resp
        mercados = []
        for m in data[:limit]:
            tokens = m.get("tokens", [])
            if len(tokens) < 2:
                continue
            mercados.append({
                "market": m.get("question", m.get("condition_id", "?")),
                "token_yes": tokens[0].get("token_id"),
                "token_no": tokens[1].get("token_id"),
                "best_ask_yes": float(tokens[0].get("price", 0) or 0),
                "best_ask_no": float(tokens[1].get("price", 0) or 0),
                "liquidity": float(m.get("liquidity", 0) or 0),
            })
        mercados.sort(key=lambda x: x["liquidity"], reverse=True)
        return mercados

    def get_price(self, token_id):
        resp = self.client.get_price(token_id=token_id, side="SELL")
        return float(resp.get("price", 0) or 0)

    def place_order(self, token_id, side, price, size_usdc):
        from py_clob_client.clob_types import OrderArgs
        from py_clob_client.order_builder.constants import BUY, SELL
        qty = round(size_usdc / price, 2) if price > 0 else 0
        order = self.client.create_order(OrderArgs(
            token_id=token_id,
            price=price,
            size=qty,
            side=BUY if side == "BUY" else SELL,
        ))
        return self.client.post_order(order)


def make_client():
    if Config.is_live():
        return LiveClient()
    return SimClient()
