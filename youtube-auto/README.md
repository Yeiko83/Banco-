# youtube-auto: videos para YouTube a costo cero con Claude Code

Pipeline: **guion (Claude) → voz (Edge-TTS) → imágenes (Pollinations.ai) → montaje (FFmpeg) → subida (API de YouTube)**.

Los scripts de `scripts/` ya están escritos y el montaje está probado. Claude ya no tiene que inventarlos en cada ejecución: solo escribe el guion y los ejecuta. Así cada video sale más rápido, gasta menos tokens y falla menos.

## Archivos

| Archivo | Para qué sirve |
|---|---|
| `CLAUDE.md` | Instrucciones que Claude Code lee automáticamente |
| `.env.example` | Plantilla de configuración: cópiala como `.env` |
| `requirements.txt` | Librerías de Python |
| `scripts/pipeline.py` | Ejecuta las fases 2 a 5 en orden y valida el guion |
| `scripts/generar_voz.py` | Fase 2: voz |
| `scripts/generar_imagenes.py` | Fase 3: imágenes y miniatura |
| `scripts/ensamblar_video.py` | Fase 4: video con efecto Ken Burns |
| `scripts/subir_youtube.py` | Fase 5: subida y miniatura |

`.env`, `client_secrets.json`, `token.json` y `proyecto_actual/` están en `.gitignore` y **nunca deben subirse a GitHub**.

## Instalación en Windows

```powershell
winget install Python.Python.3.12
winget install Gyan.FFmpeg
npm install -g @anthropic-ai/claude-code
# cierra y abre PowerShell
git clone https://github.com/yeiko83/Banco-.git C:\Proyectos\Banco-
cd C:\Proyectos\Banco-\youtube-auto
git checkout claude/youtube-automation-setup-qbzadv
python -m pip install -r requirements.txt
copy .env.example .env
```

Para obtener `client_secrets.json`, sigue el Bloque 2 de tu guía (Google Cloud → YouTube Data API v3 → pantalla de consentimiento → usuario de prueba → ID de cliente "App de escritorio"). Guárdalo dentro de `youtube-auto\`.

## Uso

```powershell
cd C:\Proyectos\Banco-\youtube-auto
claude
```

Prompt:

> Ejecuta el pipeline de CLAUDE.md para crear y subir un video de 90 segundos sobre: 5 inventos antiguos que la ciencia aún no logra explicar. Dame el enlace de YouTube al final.

Para revisar el video antes de subirlo, pide "sin subir". Cuando te guste, ejecuta `python scripts/pipeline.py --desde subir`.

## Un video diario automático con tendencias

1. Prueba primero un video a mano (sección Uso) para que se cree `token.json`.
2. Prueba el modo diario una vez: `powershell -ExecutionPolicy Bypass -File .\diario.ps1`
3. Prográmalo: `powershell -ExecutionPolicy Bypass -File .\instalar_tarea_diaria.ps1 -Hora "18:00"`

Cada día: Google Trends (`TENDENCIAS_PAIS` en `.env`) → Claude elige un tema seguro, lo investiga en la web y escribe el guion → video → subida. Los temas usados quedan en `historial.json` y los registros en `logs\`. El PC debe estar encendido (o se ejecuta al encenderlo) y con la sesión de `claude` iniciada.

## ⚠️ Correcciones importantes a la guía original

1. **Los videos pueden quedar bloqueados en privado.** Google restringe a "privado" todo video subido con `videos.insert` desde un proyecto de API **no verificado** creado después de julio de 2020. Es posible que no puedas cambiarlo a Público en YouTube Studio. Para quitar la restricción hay que pedir la auditoría de cumplimiento de la API de YouTube (es gratis, pero tarda). Mientras tanto, la Fase 4 funciona igual y puedes subir `proyecto_actual\video_final.mp4` a mano desde YouTube Studio.
2. **El token vence a los 7 días** mientras la app esté en modo "Prueba" en la pantalla de consentimiento. El script lo detecta y vuelve a abrir el navegador. Para evitarlo, en *Pantalla de consentimiento → Publicar aplicación* pásala a "En producción". Seguirá apareciendo el aviso de "app no verificada", y eso es normal.
3. **La miniatura personalizada exige un canal verificado con teléfono** (youtube.com/verify). Si no lo está, el video se sube igual y el script solo avisa.
4. **Pollinations anónimo admite ~1 imagen cada 15 s.** El script espera 16 s entre imágenes: un video de 90 s (~16 escenas) tarda ~5 minutos en esta fase. Con una clave gratuita de pollinations.ai en `POLLINATIONS_TOKEN` puedes bajar `POLLINATIONS_PAUSA`.
5. **Mejor no uses `--dangerously-skip-permissions`.** Le da a Claude permiso para ejecutar cualquier comando en tu PC sin preguntar. Es más seguro abrir `claude` normal y, en la primera petición de permiso, elegir "permitir siempre" para `python scripts/...`. O usa `/permissions` para permitir `Bash(python scripts/*)`, `Bash(pip install *)` y `Bash(ffmpeg *)`.
6. **Contenido generado con IA:** YouTube exige declarar el contenido sintético realista. El script marca `containsSyntheticMedia`. Además, YouTube desmonetiza el contenido "repetitivo o producido en masa": si quieres monetizar, revisa cada guion y aporta valor propio.
7. **Duración:** la voz lee ~2,5 palabras por segundo. 90 s ≈ 225 palabras. `CLAUDE.md` ya incluye este cálculo.

## Solución de problemas

- `ffmpeg no está en el PATH` → cierra y abre la terminal después de instalarlo.
- `Access blocked / 403 access_denied` al iniciar sesión → tu correo no está en "Usuarios de prueba".
- `quotaExceeded` → la cuota gratuita (10 000 unidades/día) permite unas 6 subidas diarias (cada una cuesta ~1600).
- Imágenes con fondo liso → Pollinations no respondió. Borra esas `escena_XX.jpg` y ejecuta `python scripts/pipeline.py --desde imagenes`.
