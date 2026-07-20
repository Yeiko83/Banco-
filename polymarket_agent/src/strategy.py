"""Logica de decision: cuando entrar y cuando salir.

IMPORTANTE (honestidad): el 'edge' del 1.2% no es dinero gratis. En mercados
reales esas diferencias se cierran en segundos y compites contra bots mas
rapidos y con mas capital. Esta estrategia es un punto de partida razonable
y auditable, NO una maquina de ganar. Validala en modo SIM antes de arriesgar.
"""
from .config import Config


def buscar_entrada(mercados):
    """Devuelve el mejor mercado para entrar, o None.

    Criterio: preferimos el lado (YES/NO) mas barato cuyo 'edge' respecto al
    precio justo (0.5 de referencia, o desbalance YES+NO) supere MIN_EDGE.
    """
    mejor = None
    mejor_edge = Config.MIN_EDGE

    for m in mercados:
        yes = m["best_ask_yes"]
        no = m["best_ask_no"]
        if yes <= 0 or no <= 0:
            continue

        # Ineficiencia clasica: si comprar YES+NO cuesta < 1, hay margen.
        suma = yes + no
        edge = (1.0 - suma) if suma < 1.0 else 0.0

        # Restamos la comision estimada de ambos lados para ser realistas.
        edge_neto = edge - 2 * Config.FEE_ESTIMATE

        if edge_neto > mejor_edge:
            mejor_edge = edge_neto
            lado_barato = "YES" if yes <= no else "NO"
            token = m["token_yes"] if lado_barato == "YES" else m["token_no"]
            precio = yes if lado_barato == "YES" else no
            mejor = {
                "market": m["market"],
                "token_id": token,
                "precio_compra": precio,
                "edge": round(edge_neto, 4),
            }

    return mejor


def decidir_cierre(precio_compra, precio_actual, minutos_abierta):
    """Devuelve (cerrar: bool, motivo: str)."""
    if precio_compra <= 0:
        return True, "STOP_LOSS"

    cambio = (precio_actual - precio_compra) / precio_compra

    if cambio >= Config.TAKE_PROFIT:
        return True, "TAKE_PROFIT"
    if cambio <= -Config.STOP_LOSS:
        return True, "STOP_LOSS"
    if minutos_abierta >= Config.POSITION_TIMEOUT_MIN:
        return True, "TIMEOUT"
    return False, ""
