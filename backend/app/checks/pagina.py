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


async def obtener_pagina(dominio: str, timeout: float = 5.0) -> dict:
    """
    Descarga la home por HTTPS. Devuelve siempre un diccionario con
    'ok' para que quien lo use sepa de un vistazo si hubo error, sin
    tener que andar con try/except repetido en cada check.
    """
    url = f"https://{dominio}"
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as cliente:
            respuesta = await cliente.get(url)
    except httpx.RequestError as error:
        return {"ok": False, "error": str(error), "url": url, "html": "", "headers": {}}

    return {
        "ok": True,
        "error": None,
        "url": str(respuesta.url),
        "html": respuesta.text,
        "headers": respuesta.headers,
    }
