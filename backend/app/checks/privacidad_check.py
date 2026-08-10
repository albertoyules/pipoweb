"""
Check de privacidad y cumplimiento (RGPD/LSSI) — diagnóstico básico.

Categoría: Privacidad y cumplimiento (ver PIPO_PLANNING.md, sección 2).
Naturaleza: 100% pasivo (verde). Buscamos enlaces y scripts en el
HTML público de la home, tal cual los vería cualquier visitante.

Importante (punto 8 del planning): esto es un diagnóstico superficial
de señales visibles, no una auditoría legal. Pipo no es un DPO. Si el
detalle dice "no se detecta política de privacidad", puede ser que
exista pero esté enlazada de una forma que no reconocemos (por
ejemplo, solo desde el footer de otra página) — se trata como
indicio, no como certeza jurídica.

Qué comprobamos:
- Enlaces a aviso legal, política de privacidad y política de cookies.
- Presencia de trackers de terceros conocidos (Google Analytics,
  Meta/Facebook Pixel) en el HTML de la home.
- Indicios de un banner de cookies (heurística simple, por palabras clave).
"""

import re

from bs4 import BeautifulSoup

# Trackers habituales, identificados por un fragmento característico
# de la URL de su script. Lista corta a propósito: mejor pocos falsos
# positivos que intentar cubrir cada herramienta de analítica que existe.
TRACKERS_CONOCIDOS = {
    "google-analytics.com": "Google Analytics",
    "googletagmanager.com": "Google Tag Manager",
    "connect.facebook.net": "Meta/Facebook Pixel",
    "hotjar.com": "Hotjar",
}

PALABRAS_AVISO_LEGAL = ("aviso legal", "aviso-legal", "legal notice")
PALABRAS_PRIVACIDAD = ("política de privacidad", "politica de privacidad", "privacy policy", "privacidad")
PALABRAS_COOKIES = ("cookies", "política de cookies")


def comprobar_privacidad(pagina: dict) -> dict:
    """
    A diferencia de otros checks, esta función es síncrona (no async):
    no hace ninguna petición de red propia, solo analiza el HTML que
    ya nos ha traído obtener_pagina().
    """
    if not pagina["ok"]:
        return _resultado(
            estado="rojo",
            prioridad="alta",
            detalle=f"No se ha podido acceder a la web para revisar privacidad ({pagina['error']}).",
        )

    soup = BeautifulSoup(pagina["html"], "html.parser")
    texto_enlaces = " ".join(
        f"{enlace.get_text(' ', strip=True)} {enlace.get('href', '')}".lower()
        for enlace in soup.find_all("a")
    )

    tiene_aviso_legal = any(p in texto_enlaces for p in PALABRAS_AVISO_LEGAL)
    tiene_privacidad = any(p in texto_enlaces for p in PALABRAS_PRIVACIDAD)
    tiene_cookies = any(p in texto_enlaces for p in PALABRAS_COOKIES)

    html_completo = pagina["html"].lower()
    trackers_detectados = [
        nombre for fragmento, nombre in TRACKERS_CONOCIDOS.items() if fragmento in html_completo
    ]

    # Heurística simple: buscamos algún elemento cuyo texto sugiera un
    # banner de consentimiento de cookies. No es perfecto (no
    # ejecutamos JavaScript, así que banners que se inyectan dinámicamente
    # no se detectan), por eso se trata como indicio, no como certeza.
    banner_cookies = bool(re.search(r"consentimiento|aceptar.{0,20}cookies|cookie.{0,20}consent", html_completo))

    datos = {
        "tiene_aviso_legal": tiene_aviso_legal,
        "tiene_politica_privacidad": tiene_privacidad,
        "tiene_politica_cookies": tiene_cookies,
        "trackers_detectados": trackers_detectados,
        "indicio_banner_cookies": banner_cookies,
    }

    return _evaluar(datos)


def _evaluar(datos: dict) -> dict:
    faltantes = []
    if not datos["tiene_aviso_legal"]:
        faltantes.append("aviso legal")
    if not datos["tiene_politica_privacidad"]:
        faltantes.append("política de privacidad")
    if not datos["tiene_politica_cookies"]:
        faltantes.append("política de cookies")

    hay_trackers_sin_banner = datos["trackers_detectados"] and not datos["indicio_banner_cookies"]

    if faltantes and hay_trackers_sin_banner:
        return _resultado(
            estado="rojo",
            prioridad="alta",
            detalle=(
                f"Faltan páginas legales básicas ({', '.join(faltantes)}) y además se detectan "
                f"trackers de terceros ({', '.join(datos['trackers_detectados'])}) sin indicio de "
                "banner de consentimiento."
            ),
            datos=datos,
        )

    if faltantes:
        return _resultado(
            estado="ambar",
            prioridad="media",
            detalle=f"No se detectan enlaces a: {', '.join(faltantes)}.",
            datos=datos,
        )

    if hay_trackers_sin_banner:
        return _resultado(
            estado="ambar",
            prioridad="media",
            detalle=(
                f"Se detectan trackers de terceros ({', '.join(datos['trackers_detectados'])}) "
                "sin indicio de banner de cookies."
            ),
            datos=datos,
        )

    return _resultado(
        estado="verde",
        prioridad="baja",
        detalle="Se detectan las páginas legales básicas y no hay señales evidentes de trackers sin consentimiento.",
        datos=datos,
    )


def _resultado(estado: str, prioridad: str, detalle: str, datos: dict | None = None) -> dict:
    """Mismo formato común que usa el resto de checks (ver ssl_check.py)."""
    return {
        "check": "privacidad",
        "estado": estado,
        "prioridad": prioridad,
        "detalle": detalle,
        "datos": datos or {},
    }
