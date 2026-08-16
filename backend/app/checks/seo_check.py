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

from app.checks.pagina import parece_dibujada_con_javascript, USER_AGENT_PIPO

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
            estado="sin_datos",
            prioridad="baja",
            detalle=f"No hemos podido leer la web para revisar el SEO ({pagina['error']}). No cuenta para la nota.",
        )

    soup = BeautifulSoup(pagina["html"], "html.parser")
    # Problemas separados por gravedad: no es lo mismo no tener título
    # (Google no sabe de qué va tu web) que tenerlo tres caracteres más
    # largo de lo recomendado. Antes se contaban todos iguales y cuatro
    # detalles menores bastaban para pintar el check de rojo crítico.
    graves = []
    menores = []

    # --- Meta title ---
    etiqueta_title = soup.find("title")
    title = etiqueta_title.get_text(strip=True) if etiqueta_title else ""
    if not title:
        graves.append("falta la etiqueta <title>: es el titular que sale en Google")
    elif not (LONGITUD_TITLE_RECOMENDADA[0] <= len(title) <= LONGITUD_TITLE_RECOMENDADA[1]):
        menores.append(f"el <title> mide {len(title)} caracteres (recomendado 10-60)")

    # --- Meta description ---
    etiqueta_description = soup.find("meta", attrs={"name": "description"})
    description = etiqueta_description.get("content", "").strip() if etiqueta_description else ""
    if not description:
        graves.append("falta la meta description: es el texto que Google enseña bajo el titular")
    elif not (LONGITUD_DESCRIPTION_RECOMENDADA[0] <= len(description) <= LONGITUD_DESCRIPTION_RECOMENDADA[1]):
        menores.append(f"la meta description mide {len(description)} caracteres (recomendado 50-160)")

    # --- Open Graph (cómo se ve al compartir en redes/WhatsApp) ---
    tiene_og_title = soup.find("meta", property="og:title") is not None
    tiene_og_image = soup.find("meta", property="og:image") is not None
    # Se dice cuál falta, no "faltan las etiquetas Open Graph" en bloque:
    # lo normal es tener og:title y og:description puestos por el CMS y
    # que solo falte la imagen. Decirlo en bloque hacía que Pipo pareciera
    # equivocado delante de alguien que sí las tiene casi todas.
    if not tiene_og_title and not tiene_og_image:
        menores.append(
            "faltan las etiquetas Open Graph (og:title y og:image): al compartir el enlace en "
            "WhatsApp o redes sale sin titular ni imagen"
        )
    elif not tiene_og_image:
        menores.append(
            "falta la etiqueta og:image: al compartir el enlace en WhatsApp o redes sale sin imagen"
        )
    elif not tiene_og_title:
        menores.append(
            "falta la etiqueta og:title: al compartir el enlace en WhatsApp o redes sale sin titular"
        )

    # --- H1 ---
    h1s = soup.find_all("h1")
    if len(h1s) == 0:
        graves.append("no hay ningún H1: la página no dice cuál es su titular principal")
    elif len(h1s) > 1:
        menores.append(f"hay {len(h1s)} etiquetas H1 (debería haber una sola)")

    # --- Imágenes sin alt ---
    imagenes = soup.find_all("img")
    sin_alt = [img for img in imagenes if not img.get("alt", "").strip()]
    if imagenes and len(sin_alt) > 0:
        menores.append(f"{len(sin_alt)} de {len(imagenes)} imágenes no tienen atributo alt")

    # --- Datos estructurados (schema.org) ---
    tiene_datos_estructurados = soup.find("script", type="application/ld+json") is not None
    if not tiene_datos_estructurados:
        menores.append("no se detectan datos estructurados (schema.org)")

    # --- robots.txt y sitemap.xml ---
    tiene_robots = await _existe(pagina["url"], "/robots.txt")
    tiene_sitemap = await _existe(pagina["url"], "/sitemap.xml")
    if not tiene_robots:
        menores.append("no existe robots.txt")
    if not tiene_sitemap:
        menores.append("no existe sitemap.xml")

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

    if parece_dibujada_con_javascript(pagina["html"]):
        # La web se dibuja en el navegador y nosotros no ejecutamos
        # JavaScript: el título y los textos pueden existir de verdad
        # aunque no estén en lo que hemos descargado. Decirlo en vez de
        # acusar (ver pagina.py).
        return _resultado(
            estado="ambar",
            prioridad="baja",
            detalle=(
                "Esta web se dibuja en el navegador con JavaScript, así que Pipo no puede leer su "
                "contenido tal y como lo ve Google. Conviene revisar el SEO con una herramienta que "
                "ejecute la página (por ejemplo, el propio inspector de Google Search Console)."
            ),
            datos={**datos, "verificable_sin_javascript": False},
        )

    return _evaluar(graves, menores, datos)


async def _existe(url_base: str, ruta: str) -> bool:
    """Comprueba si un archivo público estándar (robots.txt, sitemap.xml) existe."""
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=4.0, headers={"User-Agent": USER_AGENT_PIPO}) as cliente:
            respuesta = await cliente.get(url_base.rstrip("/") + ruta)
            return respuesta.status_code == 200
    except httpx.RequestError:
        return False


def _evaluar(graves: list[str], menores: list[str], datos: dict) -> dict:
    """
    Semáforo por gravedad, no por cantidad.

    - Rojo solo si faltan dos de las tres piezas básicas con las que
      Google construye tu resultado de búsqueda (título, descripción,
      H1). Eso sí es un problema serio de verdad.
    - Ámbar para todo lo demás: una pieza básica suelta, o cualquier
      número de detalles de los pequeños.
    - Verde si no hay nada.

    Antes bastaban cuatro pegas cualesquiera para el rojo, y eso hacía
    que un <title> largo de más pesara como un certificado caducado.
    """
    if len(graves) >= 2:
        return _resultado(
            estado="rojo",
            prioridad="alta",
            detalle="Google no tiene lo básico para entender tu web: " + "; ".join(graves) + ".",
            datos=datos,
        )

    problemas = graves + menores
    if problemas:
        return _resultado(
            estado="ambar",
            prioridad="media",
            detalle="Hay margen de mejora en SEO: " + "; ".join(problemas) + ".",
            datos=datos,
        )

    return _resultado(
        estado="verde",
        prioridad="baja",
        detalle="El SEO técnico básico está bien cubierto: title, description, H1 y datos estructurados presentes.",
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
