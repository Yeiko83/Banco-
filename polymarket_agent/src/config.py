"""Carga y valida la configuracion desde el archivo .env."""
import os
import sys
from dotenv import load_dotenv

load_dotenv()


def _f(key, default):
    return float(os.getenv(key, default))


def _i(key, default):
    return int(os.getenv(key, default))


class Config:
    MODE = os.getenv("MODE", "SIM").upper()
    LIVE_CONFIRM = os.getenv("LIVE_CONFIRM", "")

    CAPITAL_USDC = _f("CAPITAL_USDC", 50)
    POSITION_SIZE_USDC = _f("POSITION_SIZE_USDC", 1.5)
    MIN_BALANCE_USDC = _f("MIN_BALANCE_USDC", 1.5)
    MAX_TRADES_PER_DAY = _i("MAX_TRADES_PER_DAY", 30)
    MIN_EDGE = _f("MIN_EDGE", 0.012)
    POSITION_TIMEOUT_MIN = _i("POSITION_TIMEOUT_MIN", 30)
    TAKE_PROFIT = _f("TAKE_PROFIT", 0.02)
    STOP_LOSS = _f("STOP_LOSS", 0.03)
    FEE_ESTIMATE = _f("FEE_ESTIMATE", 0.0)

    POLY_PRIVATE_KEY = os.getenv("POLY_PRIVATE_KEY", "")
    POLY_CLOB_HOST = os.getenv("POLY_CLOB_HOST", "https://clob.polymarket.com")
    POLY_CHAIN_ID = _i("POLY_CHAIN_ID", 137)

    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = _i("DB_PORT", 3306)
    DB_USER = os.getenv("DB_USER", "")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "polymarket")

    SMTP_HOST = os.getenv("SMTP_HOST", "")
    SMTP_PORT = _i("SMTP_PORT", 465)
    SMTP_USER = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    REPORT_TO = os.getenv("REPORT_TO", "")

    @classmethod
    def is_live(cls):
        return cls.MODE == "LIVE"

    @classmethod
    def guard_live(cls):
        """Bloquea el modo real si no hay confirmacion explicita y credenciales."""
        if not cls.is_live():
            return
        if cls.LIVE_CONFIRM != "SI_ENTIENDO_EL_RIESGO":
            print("[SEGURIDAD] MODE=LIVE pero LIVE_CONFIRM no es 'SI_ENTIENDO_EL_RIESGO'.")
            print("            Se aborta para proteger tu dinero. Revisa tu .env.")
            sys.exit(1)
        if not cls.POLY_PRIVATE_KEY:
            print("[SEGURIDAD] MODE=LIVE sin POLY_PRIVATE_KEY. Se aborta.")
            sys.exit(1)
