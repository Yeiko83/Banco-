"""Valida proyecto_actual/guion.json sin generar nada. Sale con código 1 si hay problemas."""
import sys

from comun import cargar_guion, validar_guion

errores = validar_guion(cargar_guion())
if errores:
    print("guion.json tiene problemas:")
    for e in errores:
        print(" -", e)
    sys.exit(1)
print("guion.json válido")
