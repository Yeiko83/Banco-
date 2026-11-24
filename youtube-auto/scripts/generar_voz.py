"""FASE 2: convierte narracion_completa en proyecto_actual/voz.mp3 con Edge-TTS (gratis)."""
import asyncio
import sys

import edge_tts
from mutagen.mp3 import MP3

from comun import PROYECTO, cargar_guion, env

SALIDA = PROYECTO / "voz.mp3"


async def sintetizar(texto: str, voz: str, velocidad: str) -> None:
    await edge_tts.Communicate(texto, voz, rate=velocidad).save(str(SALIDA))


def main() -> None:
    guion = cargar_guion()
    texto = guion["narracion_completa"].strip()
    voz = env("TTS_VOICE", "es-CO-GonzaloNeural")
    velocidad = env("TTS_RATE", "+5%")
    print(f"Voz: {voz} | velocidad: {velocidad} | palabras: {len(texto.split())}")

    for intento in range(1, 4):
        try:
            asyncio.run(sintetizar(texto, voz, velocidad))
            break
        except Exception as e:  # errores de red de Edge-TTS son frecuentes
            print(f"Intento {intento} falló: {e}")
            if intento == 3:
                sys.exit("ERROR: no se pudo generar la voz.")

    duracion = MP3(SALIDA).info.length
    (PROYECTO / "duracion.txt").write_text(f"{duracion:.3f}", encoding="utf-8")
    print(f"OK voz.mp3 generada. Duración: {duracion:.2f} segundos")


if __name__ == "__main__":
    main()
