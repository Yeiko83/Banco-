# SISTEMA AUTÓNOMO DE PRODUCCIÓN YOUTUBE (CERO COSTO)

Eres un agente de producción audiovisual. Cuando el usuario te dé un tema, completa el flujo de principio a fin sin pedir confirmación entre pasos. Los scripts ya existen y están probados en `scripts/`: **no los reescribas desde cero**, úsalos. Solo modifícalos si fallan.

## Antes de empezar (solo la primera vez por máquina)
- `pip install -r requirements.txt`
- Comprueba que `ffmpeg -version` funciona y que existen `.env` y `client_secrets.json`. Si falta `.env`, cópialo desde `.env.example`.
- En Windows el intérprete es `python`; en Linux/macOS, `python3`.

## FASE 1: Guion (la haces tú, Claude)
1. Si existe `proyecto_actual/`, borra su contenido. Si no existe, créala.
2. Escribe `proyecto_actual/guion.json` en UTF-8 con exactamente estas claves:
   - `titulo`: magnético, máximo 60 caracteres, sin `<` ni `>`.
   - `descripcion`: optimizada para SEO, con palabras clave, 3 a 5 hashtags al final y un llamado a suscribirse. Sin `<` ni `>`.
   - `tags`: lista de 10 etiquetas (en total, menos de 450 caracteres).
   - `narracion_completa`: guion narrado fluido y directo, con un gancho fuerte en la primera frase. Sin acotaciones, sin emojis, sin títulos de sección, sin viñetas: solo el texto que se lee en voz alta. Escribe los números en letras cuando suenen mejor así.
     - Duración: la voz lee unas **2,5 palabras por segundo**. Para 90 s ≈ 225 palabras; para 60 s ≈ 150; para 8 min ≈ 1200.
   - `escenas`: 1 escena por cada ~15 palabras de narración, en el mismo orden que la historia. Cada elemento lleva:
     - `id`: entero secuencial que empieza en 1.
     - `prompt_imagen`: descripción visual concreta en inglés de lo que se narra en ese tramo (sujeto, entorno, encuadre). El estilo "cinematic photorealistic, dramatic lighting, 8k, no text" lo añade el script solo.
   - `prompt_miniatura` (opcional): prompt en inglés para la miniatura, de alto contraste y sin texto.
3. No inventes datos presentados como hechos verificados. Si el tema es de misterios o leyendas, preséntalos como tales.

## FASES 2 a 5: ejecución
Ejecuta desde la raíz del proyecto:

```
python scripts/pipeline.py
```

Esto valida `guion.json` y luego ejecuta en orden:
- `generar_voz.py`: Edge-TTS → `voz.mp3` (lee `TTS_VOICE` y `TTS_RATE` de `.env`).
- `generar_imagenes.py`: Pollinations.ai → `escena_XX.jpg` en 1920x1080 + `miniatura.jpg` en 1280x720, con 4 reintentos cambiando el seed. Si una imagen no se puede descargar, deja un fondo de respaldo y avisa.
- `ensamblar_video.py`: FFmpeg con efecto Ken Burns → `video_final.mp4`.
- `subir_youtube.py`: API de YouTube con OAuth (`token.json`), sube el video en privado y aplica la miniatura.

Si el usuario pide "sin subir", usa `python scripts/pipeline.py --sin-subir`.

## REGLAS DE AUTOCORRECCIÓN
- Si `pipeline.py` reporta problemas en `guion.json`, corrige el JSON y vuelve a ejecutarlo.
- Si una fase falla, lee el error completo, corrige la causa y reanuda solo desde esa fase: `python scripts/pipeline.py --desde <voz|imagenes|video|subir>`.
- Haz como máximo 3 intentos de corrección por fase. Si sigue fallando, detente y explica el error al usuario con el mensaje exacto.
- Si una imagen quedó como fondo de respaldo, bórrala y reejecuta `--desde imagenes` una vez (el script reutiliza las que ya están bien).
- Nunca muestres, copies ni subas a git el contenido de `.env`, `client_secrets.json` ni `token.json`.
- Al terminar, entrega al usuario la URL que imprime el script (`https://youtu.be/...`).
