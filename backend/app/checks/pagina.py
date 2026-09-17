"""
Descarga compartida de la home del dominio.

Varios checks (SEO, RGPD, mixed content) necesitan leer el HTML de la
página. En vez de que cada uno la pida por su cuenta, este módulo la
descarga una sola vez y el resultado se reparte entre todos: menos
peticiones al servidor del cliente, y más rápido para nosotros.

Sigue siendo 100% pasivo: es la misma petición que hace un navegador
al entrar en la web.
"""

import asyncio
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from app.seguridad import variante_www

# Códigos típicos de un bloqueo temporal (rate-limit, challenge de un
# WAF) en vez de un error real de la web. Vale la pena reintentar una
# vez: se ha visto en producción que la MISMA petición, repetida a los
# pocos segundos, a veces sí pasa — mientras que 404/500 son errores
# reales que repetir no arregla. Ver ejecutar_escaneo en scanner.py.
CODIGOS_REINTENTABLES = (403, 429, 503)
ESPERA_REINTENTO_SEGUNDOS = 1.5

# Pipo se identifica por su nombre, no se disfraza de navegador.
#
# Hace falta un User-Agent porque el de fábrica de httpx ("python-httpx/…")
# lo bloquean bastantes servidores: 6 de las 39 webs del estudio del 16 ago
# 2026 devolvían 403 solo por eso. Se comprobó que las seis aceptan
# cualquier UA razonable, incluido este, que dice quién es y a dónde ir a
# preguntar. Disfrazarse de Chrome funcionaría igual, pero sería lo
# contrario de lo que Pipo dice ser: un visitante identificado que solo
# mira lo público.
USER_AGENT_PIPO = "Mozilla/5.0 (compatible; PipoBot/1.0; +https://pipoweb.com)"

# Contenedores típicos de las webs que se dibujan con JavaScript en el
# navegador (React, Vue, Angular, Next...). Si la página trae uno de
# estos y casi nada de texto, lo que hemos descargado es el envoltorio
# vacío, no la web que ve una persona.
MARCAS_DE_JAVASCRIPT = ('id="root"', "id='root'", 'id="app"', "id='app'", 'id="__next"', "data-reactroot", "ng-version")
MINIMO_TEXTO_VISIBLE = 400  # caracteres


def raiz_del_sitio(url: str) -> str:
    """
    Solo el esquema y el host de una URL: de "https://ejemplo.es/es/"
    saca "https://ejemplo.es".

    Hace falta porque la url que devuelve obtener_pagina() es la FINAL,
    ya seguidos los redirects, y muchas webs mandan la home a un
    subdirectorio de idioma. Pegándole la ruta a esa url, Pipo pedía
    "/es/robots.txt" —que no existe en ninguna parte— y acusaba de no
    tener robots.txt ni sitemap.xml a webs que tienen los dos. Lo mismo
    con /es/readme.html en tecnologia_check, que por eso no detectaba la
    versión de WordPress en esas webs. Encontrado el 20 ago 2026.
    """
    partes = urlparse(url)
    return f"{partes.scheme}://{partes.netloc}"


def parece_dibujada_con_javascript(html: str) -> bool:
    """
    ¿Lo que hemos descargado es la web de verdad, o un esqueleto que se
    rellena en el navegador?

    Importa porque Pipo no ejecuta JavaScript (a propósito: es lo que lo
    mantiene rápido y 100% pasivo). En una web así, el HTML que llega no
    tiene ni textos ni enlaces, y los checks que los buscan —SEO,
    privacidad, accesibilidad— dirían que faltan cosas que en realidad
    están. Antes de acusar a nadie, conviene saber que estamos en este
    caso y decir "no hemos podido comprobarlo" en vez de "no lo tienes".
    """
    if not html:
        return False

    minusculas = html.lower()
    if not any(marca in minusculas for marca in MARCAS_DE_JAVASCRIPT):
        return False

    soup = BeautifulSoup(html, "html.parser")
    for etiqueta in soup(["script", "style", "noscript"]):
        etiqueta.decompose()
    texto_visible = soup.get_text(" ", strip=True)
    return len(texto_visible) < MINIMO_TEXTO_VISIBLE


