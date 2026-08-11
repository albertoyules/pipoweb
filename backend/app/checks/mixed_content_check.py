"""
Check de mixed content (recursos http:// en una página https://) y de
Subresource Integrity (SRI) en scripts/hojas de estilo externas.

Categoría: Seguridad básica (ver PIPO_PLANNING.md, sección 2).
Naturaleza: 100% pasivo (verde). Analizamos el HTML que ya nos ha
traído obtener_pagina() en busca de recursos (imágenes, scripts,
hojas de estilo, iframes) cargados por http:// en vez de https://, y
de scripts/CSS cargados desde otro dominio (típicamente un CDN) sin
el atributo "integrity".

Por qué importa lo primero: aunque la página principal esté cifrada,
cada recurso suelto en http:// viaja sin cifrar y puede ser
interceptado o alterado por cualquiera en la misma red (un ataque
clásico de "hombre en el medio"). Los navegadores ya avisan de esto
solos; aquí solo se lo señalamos también al dueño de la web.

Por qué importa lo segundo (SRI): si un script de un CDN externo se
carga sin "integrity", y ese CDN se ve comprometido algún día, el
código malicioso se ejecutaría en la web del cliente sin que él haya
cambiado nada. Es un aviso de refuerzo, no tan grave como servir
contenido directamente sin cifrar — por eso nunca sube a rojo, solo a
ámbar, y solo si no hay ya un problema de mixed content (ese manda).
"""

from urllib.parse import urlparse

from bs4 import BeautifulSoup

# Etiqueta HTML -> atributo donde vive la URL del recurso.
ETIQUETAS_CON_RECURSO = {
    "img": "src",
    "script": "src",
    "link": "href",
    "iframe": "src",
}


def _scripts_externos_sin_sri(soup: BeautifulSoup, dominio_pagina: str) -> list[str]:
    """
    Scripts y hojas de estilo cargados desde OTRO dominio (típico de un
    CDN) que no llevan el atributo "integrity". Los recursos del mismo
    dominio no necesitan SRI — ya confías en tu propio servidor.
    """
    sin_sri = []
    etiquetas = soup.find_all("script", src=True) + soup.find_all(
        "link", rel="stylesheet", href=True
    )
    for etiqueta in etiquetas:
        url = etiqueta.get("src") or etiqueta.get("href")
        if not url.startswith("http"):
            continue  # relativa: mismo origen, no aplica
        host_recurso = urlparse(url).netloc
        if host_recurso and host_recurso != dominio_pagina and not etiqueta.get("integrity"):
            sin_sri.append(url)
    return sin_sri


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

    dominio_pagina = urlparse(pagina["url"]).netloc
    scripts_sin_sri = _scripts_externos_sin_sri(soup, dominio_pagina)

    datos = {
        "recursos_inseguros": recursos_inseguros,
        "total": len(recursos_inseguros),
        "scripts_externos_sin_integrity": scripts_sin_sri,
    }

    if recursos_inseguros:
        return _resultado(
            estado="rojo",
            prioridad="alta",
            detalle=f"Se detectan {len(recursos_inseguros)} recursos cargados sin cifrar (http://) en una página https.",
            datos=datos,
        )

    if scripts_sin_sri:
        return _resultado(
            estado="ambar",
            prioridad="media",
            detalle=f"{len(scripts_sin_sri)} script(s)/hoja(s) de estilo externas se cargan sin verificación de integridad (SRI). Si el proveedor externo se ve comprometido, ese código se ejecutaría igual en tu web.",
            datos=datos,
        )

    return _resultado(
        estado="verde",
        prioridad="baja",
        detalle="No se detectan recursos cargados por http:// en la página https, y los scripts externos usan verificación de integridad (SRI) o son del propio dominio.",
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
