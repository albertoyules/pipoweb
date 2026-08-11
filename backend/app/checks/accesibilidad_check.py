"""
Check de accesibilidad web básica.

Categoría: Accesibilidad (ver PIPO_PLANNING.md, sección 2). No es solo
"nice to have": desde junio de 2025 la Ley 11/2023 (transposición de
la European Accessibility Act) obliga a bastantes negocios en España a
que sus webs/apps sean accesibles.

Naturaleza: 100% pasivo (verde). Analizamos el HTML público de la home
que ya nos ha traído obtener_pagina() — no cargamos la página en un
navegador real ni medimos contraste de color (eso exigiría renderizar
la página de verdad, más allá de leer el HTML). Es un diagnóstico de
señales básicas, no una auditoría WCAG completa.

Qué comprobamos:
- El atributo lang en <html>: sin él, los lectores de pantalla no
  saben en qué idioma pronunciar el contenido.
- Campos de formulario (texto, email, etc.) sin ninguna etiqueta
  asociada: quien usa un lector de pantalla no sabe qué tiene que
  rellenar.
- El texto alternativo de imágenes ya lo comprueba seo_check.py — no
  se duplica aquí.
"""

from bs4 import BeautifulSoup

TIPOS_INPUT_QUE_NECESITAN_ETIQUETA = {
    "text", "email", "tel", "password", "number", "search", "url", "date",
}


def _tiene_etiqueta_asociada(campo, soup: BeautifulSoup) -> bool:
    """
    Un campo está bien etiquetado si tiene aria-label, aria-labelledby,
    o un <label for="su-id">. El placeholder NO cuenta como etiqueta de
    verdad (desaparece al escribir y muchos lectores de pantalla no lo
    tratan igual que un label).
    """
    if campo.get("aria-label") or campo.get("aria-labelledby"):
        return True
    id_campo = campo.get("id")
    if id_campo and soup.find("label", attrs={"for": id_campo}):
        return True
    # <input> envuelto directamente dentro de un <label> (patrón válido
    # sin usar "for"/"id").
    return campo.find_parent("label") is not None


def comprobar_accesibilidad(pagina: dict) -> dict:
    """Función síncrona: solo analiza el HTML ya descargado, sin red propia."""
    if not pagina["ok"]:
        return _resultado(
            estado="rojo",
            prioridad="alta",
            detalle=f"No se ha podido acceder a la web para revisar accesibilidad ({pagina['error']}).",
        )

    soup = BeautifulSoup(pagina["html"], "html.parser")
    problemas = []

    etiqueta_html = soup.find("html")
    tiene_lang = bool(etiqueta_html and etiqueta_html.get("lang", "").strip())
    if not tiene_lang:
        problemas.append("la etiqueta <html> no declara el idioma (atributo lang)")

    campos = [
        campo
        for campo in soup.find_all("input")
        if campo.get("type", "text").lower() in TIPOS_INPUT_QUE_NECESITAN_ETIQUETA
    ] + soup.find_all("textarea")

    campos_sin_etiqueta = [c for c in campos if not _tiene_etiqueta_asociada(c, soup)]
    if campos_sin_etiqueta:
        problemas.append(
            f"{len(campos_sin_etiqueta)} de {len(campos)} campos de formulario no tienen ninguna etiqueta asociada"
        )

    datos = {
        "tiene_lang": tiene_lang,
        "total_campos_formulario": len(campos),
        "campos_sin_etiqueta": len(campos_sin_etiqueta),
    }

    return _evaluar(problemas, datos)


def _evaluar(problemas: list[str], datos: dict) -> dict:
    if not problemas:
        return _resultado(
            estado="verde",
            prioridad="baja",
            detalle="No se detectan problemas básicos de accesibilidad (idioma declarado, formularios etiquetados).",
            datos=datos,
        )

    return _resultado(
        estado="ambar",
        prioridad="media",
        detalle="Accesibilidad mejorable: " + "; ".join(problemas) + ".",
        datos=datos,
    )


def _resultado(estado: str, prioridad: str, detalle: str, datos: dict | None = None) -> dict:
    """Mismo formato común que usa el resto de checks (ver ssl_check.py)."""
    return {
        "check": "accesibilidad",
        "estado": estado,
        "prioridad": prioridad,
        "detalle": detalle,
        "datos": datos or {},
    }
