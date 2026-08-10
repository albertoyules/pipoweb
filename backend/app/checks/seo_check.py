"""
Check de SEO técnico.

Categoría: SEO técnico (ver PIPO_PLANNING.md, sección 2).
Naturaleza: 100% pasivo (verde). Leemos el HTML público de la home
(la misma información que indexa Google) y dos archivos que existen
específicamente para que los lean buscadores: robots.txt y
sitemap.xml. No hay nada aquí que el dueño de la web no espere que se
lea.

Qué comprobamos:
- Meta title y meta description: lo que se ve en los resultados de Google.
- Open Graph (og:title, og:image...): cómo se ve al compartir en WhatsApp/redes.
- H1: el titular principal de la página, debería haber exactamente uno.
- Imágenes sin atributo alt: afecta a SEO y a accesibilidad.
- robots.txt y sitemap.xml: si existen, ayudan a que Google rastree bien la web.
- Datos estructurados (schema.org): metadatos que ayudan a Google a
  entender el contenido (por ejemplo, mostrar estrellas de reseñas).
"""

import httpx
from bs4 import BeautifulSoup

LONGITUD_TITLE_RECOMENDADA = (10, 60)  # caracteres, orientativo
LONGITUD_DESCRIPTION_RECOMENDADA = (50, 160)


async def comprobar_seo(pagina: dict) -> dict:
    """
    Recibe el resultado de obtener_pagina() (ver pagina.py) para no
    tener que descargar la home otra vez, y añade dos peticiones
    ligeras propias: robots.txt y sitemap.xml.
    """
    if not pagina["ok"]:
        return _resultado(
            estado="rojo",
            prioridad="alta",
            detalle=f"No se ha podido acceder a la web para revisar el SEO ({pagina['error']}).",
        )

    soup = BeautifulSoup(pagina["html"], "html.parser")
    problemas = []

    # --- Meta title ---
    etiqueta_title = soup.find("title")
    title = etiqueta_title.get_text(strip=True) if etiqueta_title else ""
    if not title:
        problemas.append("falta la etiqueta <title>")
    elif not (LONGITUD_TITLE_RECOMENDADA[0] <= len(title) <= LONGITUD_TITLE_RECOMENDADA[1]):
        problemas.append(f"el <title> mide {len(title)} caracteres (recomendado 10-60)")

    # --- Meta description ---
    etiqueta_description = soup.find("meta", attrs={"name": "description"})
    description = etiqueta_description.get("content", "").strip() if etiqueta_description else ""
    if not description:
        problemas.append("falta la meta description")
    elif not (LONGITUD_DESCRIPTION_RECOMENDADA[0] <= len(description) <= LONGITUD_DESCRIPTION_RECOMENDADA[1]):
        problemas.append(f"la meta description mide {len(description)} caracteres (recomendado 50-160)")

    # --- Open Graph (cómo se ve al compartir en redes/WhatsApp) ---
    tiene_og_title = soup.find("meta", property="og:title") is not None
    tiene_og_image = soup.find("meta", property="og:image") is not None
    if not tiene_og_title or not tiene_og_image:
        problemas.append("faltan etiquetas Open Graph (se vería mal al compartir en redes/WhatsApp)")

    # --- H1 ---
    h1s = soup.find_all("h1")
    if len(h1s) == 0:
        problemas.append("no hay ningún H1 en la página")
    elif len(h1s) > 1:
        problemas.append(f"hay {len(h1s)} etiquetas H1 (debería haber una sola)")

    # --- Imágenes sin alt ---
    imagenes = soup.find_all("img")
    sin_alt = [img for img in imagenes if not img.get("alt", "").strip()]
    if imagenes and len(sin_alt) > 0:
        problemas.append(f"{len(sin_alt)} de {len(imagenes)} imágenes no tienen atributo alt")

    # --- Datos estructurados (schema.org) ---
    tiene_datos_estructurados = soup.find("script", type="application/ld+json") is not None
    if not tiene_datos_estructurados:
        problemas.append("no se detectan datos estructurados (schema.org)")

    # --- robots.txt y sitemap.xml ---
    tiene_robots = await _existe(pagina["url"], "/robots.txt")
    tiene_sitemap = await _existe(pagina["url"], "/sitemap.xml")
    if not tiene_robots:
        problemas.append("no existe robots.txt")
    if not tiene_sitemap:
        problemas.append("no existe sitemap.xml")

    datos = {
        "title": title,
        "description": description,
        "tiene_open_graph": tiene_og_title and tiene_og_image,
        "num_h1": len(h1s),
        "imagenes_sin_alt": len(sin_alt),
        "total_imagenes": len(imagenes),
        "tiene_datos_estructurados": tiene_datos_estructurados,
        "tiene_robots_txt": tiene_robots,
        "tiene_sitemap_xml": tiene_sitemap,
    }

    return _evaluar(problemas, datos)


async def _existe(url_base: str, ruta: str) -> bool:
    """Comprueba si un archivo público estándar (robots.txt, sitemap.xml) existe."""
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=4.0) as cliente:
            respuesta = await cliente.get(url_base.rstrip("/") + ruta)
            return respuesta.status_code == 200
    except httpx.RequestError:
        return False


def _evaluar(problemas: list[str], datos: dict) -> dict:
    """
    Semáforo por cantidad de problemas encontrados: es una lista
    larga de comprobaciones pequeñas, así que tiene más sentido contar
    cuántas fallan que tratarlas todas como igual de graves.
    """
    if len(problemas) == 0:
        return _resultado(
            estado="verde",
            prioridad="baja",
            detalle="El SEO técnico básico está bien cubierto: title, description, H1 y datos estructurados presentes.",
            datos=datos,
        )

    if len(problemas) <= 3:
        return _resultado(
            estado="ambar",
            prioridad="media",
            detalle="Hay margen de mejora en SEO: " + "; ".join(problemas) + ".",
            datos=datos,
        )

    return _resultado(
        estado="rojo",
        prioridad="alta",
        detalle="El SEO técnico tiene varios problemas: " + "; ".join(problemas) + ".",
        datos=datos,
    )


def _resultado(estado: str, prioridad: str, detalle: str, datos: dict | None = None) -> dict:
    """Mismo formato común que usa el resto de checks (ver ssl_check.py)."""
    return {
        "check": "seo",
        "estado": estado,
        "prioridad": prioridad,
        "detalle": detalle,
        "datos": datos or {},
    }
