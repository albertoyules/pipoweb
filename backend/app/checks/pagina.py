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
