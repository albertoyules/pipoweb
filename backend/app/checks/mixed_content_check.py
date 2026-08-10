"""
Check de mixed content (recursos http:// en una página https://).

Categoría: Seguridad básica (ver PIPO_PLANNING.md, sección 2).
Naturaleza: 100% pasivo (verde). Analizamos el HTML que ya nos ha
traído obtener_pagina() en busca de recursos (imágenes, scripts,
hojas de estilo, iframes) cargados por http:// en vez de https://.

Por qué importa: aunque la página principal esté cifrada, cada
recurso suelto en http:// viaja sin cifrar y puede ser interceptado o
alterado por cualquiera en la misma red (un ataque clásico de
"hombre en el medio"). Los navegadores ya avisan de esto solos; aquí
solo se lo señalamos también al dueño de la web.
"""

from bs4 import BeautifulSoup

# Etiqueta HTML -> atributo donde vive la URL del recurso.
ETIQUETAS_CON_RECURSO = {
    "img": "src",
    "script": "src",
    "link": "href",
    "iframe": "src",
}


def comprobar_mixed_content(pagina: dict) -> dict:
    """Función síncrona: solo analiza el HTML ya descargado, sin red propia."""
    if not pagina["ok"]:
        return _resultado(
            estado="rojo",
            prioridad="alta",
            detalle=f"No se ha podido acceder a la web para revisar mixed content ({pagina['error']}).",
        )

    if not pagina["url"].startswith("https://"):
        # Si la propia web no usa HTTPS, mixed content no aplica: el
        # problema de fondo es otro (falta de SSL), que ya cubre ssl_check.
        return _resultado(
            estado="ambar",
            prioridad="media",
            detalle="La web no usa HTTPS, así que este check no aplica (ver el check de SSL).",
        )

    soup = BeautifulSoup(pagina["html"], "html.parser")
    recursos_inseguros = []

    for etiqueta, atributo in ETIQUETAS_CON_RECURSO.items():
        for elemento in soup.find_all(etiqueta):
            url_recurso = elemento.get(atributo, "")
            if url_recurso.startswith("http://"):
                recursos_inseguros.append(url_recurso)

    datos = {"recursos_inseguros": recursos_inseguros, "total": len(recursos_inseguros)}

    if not recursos_inseguros:
        return _resultado(
            estado="verde",
            prioridad="baja",
            detalle="No se detectan recursos cargados por http:// en la página https.",
            datos=datos,
        )

    return _resultado(
        estado="rojo",
        prioridad="alta",
        detalle=f"Se detectan {len(recursos_inseguros)} recursos cargados sin cifrar (http://) en una página https.",
        datos=datos,
    )


def _resultado(estado: str, prioridad: str, detalle: str, datos: dict | None = None) -> dict:
    """Mismo formato común que usa el resto de checks (ver ssl_check.py)."""
    return {
        "check": "mixed_content",
        "estado": estado,
        "prioridad": prioridad,
        "detalle": detalle,
        "datos": datos or {},
    }