async def _intentar_una_vez(host: str, timeout: float) -> dict:
    """Un único intento de descarga contra un host concreto, sin reintentos."""
    url = f"https://{host}"
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=timeout,
            headers={"User-Agent": USER_AGENT_PIPO},
        ) as cliente:
            respuesta = await cliente.get(url)
    except httpx.RequestError as error:
        return {
            "ok": False,
            "error": str(error),
            "status_code": None,
            "url": url,
            "html": "",
            "headers": {},
            "host_pedido": host,
            "host_servido": None,
        }

    # Un 403 o un 500 NO son la web del cliente: son una página de error,
    # normalmente de 100-200 bytes. Analizarla como si fuera su home hacía
    # que Pipo dijera que no tiene ni título, ni H1, ni aviso legal, ni
    # etiqueta de móvil — todo falso, y todo dicho con la misma seguridad
    # que un hallazgo real. Le pasaba a 6 de las 39 webs del estudio del
    # 16 ago 2026, entre ellas un despacho de abogados al que se estuvo a
    # punto de acusar de cuatro cosas que sí tenía.
    if respuesta.status_code >= 400:
        return {
            "ok": False,
            "error": f"el servidor respondió {respuesta.status_code}",
            "status_code": respuesta.status_code,
            "url": str(respuesta.url),
            "html": "",
            "headers": respuesta.headers,
            "host_pedido": host,
            "host_servido": None,
        }

    return {
        "ok": True,
        "error": None,
        "status_code": respuesta.status_code,
        "url": str(respuesta.url),
        "html": respuesta.text,
        "headers": respuesta.headers,
        "host_pedido": host,
        "host_servido": host,
    }


async def _descargar(host: str, timeout: float) -> dict:
    """
    Descarga con un reintento si el primer intento da un código
    típico de bloqueo temporal (ver CODIGOS_REINTENTABLES). No es
    infalible: si el bloqueo es permanente contra el origen desde el
    que llama Pipo (visto en producción con algún hosting que
    bloquea por IP de datacenter, no por nada que Pipo mande), el
    reintento también falla y se acaba devolviendo sin_datos, que es
    lo correcto — no es un fallo de la web analizada, es un límite de
    lo que Pipo puede comprobar desde fuera (ver decisión #13 de
    CLAUDE.md: si un servidor bloquea a PipoBot, se acepta el
    sin_datos, nunca se camufla el origen).
    """
    resultado = await _intentar_una_vez(host, timeout)
    if resultado["ok"] or resultado["status_code"] not in CODIGOS_REINTENTABLES:
        return resultado

    await asyncio.sleep(ESPERA_REINTENTO_SEGUNDOS)
    return await _intentar_una_vez(host, timeout)


async def obtener_pagina(dominio: str, timeout: float = 5.0) -> dict:
    """
    Descarga la home por HTTPS. Devuelve siempre un diccionario con
    'ok' para que quien lo use sepa de un vistazo si hubo error, sin
    tener que andar con try/except repetido en cada check.

    Si la forma pedida no responde, se reintenta con la otra variante
    del "www" antes de darse por vencido. Es muy común que solo una de
    las dos esté bien configurada: en el estudio del 16 ago 2026,
    mchomeinmobiliaria.com no servía HTTPS en la raíz pero sí en
    www., y Pipo la puntuaba con un 33 sobre 100 cuando la web real
    saca un 70. Dar por muerta una web que funciona es la peor clase
    de error que puede cometer Pipo: acusa, y encima de algo falso.

    Quien lea el resultado sabe por 'host_servido' cuál de las dos
    respondió (experiencia_check lo usa para avisar de que la otra
    forma no funciona, que sí es un problema real, pero pequeño).
    """
    resultado = await _descargar(dominio, timeout)
    if resultado["ok"]:
        return resultado

    otra_forma = variante_www(dominio)
    if otra_forma == dominio:
        return resultado

    alternativa = await _descargar(otra_forma, timeout)
    if not alternativa["ok"]:
        # Ninguna de las dos responde. Se devuelve el error de la que
        # pidió el usuario, que es la que le importa.
        return resultado

    alternativa["host_pedido"] = dominio
    return alternativa
