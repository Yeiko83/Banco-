"""Vacía proyecto_actual/ para empezar un video nuevo (no toca historial ni token)."""
import shutil

from comun import PROYECTO

shutil.rmtree(PROYECTO, ignore_errors=True)
PROYECTO.mkdir()
print("OK proyecto_actual/ vacío")
