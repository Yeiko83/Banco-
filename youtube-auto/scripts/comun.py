"""Utilidades compartidas por todos los scripts del pipeline."""
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent
PROYECTO = RAIZ / "proyecto_actual"
GUION = PROYECTO / "guion.json"

load_dotenv(RAIZ / ".env")

# Evita errores de tildes/ñ en consolas antiguas de Windows.
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


def env(nombre: str, defecto: str) -> str:
    valor = os.getenv(nombre, "").strip().strip('"').strip("'")
    return valor or defecto


def cargar_guion() -> dict:
    if not GUION.exists():
        sys.exit(f"ERROR: no existe {GUION}. Primero hay que crear el guion (Fase 1).")
    with open(GUION, encoding="utf-8") as f:
        return json.load(f)


def validar_guion(g: dict) -> list[str]:
    """Devuelve la lista de problemas encontrados (vacía = guion válido)."""
    errores = []
    for clave in ("titulo", "descripcion", "tags", "narracion_completa", "escenas"):
        if clave not in g:
            errores.append(f"falta la clave '{clave}'")
    if errores:
        return errores
    if not 1 <= len(g["titulo"]) <= 100:
        errores.append("titulo debe tener entre 1 y 100 caracteres (YouTube corta en 100)")
    if any(c in g["titulo"] for c in "<>"):
        errores.append("titulo no puede contener < ni > (YouTube lo rechaza)")
    if len(g["descripcion"].encode("utf-8")) > 5000:
        errores.append("descripcion supera 5000 bytes")
    if any(c in g["descripcion"] for c in "<>"):
        errores.append("descripcion no puede contener < ni >")
    hashtags = [w for w in g["descripcion"].split() if w.startswith("#")]
    if len(hashtags) > 15:
        errores.append(f"descripcion tiene {len(hashtags)} hashtags; máximo 15 (si no, YouTube los ignora todos)")
    if not isinstance(g["tags"], list) or not g["tags"]:
        errores.append("tags debe ser una lista no vacía")
    elif sum(len(t) + 2 for t in g["tags"]) > 500:
        errores.append("tags suman más de 500 caracteres (límite de YouTube)")
    if not isinstance(g["escenas"], list) or not g["escenas"]:
        errores.append("escenas debe ser una lista no vacía")
    else:
        for i, e in enumerate(g["escenas"], 1):
            if e.get("id") != i:
                errores.append(f"escena #{i}: id debe ser {i}")
            if not str(e.get("prompt_imagen", "")).strip():
                errores.append(f"escena #{i}: falta prompt_imagen")
    return errores


def ruta_escena(i: int) -> Path:
    return PROYECTO / f"escena_{i:02d}.jpg"
