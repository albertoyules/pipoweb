"""
Detección del "perfil" del sitio: qué tipo de web es, con qué CMS está
hecha y cómo de grande es aproximadamente.

Esto NO es un check con semáforo — no tiene estado verde/ámbar/rojo, no
entra en la nota. Es metadata que se calcula ANTES de decidir qué
checks condicionales lanzar (ver scanner.py): una tienda online activa
módulos de análisis que una landing de servicios no necesita, y al
revés, un login expuesto es una pregunta que solo tiene sentido si hay
zona privada.

100% pasivo: todo sale del HTML de la home ya descargada (mismo
'pagina' que usan seo/privacidad/tecnologia — no se pide dos veces) y,
como mucho, una petición ligera extra a sitemap.xml para estimar el
número de páginas — el mismo archivo público que ya lee seo_check.py.

Las señales son independientes entre sí a propósito: una tienda con
zona de clientes tiene tiene_checkout=True Y tiene_login=True al mismo
tiempo, y eso activa los dos bloques de checks condicionales, no solo
uno. "tipo_sitio" es solo la etiqueta que se le enseña al usuario
("Tienda online detectada"), calculada a partir de esas señales con
una prioridad fija — nunca decide por sí sola qué se ejecuta.
"""

import re

import httpx
from bs4 import BeautifulSoup

from app.checks.deteccion_cms import detectar_cms_y_version
from app.checks.pagina import USER_AGENT_PIPO, parece_dibujada_con_javascript, raiz_del_sitio

# Huellas de que hay un carrito/checkout de verdad, no solo la palabra
# "comprar" suelta en un botón de landing. Se buscan en el HTML crudo
# (rutas, scripts) y en enlaces/formularios ya parseados.
RUTAS_CHECKOUT = ("/carrito", "/cart", "/checkout", "/cesta", "/finalizar-compra")
HUELLAS_WOOCOMMERCE = ("woocommerce", "wc-cart", "add-to-cart")
HUELLAS_SHOPIFY = ("cdn.shopify.com", "shopify.theme", "/cart.js")
HUELLAS_PRESTASHOP = ("prestashop", "id_product")

# Rutas de login típicas. No se piden por red (eso sería activo): solo
# se busca si APARECEN COMO ENLACE en el HTML de la home, que es lo
# mismo que vería cualquier visitante que mire el código fuente.
RUTAS_LOGIN = ("/wp-login.php", "/mi-cuenta", "/my-account", "/login", "/acceso", "/area-cliente", "/area-privada", "/wp-admin")

# Señales de que la web es un blog/web de contenido: feed RSS, o
# estructura típica de posts (/blog/, /category/, /tag/, /author/).
RUTAS_BLOG = ("/feed", "/blog/", "/category/", "/tag/", "/author/", "rss+xml")

LIMITE_URLS_SITEMAP = 5000  # por si el sitemap es enorme, no lo leemos entero


def _hay_huella(html_minusculas: str, huellas: tuple[str, ...]) -> bool:
    return any(huella in html_minusculas for huella in huellas)


def _enlaces_contienen(soup: BeautifulSoup, rutas: tuple[str, ...]) -> bool:
    for enlace in soup.find_all("a", href=True):
        href = enlace["href"].lower()
        if any(ruta in href for ruta in rutas):
            return True
    return False


def _tiene_formulario_login(soup: BeautifulSoup) -> bool:
    """Un <form> con un campo type="password" es un formulario de acceso."""
    for formulario in soup.find_all("form"):
        if formulario.find("input", attrs={"type": "password"}):
            return True
    return False


