"""
Descarga compartida de la home del dominio.

Varios checks (SEO, RGPD, mixed content) necesitan leer el HTML de la
página. En vez de que cada uno la pida por su cuenta, este módulo la
descarga una sola vez y el resultado se reparte entre todos: menos
peticiones al servidor del cliente, y más rápido para nosotros.

Sigue siendo 100% pasivo: es la misma petición que hace un navegador
al entrar en la web.
"""

import httpx
from bs4 import BeautifulSoup

from app.seguridad import variante_www

# Contenedores típicos de las webs que se dibujan con JavaScript en el
# navegador (React, Vue, Angular, Next...). Si la página trae uno de
# estos y casi nada de texto, lo que hemos descargado es el envoltorio
# vacío, no la web que ve una persona.
MARCAS_DE_JAVASCRIPT = ('id="root"', "id='root'", 'id="app"', "id='app'", 'id="__next"', "data-reactroot", "ng-version")
MINIMO_TEXTO_VISIBLE = 400  # caracteres


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


async def _descargar(host: str, timeout: float) -> dict:
    """Un intento de descarga contra un host concreto."""
    url = f"https://{host}"
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as cliente:
            respuesta = await cliente.get(url)
    except httpx.RequestError as error:
        return {
            "ok": False,
            "error": str(error),
            "url": url,
            "html": "",
            "headers": {},
            "host_pedido": host,
            "host_servido": None,
        }

    return {
        "ok": True,
        "error": None,
        "url": str(respuesta.url),
        "html": respuesta.text,
        "headers": respuesta.headers,
        "host_pedido": host,
        "host_servido": host,
    }


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
