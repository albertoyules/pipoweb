"""
Detección de CMS/plataforma a partir del HTML ya descargado.

Extraído de tecnologia_check.py el 16 sep 2026 para que perfil_sitio.py
pueda usar la misma detección sin duplicarla ni arriesgarse a que los
dos módulos digan cosas distintas del mismo HTML.

100% pasivo: solo mira la etiqueta <meta name="generator"> y huellas
que quedan en el HTML normal de la página (rutas, enlaces de
descubrimiento de API) aunque esa etiqueta se haya quitado a propósito.
"""

import re

from bs4 import BeautifulSoup


def detectar_cms_y_version(soup: BeautifulSoup, html: str) -> tuple[str | None, str | None]:
    """
    Primero mira la etiqueta <meta name="generator">, que es la forma
    más directa (varios CMS la rellenan solos). Si no está, busca
    huellas de WordPress/WooCommerce que quedan aunque se quite esa
    etiqueta por seguridad: el enlace de descubrimiento de su API REST,
    o rutas /wp-content//wp-includes/ que aparecen en cualquier
    instalación por defecto (scripts, hojas de estilo...), o el script
    de Shopify que carga en cualquier tienda de esa plataforma.
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
        if "shopify" in contenido.lower():
            return "Shopify", None

    # Sin <meta generator>: buscamos huellas que sobreviven aunque esa
    # etiqueta se haya quitado a propósito.
    if "cdn.shopify.com" in html or "Shopify.theme" in html:
        return "Shopify", None

    tiene_enlace_api_rest = soup.find("link", attrs={"rel": "https://api.w.org/"}) is not None
    tiene_rutas_wp = "/wp-content/" in html or "/wp-includes/" in html
    if tiene_enlace_api_rest or tiene_rutas_wp:
        # WooCommerce es un plugin de WordPress, no un CMS aparte: si
        # hay huellas suyas, seguimos diciendo "WordPress" (es lo que
        # tecnologia_check sabe auditar, versión incluida) y es
        # perfil_sitio.py quien decide aparte si además es una tienda.
        return "WordPress", None

    return None, None
