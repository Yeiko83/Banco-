"""
PolyPhoenix — agente de trading para Polymarket (modo paper por defecto).

Orquesta el ciclo 24/7:
  1. Escanea TODOS los mercados disponibles.
  2. Genera señales (strategy).
  3. Filtra cada entrada con los 15 escudos (risk).
  4. Ejecuta en simulación (o real si mode=live y está implementada la firma).
  5. Gestiona posiciones abiertas (stops / take-profit / trailing).
  6. Escribe reportes automáticos (CSV + Google Sheets opcional).

Ejecución:
    python -m polyphoenix.agent            # loop infinito (Ctrl+C para parar)
    python -m polyphoenix.agent --cycles 5 # nº fijo de ciclos (pruebas)
"""
from __future__ import annotations

import argparse
import time
from datetime import datetime

from .config import cargar_config
from .polymarket_client import crear_cliente
from .portfolio import Portfolio
from .reporting import Reporter
from .risk import RiskManager
from .strategy import evaluar_todos


class PolyPhoenixAgent:
    def __init__(self, cfg=None):
        self.cfg = cfg or cargar_config()
        self.cliente = crear_cliente(self.cfg)
        self.pf = Portfolio(self.cfg)
        self.rm = RiskManager(self.cfg)
        self.rep = Reporter(self.cfg)
        self._ciclo = 0
        self._ultimo_dia = datetime.now().date()
        self._ciclos_sin_datos = 0

        modo = "LIVE (dinero real)" if self.cfg.es_live() else "PAPER (simulación)"
        print("=" * 64)
        print(f"  PolyPhoenix iniciado — modo: {modo}")
        print(f"  Capital: {self.cfg.capital_inicial:,.2f} {self.cfg.moneda}")
        print(f"  Cliente: {type(self.cliente).__name__}")
        print("=" * 64)
        if self.cfg.es_live():
            print("⚠️  MODO LIVE: la ejecución real de órdenes NO está implementada")
            print("    en este código (requiere firma EIP-712 y credenciales CLOB).")
            print("    Se opera en simulación hasta que la integres conscientemente.")

    # ------------------------------------------------------------------ #
    def _precios(self, mercados) -> dict:
        return {m.token_id: m.price for m in mercados}

    def ciclo(self) -> None:
        self._ciclo += 1
        mercados = self.cliente.get_markets(self.cfg.limite_mercados)

        # ESCUDO 12: timeout / diagnóstico si no llegan datos.
        if not mercados:
            self._ciclos_sin_datos += 1
            print(f"[ciclo {self._ciclo}] Sin datos de mercado ({self._ciclos_sin_datos}).")
            if self._ciclos_sin_datos >= 3:
                print("[escudo 12] Ejecutando diagnóstico: reconstruyo cliente.")
                self.cliente = crear_cliente(self.cfg)
                self._ciclos_sin_datos = 0
            return
        self._ciclos_sin_datos = 0

        precios = self._precios(mercados)

        # 1) Gestionar posiciones abiertas (stops, TP, trailing = escudo 1)
        for trade, motivo in self.pf.marcar(precios):
            self.rep.registrar_operacion(trade)
            self.rm.registrar_resultado(trade.pnl, self.pf.valor_mercado(precios))
            print(f"  ⟳ cierre {trade.market_id} {motivo} PnL={trade.pnl:+.4f}")

        # 2) Cambio de día -> resumen diario + reset de límites
        hoy = datetime.now().date()
        if hoy != self._ultimo_dia:
            fila = self.rep.registrar_resumen_diario(self.pf, precios)
            print(f"  📊 Resumen diario: retorno {fila[4]}% | {fila[5]} ops | WR {fila[6]}%")
            self.rm.nuevo_dia(self.pf.valor_mercado(precios))
            self._ultimo_dia = hoy

        # 3) Generar y filtrar señales
        señales = evaluar_todos(mercados, self.cfg)
        by_id = {m.id: m for m in mercados}
        ejecutadas = 0
        for sig in señales:
            if ejecutadas >= self.cfg.top_n:
                break
            mk = by_id.get(sig.market_id)
            if not mk:
                continue
            permitido, alertas = self.rm.evaluar(sig, mk, self.pf, mercados)
            self.rep.registrar_alertas(alertas)   # escudo 15: auditoría
            if not permitido:
                continue
            tamano = self.pf.tamano_objetivo(self.cfg, self.rm.modo_conservador)
            pos = self.pf.abrir(sig, tamano)
            if pos:
                self.rm.registrar_operacion()
                ejecutadas += 1
                print(f"  ▸ ABRE {sig.side} {mk.question[:48]!r} "
                      f"score={sig.score} tam=${tamano:,.2f} [{sig.estrategia}]")

        # 4) Métricas por ciclo
        self.rep.registrar_metricas(self.pf, precios)
        eq = self.pf.valor_mercado(precios)
        ret = 100 * (eq - self.cfg.capital_inicial) / self.cfg.capital_inicial
        print(f"[ciclo {self._ciclo}] equity={eq:,.2f} ({ret:+.2f}%) "
              f"| pos={len(self.pf.posiciones)} | trades={len(self.pf.historial)} "
              f"| conservador={self.rm.modo_conservador}")

    def run(self, cycles: int | None = None) -> None:
        try:
            n = 0
            while cycles is None or n < cycles:
                self.ciclo()
                n += 1
                if cycles is None or n < cycles:
                    time.sleep(self.cfg.intervalo_seg if cycles is None else 0)
        except KeyboardInterrupt:
            print("\n[agente] Detenido por el usuario. Escribiendo resumen final…")
        finally:
            precios = self._precios(self.cliente.get_markets(self.cfg.limite_mercados) or [])
            fila = self.rep.registrar_resumen_diario(self.pf, precios)
            print(f"[agente] Resumen final: capital {fila[2]} | retorno {fila[4]}% | "
                  f"{fila[5]} ops | WR {fila[6]}% | maxDD {fila[8]}%")


def main():
    ap = argparse.ArgumentParser(description="PolyPhoenix — agente Polymarket (paper)")
    ap.add_argument("--cycles", type=int, default=None,
                    help="Número de ciclos a ejecutar (por defecto: infinito)")
    args = ap.parse_args()
    PolyPhoenixAgent().run(cycles=args.cycles)


if __name__ == "__main__":
    main()
