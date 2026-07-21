"""PolyPhoenix — agente de trading para Polymarket (modo paper por defecto)."""

__version__ = "1.0.0"

from .config import Config, cargar_config

__all__ = ["Config", "cargar_config", "__version__"]
