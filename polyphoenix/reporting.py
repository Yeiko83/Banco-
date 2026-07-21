"""
Motor de reportes.

Escribe automáticamente 4 reportes en CSV (siempre) y, opcionalmente, los
sube a Google Sheets si hay credenciales configuradas:

  1. resumen_diario.csv   -> métricas del día
  2. operaciones.csv      -> cada trade cerrado
  3. metricas.csv         -> foto por ciclo (equity, exposición, etc.)
  4. alertas.csv          -> disparos de los escudos de seguridad

El diseño replica las 4 hojas que pediste para Google Sheets.
"""
from __future__ import annotations

import csv
import os
from datetime import datetime, timezone
from typing import List


CABECERAS = {
    "resumen_diario.csv": [
        "Fecha", "Capital Inicial", "Capital Final", "Utilidad Neta",
        "% Retorno", "N Operaciones", "Win Rate %", "Sharpe",
        "Max Drawdown %", "Factor Beneficio",
    ],
    "operaciones.csv": [
        "Timestamp", "Mercado", "Tipo", "Precio Entrada", "Precio Salida",
        "Shares", "PnL", "% Retorno", "Estrategia",
        "Motivo Entrada", "Motivo Salida", "Confianza",
    ],
    "metricas.csv": [
        "Timestamp", "Equity", "Cash", "Exposicion Total",
        "N Posiciones", "Volatilidad Portafolio", "Sharpe Movil",
    ],
    "alertas.csv": [
        "Timestamp", "Escudo", "Tipo Alerta", "Descripcion", "Accion",
    ],
}


def _ahora() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")


class Reporter:
    def __init__(self, cfg):
        self.cfg = cfg
        self.dir = cfg.reportes_dir
        os.makedirs(self.dir, exist_ok=True)
        for nombre, cab in CABECERAS.items():
            ruta = os.path.join(self.dir, nombre)
            if not os.path.exists(ruta):
                self._escribir(nombre, [cab])
        self.sheets = self._init_sheets()

    # ---- CSV ------------------------------------------------------------ #
    def _escribir(self, nombre: str, filas: List[list]) -> None:
        ruta = os.path.join(self.dir, nombre)
        with open(ruta, "a", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerows(filas)

    def registrar_operacion(self, trade) -> None:
        fila = [
            datetime.fromtimestamp(trade.ts).strftime("%Y-%m-%d %H:%M:%S"),
            trade.market_id, trade.side, trade.precio_entrada, trade.precio_salida,
            trade.shares, trade.pnl, trade.retorno_pct, trade.estrategia,
            trade.motivo_entrada, trade.motivo_salida, trade.confianza,
        ]
        self._escribir("operaciones.csv", [fila])
        self._sheets_append("OPERACIONES", fila)

    def registrar_metricas(self, pf, precios) -> None:
        exp = sum(p.costo for p in pf.posiciones.values())
        fila = [
            _ahora(), round(pf.valor_mercado(precios), 4), round(pf.cash, 4),
            round(exp, 4), len(pf.posiciones),
            round(pf.volatilidad_portafolio(), 4), round(pf.sharpe(), 4),
        ]
        self._escribir("metricas.csv", [fila])
        self._sheets_append("METRICAS", fila)

    def registrar_alertas(self, alertas) -> None:
        filas = [[_ahora(), a.escudo, a.nombre, a.descripcion, a.accion] for a in alertas]
        if filas:
            self._escribir("alertas.csv", filas)
            for f in filas:
                self._sheets_append("ALERTAS", f)

    def registrar_resumen_diario(self, pf, precios) -> list:
        cap_ini = self.cfg.capital_inicial
        cap_fin = pf.valor_mercado(precios)
        util = cap_fin - cap_ini
        fila = [
            datetime.now().strftime("%Y-%m-%d"),
            round(cap_ini, 2), round(cap_fin, 2), round(util, 2),
            round(100 * util / cap_ini, 3) if cap_ini else 0,
            len(pf.historial), round(pf.win_rate(), 2), round(pf.sharpe(), 3),
            round(pf.drawdown_maximo(), 2), round(pf.factor_beneficio(), 3),
        ]
        self._escribir("resumen_diario.csv", [fila])
        self._sheets_append("RESUMEN_DIARIO", fila)
        return fila

    # ---- Google Sheets (opcional) -------------------------------------- #
    def _init_sheets(self):
        if not self.cfg.google_sheets_id:
            return None
        try:
            from google.oauth2.service_account import Credentials
            from googleapiclient.discovery import build
            scopes = ["https://www.googleapis.com/auth/spreadsheets"]
            creds = Credentials.from_service_account_file(self.cfg.google_creds, scopes=scopes)
            svc = build("sheets", "v4", credentials=creds, cache_discovery=False)
            print("[reportes] Google Sheets conectado.")
            return svc
        except Exception as e:
            print(f"[reportes] Google Sheets no disponible ({e}). Solo CSV.")
            return None

    def _sheets_append(self, hoja: str, fila: list) -> None:
        if not self.sheets:
            return
        try:
            self.sheets.spreadsheets().values().append(
                spreadsheetId=self.cfg.google_sheets_id,
                range=f"{hoja}!A:Z",
                valueInputOption="USER_ENTERED",
                body={"values": [fila]},
            ).execute()
        except Exception as e:
            print(f"[reportes] Error subiendo a Sheets: {e}")
