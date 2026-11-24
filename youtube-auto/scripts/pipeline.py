"""Ejecuta las fases 2 a 5 en orden, tras validar proyecto_actual/guion.json.

Uso:
    python scripts/pipeline.py              # voz + imágenes + video + subida
    python scripts/pipeline.py --sin-subir  # todo menos la subida a YouTube
    python scripts/pipeline.py --desde video
"""
import argparse
import subprocess
import sys
from pathlib import Path

from comun import cargar_guion, validar_guion

DIR = Path(__file__).resolve().parent
FASES = [("voz", "generar_voz.py"), ("imagenes", "generar_imagenes.py"),
         ("video", "ensamblar_video.py"), ("subir", "subir_youtube.py")]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--sin-subir", action="store_true")
    p.add_argument("--desde", choices=[f for f, _ in FASES], default="voz")
    a = p.parse_args()

    errores = validar_guion(cargar_guion())
    if errores:
        print("guion.json tiene problemas:")
        for e in errores:
            print(" -", e)
        sys.exit(1)
    print("guion.json válido\n")

    nombres = [f for f, _ in FASES]
    for fase, script in FASES[nombres.index(a.desde):]:
        if fase == "subir" and a.sin_subir:
            break
        print(f"===== FASE: {fase} =====")
        if subprocess.run([sys.executable, str(DIR / script)]).returncode != 0:
            sys.exit(f"\nFalló la fase '{fase}'. Corrige y reanuda con: "
                     f"python scripts/pipeline.py --desde {fase}")
        print()
    print("PIPELINE TERMINADO")


if __name__ == "__main__":
    main()
