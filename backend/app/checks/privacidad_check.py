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

from app.checks.pagina import parece_dibujada_con_javascript

# Gestores de consentimiento de cookies conocidos, identificados por un
# fragmento de la URL de su script.
#
# Por qué hacía falta esto: casi ningún banner de cookies real está
# escrito en el HTML — lo inyecta uno de estos servicios con JavaScript
# después de cargar la página. Como Pipo no ejecuta JavaScript, buscar
# la palabra "aceptar cookies" en el HTML fallaba en la mayoría de webs
# que SÍ cumplen, y esa es la acusación más grave que hace Pipo. Ver el
# script del gestor es la prueba fiable de que el banner existe.
GESTORES_DE_COOKIES = {
    "cookiebot.com": "Cookiebot",
    "cookie-script.com": "CookieScript",
    "cookieyes.com": "CookieYes",
    "cdn.iubenda.com": "Iubenda",
    "cookielaw.org": "OneTrust",
    "onetrust.com": "OneTrust",
    "termly.io": "Termly",
    "complianz": "Complianz",
    "borlabs-cookie": "Borlabs Cookie",
    "cookieconsent": "Cookie Consent",
    "klaro": "Klaro",
    "tarteaucitron": "tarteaucitron",
    "osano.com": "Osano",
    "usercentrics": "Usercentrics",
    "didomi": "Didomi",
    "axeptio": "Axeptio",
}

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

    # Dos formas de detectar el banner de cookies, de más a menos fiable:
    # 1) el script de un gestor de consentimiento conocido (prueba casi
    #    segura de que el banner existe, aunque se dibuje con JavaScript);
    # 2) palabras sueltas en el HTML (indicio flojo, se mantiene por si
    #    el banner está escrito a mano).
    gestor_detectado = next(
        (nombre for fragmento, nombre in GESTORES_DE_COOKIES.items() if fragmento in html_completo),
        None,
    )
    indicio_texto = bool(
        re.search(r"consentimiento|aceptar.{0,20}cookies|cookie.{0,20}consent", html_completo)
    )
    banner_cookies = bool(gestor_detectado) or indicio_texto

    datos = {
        "tiene_aviso_legal": tiene_aviso_legal,
        "tiene_politica_privacidad": tiene_privacidad,
        "tiene_politica_cookies": tiene_cookies,
        "trackers_detectados": trackers_detectados,
        "indicio_banner_cookies": banner_cookies,
        "gestor_de_cookies": gestor_detectado,
    }

    # Web dibujada con JavaScript: los enlaces del pie (aviso legal,
    # privacidad, cookies) puede que ni siquiera estén en el HTML que
    # hemos descargado. Aquí no se acusa, se avisa — es la diferencia
    # entre "no tienes política de privacidad" y "no he podido verlo".
    if parece_dibujada_con_javascript(pagina["html"]):
        return _resultado(
            estado="ambar",
            prioridad="baja",
            detalle=(
                "Esta web se dibuja en el navegador con JavaScript y Pipo no puede leer sus enlaces "
                "legales desde fuera. Comprueba a mano que el aviso legal, la política de privacidad "
                "y la de cookies están enlazados y accesibles."
            ),
            datos={**datos, "verificable_sin_javascript": False},
        )

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
