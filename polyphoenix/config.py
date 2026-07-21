"""
Configuración central de PolyPhoenix.

Todos los parámetros se pueden sobreescribir con variables de entorno.
Lee un archivo .env si existe (sin dependencias externas).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field, asdict


def _load_dotenv(path: str = ".env") -> None:
    """Carga un .env simple a os.environ (no sobreescribe lo ya definido)."""
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key, val = key.strip(), val.strip().strip('"').strip("'")
            os.environ.setdefault(key, val)


def _f(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _i(name: str, default: int) -> int:
    try:
        return int(float(os.environ.get(name, default)))
    except (TypeError, ValueError):
        return default


def _b(name: str, default: bool) -> bool:
    v = os.environ.get(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "y", "si", "sí", "on")


@dataclass
class Config:
    # --- Modo de operación -------------------------------------------------
    # "paper"  -> simulación con dinero ficticio (por defecto, seguro)
    # "live"   -> dinero real. Requiere credenciales y activación explícita.
    mode: str = field(default_factory=lambda: os.environ.get("MODE", "paper"))
    offline: bool = field(default_factory=lambda: _b("OFFLINE", False))

    # --- Capital -----------------------------------------------------------
    # Capital en la moneda que uses. Polymarket liquida en USDC (USD).
    # 200.000 COP ≈ 50 USD. Ajusta CAPITAL a lo que realmente vayas a usar.
    capital_inicial: float = field(default_factory=lambda: _f("CAPITAL", 50.0))
    moneda: str = field(default_factory=lambda: os.environ.get("MONEDA", "USD"))

    # --- Estrategia --------------------------------------------------------
    # Umbral de score (0-100) para entrar. Más bajo = más agresivo.
    umbral_entrada: float = field(default_factory=lambda: _f("UMBRAL_ENTRADA", 60.0))
    # Ventana de precios (nº de muestras) para calcular momentum/volatilidad.
    ventana: int = field(default_factory=lambda: _i("VENTANA", 12))
    # Máximo de oportunidades ejecutadas por ciclo.
    top_n: int = field(default_factory=lambda: _i("TOP_N", 3))

    # --- Gestión de riesgo (los 15 escudos) -------------------------------
    stop_loss_pct: float = field(default_factory=lambda: _f("STOP_LOSS", 0.08))
    take_profit_pct: float = field(default_factory=lambda: _f("TAKE_PROFIT", 0.15))
    tamano_posicion_pct: float = field(default_factory=lambda: _f("TAMANO_POSICION", 0.10))
    max_posicion_pct: float = field(default_factory=lambda: _f("MAX_POSICION_PCT", 0.30))
    max_por_mercado_pct: float = field(default_factory=lambda: _f("MAX_POR_MERCADO_PCT", 0.60))
    drawdown_diario_max: float = field(default_factory=lambda: _f("DRAWDOWN_DIARIO_MAX", 0.08))
    max_posiciones: int = field(default_factory=lambda: _i("MAX_POSICIONES", 8))
    max_ops_por_hora: int = field(default_factory=lambda: _i("MAX_OPS_POR_HORA", 12))
    spread_max_pct: float = field(default_factory=lambda: _f("SPREAD_MAX_PCT", 0.05))
    liquidez_min_mult: float = field(default_factory=lambda: _f("LIQUIDEZ_MIN_MULT", 5.0))
    ratio_rr_min: float = field(default_factory=lambda: _f("RATIO_RR_MIN", 1.5))
    correlacion_max: float = field(default_factory=lambda: _f("CORRELACION_MAX", 0.7))
    atr_mult: float = field(default_factory=lambda: _f("ATR_MULT", 2.5))
    pausa_drawdown_min: int = field(default_factory=lambda: _i("PAUSA_DRAWDOWN_MIN", 120))

    # --- Ciclo -------------------------------------------------------------
    intervalo_seg: int = field(default_factory=lambda: _i("INTERVALO_SEG", 60))
    limite_mercados: int = field(default_factory=lambda: _i("LIMITE_MERCADOS", 200))

    # --- Reportes ----------------------------------------------------------
    reportes_dir: str = field(default_factory=lambda: os.environ.get("REPORTES_DIR", "reportes"))
    google_sheets_id: str = field(default_factory=lambda: os.environ.get("GOOGLE_SHEETS_ID", ""))
    google_creds: str = field(default_factory=lambda: os.environ.get("GOOGLE_CREDS", "credentials.json"))

    # --- API ---------------------------------------------------------------
    gamma_url: str = field(default_factory=lambda: os.environ.get("GAMMA_URL", "https://gamma-api.polymarket.com"))
    clob_url: str = field(default_factory=lambda: os.environ.get("CLOB_URL", "https://clob.polymarket.com"))

    def es_live(self) -> bool:
        return self.mode.strip().lower() == "live"

    def resumen(self) -> str:
        d = asdict(self)
        lineas = [f"  {k:24s}: {v}" for k, v in d.items()]
        return "Configuración PolyPhoenix:\n" + "\n".join(lineas)


def cargar_config() -> Config:
    _load_dotenv()
    return Config()
