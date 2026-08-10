"""
Check de tecnología/CMS y si está desactualizada.

Categoría: seguridad básica (ver PIPO_PLANNING.md, sección 2).
Naturaleza: 100% pasivo (verde). Todo lo que miramos es información que
la propia web publica a cualquier visitante sin querer: la etiqueta
<meta name="generator">, el enlace de descubrimiento de la API REST de
WordPress (<link rel="https://api.w.org/">), rutas como /wp-content/
que aparecen en el HTML normal de la página, y el archivo readme.html
que WordPress instala por defecto en la raíz — es un archivo público
más, como robots.txt.

Para saber cuál es la última versión estable, consultamos la propia
API pública de WordPress.org (api.wordpress.org) — no el dominio del
cliente. Es igual de pasivo: es la misma consulta que hace el propio
WordPress del cliente para avisar de que hay una actualización.

Por qué importa: un CMS desactualizado es la puerta de entrada más
común para atacar la web de una pyme (vulnerabilidades conocidas y
públicas de versiones antiguas). Es justo el ejemplo "WordPress
desactualizado" que ya aparecía en el "cómo funciona" de la landing.
"""

import re

import httpx
from bs4 import BeautifulSoup
from packaging.version import InvalidVersion, Version

# Si algún día falla la consulta a la API de WordPress.org, usamos esta
# versión como referencia de "recién actualizado" en vez de no decir
# nada. Conviene revisarla de vez en cuando (igual que el modelo de
# Gemini en app/ia/cliente.py) — no es crítico si se queda unas
# versiones por detrás, solo hace la comparación un poco menos precisa.
ULTIMA_VERSION_WP_RESPALDO = "6.7"


async def comprobar_tecnologia(pagina: dict) -> dict:
    """
    Recibe el resultado de obtener_pagina() (ver pagina.py) para no
    volver a descargar la home. Si detecta WordPress y no puede sacar
    la versión de ahí, hace una petición extra ligera a /readme.html.
    """
    if not pagina["ok"]:
        return _resultado(
            estado="rojo",
            prioridad="alta",
            detalle=f"No se ha podido acceder a la web para identificar su tecnología ({pagina['error']}).",
        )

    soup = BeautifulSoup(pagina["html"], "html.parser")

    cms, version = _detectar_cms_y_version(soup, pagina["html"])

    if cms is None:
        return _resultado(
            estado="verde",
            prioridad="baja",
            detalle="No se ha detectado ningún gestor de contenidos (CMS) conocido en la web; probablemente está hecha a medida o no expone esta información.",
            datos={"cms_detectado": None},
        )

    if cms == "WordPress" and version is None:
        version = await _version_wordpress_desde_readme(pagina["url"])

    if cms != "WordPress" or version is None:
        detalle_version = f" (versión {version})" if version else ""
        return _resultado(
            estado="ambar",
            prioridad="media",
            detalle=f"Se ha detectado que la web usa {cms}{detalle_version}, pero no ha sido posible comprobar desde fuera si está actualizada.",
            datos={"cms_detectado": cms, "version_detectada": version},
        )

    # A partir de aquí: WordPress con versión conocida.
    ultima_version = await _ultima_version_estable_wordpress()

    return _evaluar_wordpress(version, ultima_version)


def _detectar_cms_y_version(soup: BeautifulSoup, html: str) -> tuple[str | None, str | None]:
    """
    Primero mira la etiqueta <meta name="generator">, que es la forma
    más directa (varios CMS la rellenan solos). Si no está, busca
    huellas de WordPress que quedan aunque se quite esa etiqueta por
    seguridad: el enlace de descubrimiento de su API REST, o rutas
    /wp-content//wp-includes/ que aparecen en cualquier instalación
    por defecto (scripts, hojas de estilo...).
    """
    generator = soup.find("meta", attrs={"name": "generator"})
    contenido = generator.get("content", "").strip() if generator else ""

    if contenido:
        coincidencia = re.match(r"WordPress\s+([\d.]+)", contenido, re.IGNORECASE)
        if coincidencia:
            return "WordPress", coincidencia.group(1)
        if contenido.lower().startswith("joomla"):
            return "Joomla", None
        if contenido.lower().startswith("drupal"):
            coincidencia = re.search(r"Drupal\s+([\d.]+)", contenido, re.IGNORECASE)
            return "Drupal", coincidencia.group(1) if coincidencia else None
        if "prestashop" in contenido.lower():
            return "PrestaShop", None
        if "wix.com" in contenido.lower():
            return "Wix", None
        if "squarespace" in contenido.lower():
            return "Squarespace", None

    # Sin <meta generator>: buscamos huellas de WordPress que sobreviven
    # aunque esa etiqueta se haya quitado a propósito.
    tiene_enlace_api_rest = soup.find("link", attrs={"rel": "https://api.w.org/"}) is not None
    tiene_rutas_wp = "/wp-content/" in html or "/wp-includes/" in html
    if tiene_enlace_api_rest or tiene_rutas_wp:
        return "WordPress", None

    return None, None


