"""Obtiene las búsquedas en tendencia de Google Trends (RSS público, gratis) y descarta las ya usadas.

Uso:
    python scripts/tendencias.py            # imprime las tendencias de hoy en JSON
    python scripts/tendencias.py --pais MX
"""
import argparse
import json
import re
import xml.etree.ElementTree as ET

import requests

from comun import RAIZ, env

RSS = "https://trends.google.com/trending/rss?geo={pais}"
NS = {"ht": "https://trends.google.com/trending/rss"}
HISTORIAL = RAIZ / "historial.json"


def cargar_historial() -> list[dict]:
    if HISTORIAL.exists():
        return json.loads(HISTORIAL.read_text(encoding="utf-8"))
    return []


def normalizar(t: str) -> str:
    return re.sub(r"\W+", " ", t.lower()).strip()


def parsear(xml: str) -> list[dict]:
    raiz = ET.fromstring(xml)
    temas = []
    for item in raiz.iter("item"):
        noticias = [
            {"titulo": (n.findtext("ht:news_item_title", "", NS) or "").strip(),
             "fuente": (n.findtext("ht:news_item_source", "", NS) or "").strip(),
             "url": (n.findtext("ht:news_item_url", "", NS) or "").strip()}
            for n in item.findall("ht:news_item", NS)
        ]
        temas.append({
            "tema": (item.findtext("title") or "").strip(),
            "trafico": (item.findtext("ht:approx_traffic", "", NS) or "").strip(),
            "noticias": noticias[:3],
        })
    return [t for t in temas if t["tema"]]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--pais", default=env("TENDENCIAS_PAIS", "CO"))
    a = p.parse_args()

    r = requests.get(RSS.format(pais=a.pais), timeout=30,
                     headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    usados = {normalizar(h["tema"]) for h in cargar_historial()}
    temas = [t for t in parsear(r.text) if normalizar(t["tema"]) not in usados]
    print(json.dumps({"pais": a.pais, "tendencias": temas}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
