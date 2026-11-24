"""FASE 4: arma video_final.mp4 (imágenes con efecto Ken Burns + voz) usando FFmpeg."""
import shutil
import subprocess
import sys

from mutagen.mp3 import MP3

from comun import PROYECTO, cargar_guion, ruta_escena

FPS = 30
ZOOM_MAX = 1.15
TMP = PROYECTO / "tmp_clips"


def ffmpeg(*args: str) -> None:
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *args]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("Comando:", " ".join(cmd))
        print(r.stderr)
        sys.exit("ERROR: FFmpeg falló (ver mensaje arriba)")


def clip(imagen, salida, frames: int, acercar: bool) -> None:
    paso = (ZOOM_MAX - 1) / max(frames, 1)
    # Alterna acercamiento / alejamiento para que no todas las escenas se vean igual.
    zoom = f"1+{paso}*on" if acercar else f"{ZOOM_MAX}-{paso}*on"
    filtro = (
        "scale=3840:2160:force_original_aspect_ratio=increase,crop=3840:2160,"
        f"zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        f":d={frames}:s=1920x1080:fps={FPS},format=yuv420p"
    )
    ffmpeg("-i", str(imagen), "-vf", filtro, "-frames:v", str(frames),
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-r", str(FPS), str(salida))


def main() -> None:
    if not shutil.which("ffmpeg"):
        sys.exit("ERROR: ffmpeg no está en el PATH. Instálalo: winget install Gyan.FFmpeg")
    guion = cargar_guion()
    voz = PROYECTO / "voz.mp3"
    duracion = MP3(voz).info.length
    n = len(guion["escenas"])
    total_frames = round(duracion * FPS) + FPS // 2  # medio segundo extra de margen
    base = total_frames // n
    print(f"Audio: {duracion:.2f}s | escenas: {n} | {base / FPS:.2f}s por escena")

    TMP.mkdir(exist_ok=True)
    lista = PROYECTO / "lista_clips.txt"
    lineas = []
    for i, e in enumerate(guion["escenas"]):
        frames = base + (total_frames - base * n if i == n - 1 else 0)
        salida = TMP / f"clip_{e['id']:02d}.mp4"
        clip(ruta_escena(e["id"]), salida, frames, acercar=(i % 2 == 0))
        lineas.append(f"file '{salida.as_posix()}'")
        print(f"  clip {i + 1}/{n} listo")
    lista.write_text("\n".join(lineas) + "\n", encoding="utf-8")

    unido = TMP / "unido.mp4"
    ffmpeg("-f", "concat", "-safe", "0", "-i", str(lista), "-c", "copy", str(unido))
    final = PROYECTO / "video_final.mp4"
    ffmpeg("-i", str(unido), "-i", str(voz), "-map", "0:v", "-map", "1:a",
           "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(final))

    shutil.rmtree(TMP, ignore_errors=True)
    lista.unlink(missing_ok=True)
    print(f"OK video_final.mp4 ({final.stat().st_size / 1_048_576:.1f} MB)")


if __name__ == "__main__":
    main()