async def _version_wordpress_desde_readme(url_base: str) -> str | None:
    """
    WordPress instala por defecto un readme.html en la raíz con la
    versión en las primeras líneas ("=== WordPress === \n\n Version
    X.Y"). Es un archivo público más, como robots.txt: cualquier
    visitante puede pedirlo sin credenciales. Algunas webs lo borran
    por seguridad, en cuyo caso simplemente no encontramos versión.
    """
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=4.0) as cliente:
            respuesta = await cliente.get(url_base.rstrip("/") + "/readme.html")
    except httpx.RequestError:
        return None

    if respuesta.status_code != 200:
        return None

    coincidencia = re.search(r"Version\s+([\d.]+)", respuesta.text[:2000])
    return coincidencia.group(1) if coincidencia else None


async def _ultima_version_estable_wordpress() -> str:
    """
    Consulta la API pública de WordPress.org que usa el propio
    WordPress para avisar de actualizaciones. Si falla (red, timeout),
    usamos ULTIMA_VERSION_WP_RESPALDO en vez de dejar el check sin
    poder valorar nada.
    """
    try:
        async with httpx.AsyncClient(timeout=4.0) as cliente:
            respuesta = await cliente.get("https://api.wordpress.org/core/version-check/1.7/")
            datos = respuesta.json()
            return datos["offers"][0]["version"]
    except (httpx.RequestError, KeyError, IndexError, ValueError):
        return ULTIMA_VERSION_WP_RESPALDO


def _evaluar_wordpress(version_instalada: str, version_ultima: str) -> dict:
    """
    Compara versiones con packaging.version (ya en requirements.txt)
    en vez de a mano, para no tropezar con casos raros (10.0 vs 9.2).
    Si la versión detectada no es un número de verdad (por ejemplo, un
    plugin ha puesto algo raro en el generator), lo tratamos como
    "no se puede evaluar" en vez de reventar.
    """
    datos = {
        "cms_detectado": "WordPress",
        "version_detectada": version_instalada,
        "ultima_version_conocida": version_ultima,
    }

    try:
        instalada = Version(version_instalada)
        ultima = Version(version_ultima)
    except InvalidVersion:
        return _resultado(
            estado="ambar",
            prioridad="media",
            detalle=f"Se ha detectado WordPress {version_instalada}, pero no ha sido posible comparar la versión de forma fiable.",
            datos=datos,
        )

    if instalada >= ultima:
        return _resultado(
            estado="verde",
            prioridad="baja",
            detalle=f"WordPress está actualizado (versión {version_instalada}).",
            datos=datos,
        )

    if instalada.release[0] < ultima.release[0]:
        return _resultado(
            estado="rojo",
            prioridad="alta",
            detalle=f"WordPress está desactualizado: tiene la versión {version_instalada} y la última estable es {version_ultima}. Las versiones antiguas suelen tener vulnerabilidades conocidas y públicas.",
            datos=datos,
        )

    return _resultado(
        estado="ambar",
        prioridad="media",
        detalle=f"WordPress no tiene la última versión: tiene la {version_instalada} y la última estable es la {version_ultima}. Conviene actualizar cuando sea posible.",
        datos=datos,
    )


def _resultado(estado: str, prioridad: str, detalle: str, datos: dict | None = None) -> dict:
    """Mismo formato común que usa el resto de checks (ver ssl_check.py)."""
    return {
        "check": "tecnologia",
        "estado": estado,
        "prioridad": prioridad,
        "detalle": detalle,
        "datos": datos or {},
    }
