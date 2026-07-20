"""Gestion de riesgo: los 'escudos' del agente.

Estos controles NO garantizan ganancias. Sirven para limitar cuanto puedes
perder y evitar errores de ejecucion. Un agente sin estos controles es una
forma rapida de perder todo el capital.
"""
from .config import Config
from . import db


class RiskManager:
    def __init__(self, client):
        self.client = client

    def saldo_disponible(self):
        return self.client.get_balance()

    def puede_operar(self):
        """Devuelve (True, '') si se puede abrir una operacion, o (False, motivo)."""
        saldo = self.saldo_disponible()

        # 1) Balance check: si no alcanza para una posicion, pausar.
        if saldo < Config.MIN_BALANCE_USDC:
            return False, f"Saldo {saldo:.2f} < minimo {Config.MIN_BALANCE_USDC:.2f} USDC. Pausado."

        # 2) Tope de operaciones diarias.
        try:
            hechas = db.contar_operaciones_hoy()
        except Exception as e:
            return False, f"No se pudo consultar la BD: {e}"
        if hechas >= Config.MAX_TRADES_PER_DAY:
            return False, f"Alcanzado el tope de {Config.MAX_TRADES_PER_DAY} operaciones hoy."

        return True, ""

    def tamano_posicion(self):
        """Nunca compromete mas del tamano configurado ni mas del saldo."""
        return min(Config.POSITION_SIZE_USDC, self.saldo_disponible())