def _detectar_senales(soup: BeautifulSoup, html: str, cms: str | None) -> dict:
    minusculas = html.lower()

    tiene_carrito = (
        (cms == "WordPress" and _hay_huella(minusculas, HUELLAS_WOOCOMMERCE))
        or cms == "Shopify"
        or _hay_huella(minusculas, HUELLAS_SHOPIFY)
        or _hay_huella(minusculas, HUELLAS_PRESTASHOP)
        or _enlaces_contienen(soup, RUTAS_CHECKOUT)
    )
    tiene_checkout = tiene_carrito or _hay_huella(minusculas, ("/checkout", "/finalizar-compra"))

    tiene_login = (
        _enlaces_contienen(soup, RUTAS_LOGIN)
        or _tiene_formulario_login(soup)
        or (cms == "WordPress" and "/wp-admin" in minusculas)
    )

    es_blog = _enlaces_contienen(soup, RUTAS_BLOG) or _hay_huella(minusculas, RUTAS_BLOG)

    return {
        "tiene_checkout": tiene_checkout,
        "tiene_carrito": tiene_carrito,
        "tiene_login": tiene_login,
        "es_blog": es_blog,
        "es_spa": parece_dibujada_con_javascript(html),
    }


def _etiqueta_tipo_sitio(senales: dict) -> str:
    """
    Una sola etiqueta descriptiva para mostrar al usuario, calculada a
    partir de las señales con una prioridad fija. No decide qué checks
    se ejecutan (eso lo hacen las señales directamente) — es solo texto.
    """
    if senales["tiene_checkout"] or senales["tiene_carrito"]:
        return "tienda_online"
    if senales["tiene_login"]:
        return "area_privada"
    if senales["es_blog"]:
        return "blog"
    return "landing_servicios"


async def _tamano_por_sitemap(url_pagina: str) -> dict:
    """
    Cuenta cuántas <loc> hay en sitemap.xml como estimación aproximada
    del número de páginas. Si el sitemap es un índice de sitemaps (caso
    típico en tiendas grandes), no baja a leer cada uno — con saber que
    existe y es un índice ya basta para decir "sitio grande".
    """
    base = raiz_del_sitio(url_pagina)
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=4.0, headers={"User-Agent": USER_AGENT_PIPO}) as cliente:
            respuesta = await cliente.get(f"{base}/sitemap.xml")
    except httpx.RequestError:
        return {"tiene_sitemap": False, "paginas_aprox": None}

    if respuesta.status_code != 200 or not respuesta.text.strip():
        return {"tiene_sitemap": False, "paginas_aprox": None}

    contenido = respuesta.text[: LIMITE_URLS_SITEMAP * 200]  # tope de bytes leídos, no solo de <loc>
    es_indice = "<sitemapindex" in contenido
    num_urls = len(re.findall(r"<loc>", contenido))

    return {
        "tiene_sitemap": True,
        "es_indice_de_sitemaps": es_indice,
        "paginas_aprox": None if es_indice else min(num_urls, LIMITE_URLS_SITEMAP),
    }


async def detectar_perfil(pagina: dict) -> dict:
    """
    Recibe la home ya descargada (ver pagina.py) para no volver a
    pedirla. Detecta el CMS con la misma función que usa
    tecnologia_check.py (app.checks.deteccion_cms), así que los dos
    checks siempre dicen el mismo CMS para el mismo HTML — es un
    parseo barato (ya en memoria, sin red), no compensa pasarlo por
    parámetro solo para ahorrarse una llamada.

    Si la página no se pudo descargar, se devuelve un perfil vacío en
    vez de intentar adivinar nada — sin HTML no hay señales que leer.
    """
    if not pagina["ok"]:
        return {
            "tipo_sitio": None,
            "cms": None,
            "version_cms": None,
            "senales": {},
            "tamano": {"tiene_sitemap": False, "paginas_aprox": None},
        }

    soup = BeautifulSoup(pagina["html"], "html.parser")
    cms, version_cms = detectar_cms_y_version(soup, pagina["html"])
    senales = _detectar_senales(soup, pagina["html"], cms)
    tamano = await _tamano_por_sitemap(pagina["url"])

    return {
        "tipo_sitio": _etiqueta_tipo_sitio(senales),
        "cms": cms,
        "version_cms": version_cms,
        "senales": senales,
        "tamano": tamano,
    }
