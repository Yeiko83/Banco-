"""FASE 5: sube video_final.mp4 + miniatura a YouTube con la API oficial (OAuth2)."""
import json
import os
import socket
import sys
import time
from datetime import date

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from comun import PROYECTO, RAIZ, cargar_guion, env

SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube"]
TOKEN = RAIZ / "token.json"


# En algunas redes (frecuente en Windows) IPv6 no funciona y httplib2 se queda esperando
# hasta dar WinError 10060, aunque el navegador y curl sí conectan. Se prefiere IPv4.
_getaddrinfo_original = socket.getaddrinfo


def _preferir_ipv4(host, *args, **kwargs):
    resultados = _getaddrinfo_original(host, *args, **kwargs)
    ipv4 = [r for r in resultados if r[0] == socket.AF_INET]
    return ipv4 or resultados


if os.getenv("YOUTUBE_PERMITIR_IPV6", "").lower() not in ("1", "true", "si"):
    socket.getaddrinfo = _preferir_ipv4


def credenciales() -> Credentials:
    secretos = RAIZ / env("YOUTUBE_CLIENT_SECRETS_FILE", "client_secrets.json")
    if not secretos.exists():
        sys.exit(f"ERROR: falta {secretos.name}. Descárgalo de Google Cloud Console (Bloque 2).")
    creds = Credentials.from_authorized_user_file(str(TOKEN), SCOPES) if TOKEN.exists() else None
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except RefreshError:
            # Pasa si la app está en modo "Prueba": Google vence el token a los 7 días.
            print("El token venció; se pedirá iniciar sesión de nuevo en el navegador.")
            creds = None
    if not creds or not creds.valid:
        if os.getenv("CI"):
            sys.exit("ERROR: token.json inválido o vencido en el servidor. Genera uno nuevo en tu PC "
                     "y actualiza el secreto YOUTUBE_TOKEN en GitHub.")
        flow = InstalledAppFlow.from_client_secrets_file(str(secretos), SCOPES)
        creds = flow.run_local_server(port=0, prompt="consent")
    TOKEN.write_text(creds.to_json(), encoding="utf-8")
    return creds


def subir(youtube, cuerpo: dict, video) -> str:
    # Trozos de 2 MB: en conexiones lentas o inestables cada trozo termina antes del tiempo límite.
    media = MediaFileUpload(str(video), mimetype="video/mp4", chunksize=2 * 1024 * 1024, resumable=True)
    peticion = youtube.videos().insert(part="snippet,status", body=cuerpo, media_body=media)
    respuesta, errores = None, 0
    while respuesta is None:
        try:
            estado, respuesta = peticion.next_chunk(num_retries=3)
            errores = 0
            if estado:
                print(f"  subiendo... {int(estado.progress() * 100)}%")
        except HttpError as e:
            if e.resp.status not in (500, 502, 503, 504) or errores >= 8:
                raise
            errores += 1
            print(f"  error {e.resp.status} de YouTube, reintento {errores}/8...")
            time.sleep(min(2 ** errores, 60))
        except (OSError, TimeoutError, ConnectionError) as e:
            # WinError 10060/10054, cortes de red, etc. La subida continúa donde iba.
            if errores >= 8:
                raise
            errores += 1
            print(f"  problema de conexión ({e}), reintento {errores}/8...")
            time.sleep(min(2 ** errores, 60))
    return respuesta["id"]


def main() -> None:
    guion = cargar_guion()
    video = PROYECTO / "video_final.mp4"
    if not video.exists():
        sys.exit("ERROR: no existe video_final.mp4 (ejecuta la Fase 4).")

    socket.setdefaulttimeout(300)  # 5 min por petición en vez de cortar enseguida
    youtube = build("youtube", "v3", credentials=credenciales(), num_retries=3)
    cuerpo = {
        "snippet": {
            "title": guion["titulo"][:100],
            "description": guion["descripcion"],
            "tags": guion["tags"],
            "categoryId": env("YOUTUBE_CATEGORY_ID", "27"),
            "defaultLanguage": "es",
            "defaultAudioLanguage": "es",
        },
        "status": {
            "privacyStatus": env("YOUTUBE_PRIVACY", "private"),
            "selfDeclaredMadeForKids": False,
            # Las imágenes son generadas por IA: YouTube pide declararlo.
            "containsSyntheticMedia": True,
        },
    }
    try:
        video_id = subir(youtube, cuerpo, video)
    except HttpError as e:
        if "containsSyntheticMedia" in str(e):
            cuerpo["status"].pop("containsSyntheticMedia")
            video_id = subir(youtube, cuerpo, video)
        else:
            raise
    print(f"OK video subido: {video_id}")

    mini = PROYECTO / "miniatura.jpg"
    if mini.exists():
        try:
            youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(str(mini))).execute()
            print("OK miniatura aplicada")
        except HttpError as e:
            print(f"AVISO: no se pudo poner la miniatura ({e.resp.status}). Si el error es 403, "
                  "verifica tu canal con teléfono en https://www.youtube.com/verify")

    url = f"https://youtu.be/{video_id}"
    (PROYECTO / "url_youtube.txt").write_text(url, encoding="utf-8")
    historial = RAIZ / "historial.json"
    datos = json.loads(historial.read_text(encoding="utf-8")) if historial.exists() else []
    datos.append({"fecha": date.today().isoformat(), "tema": guion.get("tema_tendencia", guion["titulo"]),
                  "titulo": guion["titulo"], "url": url})
    historial.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nURL DEL VIDEO: {url}")


if __name__ == "__main__":
    main()
