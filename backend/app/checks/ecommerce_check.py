"""
Check condicional: seguridad y cumplimiento específicos de una tienda
online. Solo se ejecuta si perfil_sitio.py detecta tiene_checkout=True
(ver scanner.py) — no tiene sentido preguntar esto a una landing sin
carrito.

Categoría: seguridad de e-commerce (ver app/puntuacion.py, FAMILIAS).
Naturaleza: 100% pasivo (verde). Todo lo que se mira es HTML/cabeceras
públicas de la home ya descargada, más una petición ligera a la propia
página (ya se tiene, no se pide otra vez) — no se navega el checkout
de verdad ni se intenta comprar nada, eso ya sería activo.

Qué comprobamos, y por qué es específico de tiendas:
- Toda la web sirve HTTPS de verdad (ssl_check.py ya lo comprueba en
  general; aquí se repite la conclusión con lenguaje de "esto es
  donde tus clientes pagan", que es lo que hace que el hallazgo
  importe de verdad a un dueño de tienda).
- Se reconoce una pasarela de pago conocida (Stripe, Redsys, PayPal,
  Shopify Payments...) en vez de algo no identificable: un dueño de
  negocio no puede juzgar la seguridad de una pasarela que no conoce,
  pero sí puede preguntar por una que no reconocemos.
- Condiciones de venta / política de devoluciones enlazadas: en
  España son obligatorias en e-commerce (art. 97 y 103 del Real
  Decreto Legislativo 1/2007, TR de la Ley General para la Defensa de
  Consumidores y Usuarios) y son DISTINTAS del aviso legal genérico
  que ya comprueba privacidad_check.py — una tienda puede tener aviso
  legal y no tener condiciones de venta.
- Datos estructurados de producto (schema.org/Product): sin esto,
  Google no puede mostrar precio/disponibilidad en el buscador. Es
  más específico que "tiene datos estructurados" (lo que ya mira
  seo_check.py): aquí se comprueba el @type concreto.
"""

import re

from bs4 import BeautifulSoup

PASARELAS_CONOCIDAS = {
    "js.stripe.com": "Stripe",
    "checkout.stripe.com": "Stripe",
    "sis.redsys.es": "Redsys",
    "sis-t.redsys.es": "Redsys (entorno de pruebas)",
    "paypal.com/sdk": "PayPal",
    "paypalobjects.com": "PayPal",
    "checkout.shopify.com": "Shopify Payments",
    "js.squareup.com": "Square",
    "mercadopago.com": "Mercado Pago",
    "checkout.com": "Checkout.com",
}

PALABRAS_CONDICIONES_VENTA = (
    "condiciones de venta",
    "condiciones generales de contratación",
    "política de devoluciones",
    "politica de devoluciones",
    "derecho de desistimiento",
    "terms of sale",
    "return policy",
)


def comprobar_ecommerce(pagina: dict) -> dict:
    """
    Recibe la home ya descargada (ver pagina.py) para no volver a
    pedirla. Solo se llama cuando perfil_sitio.py ya ha detectado
    tiene_checkout=True — scanner.py decide si esta función se lanza.
    """
    if not pagina["ok"]:
        return _resultado(
            estado="sin_datos",
            prioridad="baja",
            detalle=f"No hemos podido leer la web para revisar la seguridad de la tienda ({pagina['error']}). No cuenta para la nota.",
        )

    html = pagina["html"]
    minusculas = html.lower()
    soup = BeautifulSoup(html, "html.parser")

    sirve_https = pagina["url"].startswith("https://")

    pasarela_detectada = next(
        (nombre for fragmento, nombre in PASARELAS_CONOCIDAS.items() if fragmento in minusculas),
        None,
    )

    texto_enlaces = " ".join(
        f"{enlace.get_text(' ', strip=True)} {enlace.get('href', '')}".lower()
        for enlace in soup.find_all("a")
    )
    tiene_condiciones_venta = any(p in texto_enlaces for p in PALABRAS_CONDICIONES_VENTA)

    tiene_datos_producto = _tiene_schema_product(soup)

    datos = {
        "sirve_https": sirve_https,
        "pasarela_detectada": pasarela_detectada,
        "tiene_condiciones_venta": tiene_condiciones_venta,
        "tiene_datos_producto": tiene_datos_producto,
    }

    return _evaluar(datos)


def _tiene_schema_product(soup: BeautifulSoup) -> bool:
    """
    Busca un bloque JSON-LD cuyo @type sea "Product" (o lo incluya, si
    es una lista de tipos). No se usa json.loads estricto porque
    bastantes webs generan este bloque con errores menores de sintaxis
    que los navegadores y Google toleran igual — una comprobación de
    texto es más tolerante que un parseo exigente para este propósito.
    """
    for bloque in soup.find_all("script", type="application/ld+json"):
        contenido = bloque.string or ""
        if re.search(r'"@type"\s*:\s*"Product"', contenido) or re.search(
            r'"@type"\s*:\s*\[[^\]]*"Product"', contenido
        ):
            return True
    return False


def _evaluar(datos: dict) -> dict:
    if not datos["sirve_https"]:
        return _resultado(
            estado="rojo",
            prioridad="alta",
            detalle=(
                "La tienda no está sirviendo la página por HTTPS. En una web con carrito de compra, "
                "esto significa que los datos que introduce el cliente pueden viajar sin cifrar."
            ),
            datos=datos,
        )

    faltantes = []
    if not datos["tiene_condiciones_venta"]:
        faltantes.append("condiciones de venta o política de devoluciones")
    if datos["pasarela_detectada"] is None:
        faltantes.append("una pasarela de pago reconocible")

    if faltantes:
        return _resultado(
            estado="ambar",
            prioridad="media",
            detalle=f"A la tienda le falta: {', '.join(faltantes)}.",
            datos=datos,
        )

    if not datos["tiene_datos_producto"]:
        return _resultado(
            estado="ambar",
            prioridad="baja",
            detalle=(
                "No se detectan datos estructurados de producto (schema.org/Product): sin ellos, "
                "Google no puede mostrar precio o disponibilidad directamente en el buscador."
            ),
            datos=datos,
        )

    return _resultado(
        estado="verde",
        prioridad="baja",
        detalle=(
            f"La tienda sirve HTTPS, tiene condiciones de venta enlazadas, usa una pasarela "
            f"reconocible ({datos['pasarela_detectada']}) y publica datos estructurados de producto."
        ),
        datos=datos,
    )


def _resultado(estado: str, prioridad: str, detalle: str, datos: dict | None = None) -> dict:
    """Mismo formato común que usa el resto de checks (ver ssl_check.py)."""
    return {
        "check": "ecommerce",
        "estado": estado,
        "prioridad": prioridad,
        "detalle": detalle,
        "datos": datos or {},
    }
