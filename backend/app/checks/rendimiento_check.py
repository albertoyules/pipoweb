"""
Check de rendimiento con Google PageSpeed Insights.

Categoría: Rendimiento y experiencia (ver PIPO_PLANNING.md, sección 2).
Naturaleza: 100% pasivo (verde) y, de hecho, ni siquiera lo hacemos
nosotros: la petición HTTP la hace Google, que carga la web con su
propio motor (Lighthouse, el mismo que usa Chrome DevTools) y nos
devuelve los resultados via API. No tocamos el servidor del cliente
en ningún momento.

Qué comprobamos, en MÓVIL y en ORDENADOR por separado (como la propia
página de PageSpeed Insights):
- Las 4 categorías de Lighthouse: rendimiento, accesibilidad, prácticas
  recomendadas y SEO.
- Los Core Web Vitals más relevantes: FCP, LCP, CLS, TBT y Speed Index.

No es todo lo que muestra la web oficial de PageSpeed (esa tiene
auditorías detalladas por cada punto), pero sí bastante más que un
único número — lo justo para que un dueño de negocio entienda dónde
está el problema sin agobiarse.

Nota: usamos datos de laboratorio (Lighthouse), no datos de campo
(CrUX, usuarios reales), porque la mayoría de webs de pymes no tienen
tráfico suficiente para que Google recoja datos de campo. Es la misma
limitación que tiene cualquier herramienta de este tipo.
"""

import asyncio

import httpx

from app.config import GOOGLE_PAGESPEED_API_KEY

URL_API = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"

# Los mismos umbrales que usa Google para sus categorías de Lighthouse
# (0-100): a partir de 90 es "bueno", por debajo de 50 es "pobre".
UMBRAL_VERDE = 90
UMBRAL_AMBAR = 50

# Categorías que pedimos en cada auditoría. "best-practices" es el
# nombre real de la API (con guion), lo traducimos al presentarlo.
CATEGORIAS = ["performance", "accessibility", "best-practices", "seo"]


async def comprobar_rendimiento(dominio: str, timeout: float = 45.0) -> dict:
    """
    Pide a PageSpeed que audite la web dos veces — una en modo 'mobile'
    y otra en 'desktop' — en paralelo, para no duplicar el tiempo de
    espera. El semáforo (verde/ámbar/rojo) se decide por el rendimiento
    en móvil, porque es donde entra la mayoría del tráfico de una pyme;
    los datos de ordenador se muestran igualmente, solo que no mandan
    en el color.
    """
    if not GOOGLE_PAGESPEED_API_KEY:
        return _resultado(
            estado="ambar",
            prioridad="baja",
            detalle="Pipo no tiene configurada la clave de PageSpeed todavía; este check no se ha podido ejecutar.",
        )

    try:
        movil, ordenador = await asyncio.gather(
            _auditar(dominio, "mobile", timeout),
            _auditar(dominio, "desktop", timeout),
        )
    # Que la API de PageSpeed de Google falle o no conteste es un
    # problema NUESTRO, no de la web analizada. Ponerlo en rojo le
    # restaba nota a un negocio por una avería de Google.
    except httpx.RequestError as error:
        return _resultado(
            estado="sin_datos",
            prioridad="baja",
            detalle=f"No hemos podido medir la velocidad ({error}). No cuenta para la nota.",
        )
    except _ErrorPageSpeed as error:
        return _resultado(
            estado="sin_datos",
            prioridad="baja",
            detalle=f"No hemos podido medir la velocidad: {error} No cuenta para la nota.",
        )

    puntuacion = movil["rendimiento"]
    datos = {"mobile": movil, "desktop": ordenador}

    if puntuacion >= UMBRAL_VERDE:
        return _resultado(
            estado="verde",
            prioridad="baja",
            detalle=f"Buen rendimiento en móvil (puntuación {puntuacion}/100). LCP: {movil['lcp']}, CLS: {movil['cls']}.",
            datos=datos,
        )

    if puntuacion >= UMBRAL_AMBAR:
        return _resultado(
            estado="ambar",
            prioridad="media",
            detalle=f"Rendimiento mejorable en móvil (puntuación {puntuacion}/100). LCP: {movil['lcp']}, CLS: {movil['cls']}.",
            datos=datos,
        )

    return _resultado(
        estado="rojo",
        prioridad="alta",
        detalle=f"Rendimiento pobre en móvil (puntuación {puntuacion}/100). LCP: {movil['lcp']}, CLS: {movil['cls']}. Esto probablemente afecta a las visitas y al posicionamiento en Google.",
        datos=datos,
    )


class _ErrorPageSpeed(Exception):
    """Fallo al pedir o interpretar la respuesta de PageSpeed para una estrategia."""


async def _auditar(dominio: str, estrategia: str, timeout: float) -> dict:
    """
    Pide una auditoría completa (4 categorías) para 'mobile' o
    'desktop', y devuelve solo los números que vamos a mostrar.
    """
    parametros = [
        ("url", f"https://{dominio}"),
        ("key", GOOGLE_PAGESPEED_API_KEY),
        ("strategy", estrategia),
        *[("category", categoria) for categoria in CATEGORIAS],
    ]

    async with httpx.AsyncClient(timeout=timeout) as cliente:
        respuesta = await cliente.get(URL_API, params=parametros)

    if respuesta.status_code != 200:
        raise _ErrorPageSpeed(f"Google PageSpeed no ha podido analizar la web (código {respuesta.status_code}).")

    cuerpo = respuesta.json()
    resultado_lighthouse = cuerpo["lighthouseResult"]
    categorias = resultado_lighthouse["categories"]
    auditorias = resultado_lighthouse["audits"]

    def puntuacion_categoria(nombre: str) -> int | None:
        # No todas las categorías siempre vienen (a veces Google omite
        # alguna); mejor devolver None que reventar el resto del check.
        dato = categorias.get(nombre)
        return round(dato["score"] * 100) if dato and dato.get("score") is not None else None

    def valor_metrica(id_auditoria: str) -> str | None:
        dato = auditorias.get(id_auditoria)
        return dato["displayValue"] if dato else None

    return {
        "rendimiento": puntuacion_categoria("performance"),
        "accesibilidad": puntuacion_categoria("accessibility"),
        "practicas": puntuacion_categoria("best-practices"),
        "seo": puntuacion_categoria("seo"),
        "fcp": valor_metrica("first-contentful-paint"),
        "lcp": valor_metrica("largest-contentful-paint"),
        "cls": valor_metrica("cumulative-layout-shift"),
        "tbt": valor_metrica("total-blocking-time"),
        "speed_index": valor_metrica("speed-index"),
    }


def _resultado(estado: str, prioridad: str, detalle: str, datos: dict | None = None) -> dict:
    """Mismo formato común que usa el resto de checks (ver ssl_check.py)."""
    return {
        "check": "rendimiento",
        "estado": estado,
        "prioridad": prioridad,
        "detalle": detalle,
        "datos": datos or {},
    }
