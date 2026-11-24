"""FASE 3: descarga una imagen por escena + miniatura desde Pollinations.ai (gratis)."""
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

import requests

from comun import PROYECTO, cargar_guion, env, ruta_escena

URL = "https://image.pollinations.ai/prompt/{prompt}?width={w}&height={h}&nologo=true&seed={seed}"
ESTILO = ", cinematic photorealistic, dramatic lighting, 8k, highly detailed, no text, no letters, no watermark"
MIN_BYTES = 15 * 1024
INTENTOS = 6
# El acceso anónimo de Pollinations admite ~1 petición cada 15 s; más rápido devuelve 429.
PAUSA = float(env("POLLINATIONS_PAUSA", "16"))
TOKEN = env("POLLINATIONS_TOKEN", "")  # opcional: clave gratuita de pollinations.ai


def es_imagen(datos: bytes) -> bool:
    return datos[:3] == b"\xff\xd8\xff" or datos[:8] == b"\x89PNG\r\n\x1a\n" or datos[8:12] == b"WEBP"


def descargar(prompt: str, destino: Path, w: int, h: int, seed: int) -> bool:
    for intento in range(INTENTOS):
        s = seed + intento * 1000  # cambia el seed en cada reintento
        url = URL.format(prompt=urllib.parse.quote(prompt + ESTILO, safe=""), w=w, h=h, seed=s)
        try:
            cabeceras = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}
            r = requests.get(url, headers=cabeceras, timeout=180)
            if r.status_code == 200 and len(r.content) > MIN_BYTES and es_imagen(r.content):
                destino.write_bytes(r.content)
                print(f"  OK {destino.name} ({len(r.content) // 1024} KB, seed {s})")
                time.sleep(PAUSA)
                return True
            print(f"  {destino.name}: respuesta inválida (HTTP {r.status_code}, {len(r.content)} bytes)")
            if r.status_code in (402, 429):
                # Límite del acceso gratuito: esperar más antes de reintentar.
                time.sleep(PAUSA * 2)
        except requests.RequestException as e:
            print(f"  {destino.name}: error de red: {e}")
        time.sleep(max(3, PAUSA))
    return False


def respaldo(destino: Path, w: int, h: int, n: int) -> None:
    """Si Pollinations falla del todo, crea un fondo degradado para no romper el video."""
    colores = ["0x1b263b", "0x3a0ca3", "0x0b3d2e", "0x5a189a", "0x7f1d1d"]
    c = colores[n % len(colores)]
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
         "-i", f"gradients=s={w}x{h}:c0={c}:c1=black:duration=1",
         "-frames:v", "1", str(destino)],
        check=True,
    )
    print(f"  AVISO: {destino.name} es un fondo de respaldo (Pollinations no respondió)")


def main() -> None:
    guion = cargar_guion()
    escenas = guion["escenas"]
    fallidas = 0
    print(f"Descargando {len(escenas)} imágenes 1920x1080...")
    for e in escenas:
        destino = ruta_escena(e["id"])
        if destino.exists() and destino.stat().st_size > MIN_BYTES:
            print(f"  ya existe {destino.name}, se reutiliza")
            continue
        if not descargar(e["prompt_imagen"], destino, 1920, 1080, e["id"]):
            fallidas += 1
            respaldo(destino, 1920, 1080, e["id"])

    print("Descargando miniatura 1280x720...")
    prompt_mini = guion.get("prompt_miniatura") or (
        f"Eye-catching YouTube thumbnail background about: {guion['titulo']}. "
        "Extreme visual contrast, vivid saturated colors, single bold focal subject"
    )
    mini = PROYECTO / "miniatura.jpg"
    if not descargar(prompt_mini, mini, 1280, 720, 777):
        fallidas += 1
        respaldo(mini, 1280, 720, 0)

    if fallidas:
        print(f"AVISO: {fallidas} imagen(es) usan fondo de respaldo. Puedes borrarlas y reejecutar.")
    # La miniatura de YouTube debe pesar < 2 MB.
    if mini.stat().st_size > 2 * 1024 * 1024:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mini), "-q:v", "5",
                        str(mini.with_name("miniatura_tmp.jpg"))], check=True)
        mini.with_name("miniatura_tmp.jpg").replace(mini)
    print("OK imágenes listas")


if __name__ == "__main__":
    sys.exit(main())
