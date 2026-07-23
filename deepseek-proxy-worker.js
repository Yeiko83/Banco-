/*
 * PROXY DEEPSEEK PARA TECINTEK LICITACIONES
 * ------------------------------------------
 * Este pequeño "puente" resuelve el bloqueo CORS que impide que un navegador
 * llame directamente a la API de DeepSeek. NO guarda tu clave: simplemente
 * reenvía la petición que hace tu web y devuelve la respuesta añadiendo las
 * cabeceras CORS que faltan.
 *
 * CÓMO DESPLEGARLO (gratis, ~2 minutos, sin tarjeta):
 *  1. Entra en  https://dash.cloudflare.com  y crea una cuenta.
 *  2. Menú izquierdo -> "Workers & Pages" -> botón "Create" -> "Create Worker".
 *  3. Ponle un nombre (ej: deepseek-proxy) y pulsa "Deploy".
 *  4. Pulsa "Edit code", BORRA todo lo que haya y PEGA este archivo completo.
 *  5. Pulsa "Deploy" (arriba a la derecha).
 *  6. Copia la URL que te da (ej: https://deepseek-proxy.TUUSUARIO.workers.dev).
 *  7. En la web de licitaciones -> "Configurar IA" -> DeepSeek -> pega esa URL
 *     en el campo "URL del proxy".  Ya está.
 */

const DEEPSEEK_URL = "https://api.deepseek.com/chat/completions";

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "authorization, content-type",
  "Access-Control-Max-Age": "86400",
};

export default {
  async fetch(request) {
    if (request.method === "OPTIONS") {
      return new Response(null, { headers: CORS });
    }
    if (request.method !== "POST") {
      return new Response("Solo se admite POST", { status: 405, headers: CORS });
    }
    const auth = request.headers.get("authorization") || "";
    const body = await request.text();

    let upstream;
    try {
      upstream = await fetch(DEEPSEEK_URL, {
        method: "POST",
        headers: { "content-type": "application/json", authorization: auth },
        body,
      });
    } catch (e) {
      return new Response(
        JSON.stringify({ error: { message: "No se pudo contactar con DeepSeek: " + e.message } }),
        { status: 502, headers: { ...CORS, "content-type": "application/json" } }
      );
    }

    const headers = new Headers(upstream.headers);
    for (const k in CORS) headers.set(k, CORS[k]);
    return new Response(upstream.body, { status: upstream.status, headers });
  },
};
