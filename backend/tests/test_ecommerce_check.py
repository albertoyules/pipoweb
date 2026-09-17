"""
Tests de ecommerce_check.py, el check condicional de tienda online (ver
app/checks/perfil_sitio.py — solo se lanza si tiene_checkout=True).

No tocan la red: se le pasa el HTML ya "descargado", igual que hace
pagina.py en el escaneo real.

Foco especial en no acusar a un negocio pequeño que cobra por
transferencia o contra reembolso de "no tener pasarela de pago" — es
justo el caso real que hizo ampliar este check el 17 sep 2026.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.checks.ecommerce_check import comprobar_ecommerce  # noqa: E402


def pagina(html: str, url: str = "https://tienda.es") -> dict:
    """El mismo formato que devuelve obtener_pagina()."""
    return {"ok": True, "error": None, "url": url, "html": html, "headers": {}}


HTML_BASE = """
<!DOCTYPE html><html lang="es"><head><title>Tienda</title></head><body>
<a href="/condiciones-de-venta">Condiciones de venta</a>
<script type="application/ld+json">{{"@type":"Product","name":"Producto"}}</script>
{extra}
</body></html>
"""


def test_reconoce_redsys_por_su_nombre_historico_sermepa():
    """
    Redsys (antes Sermepa) es el TPV que hay debajo de la mayoría de
    bancos españoles (CaixaBank, BBVA, Santander, Sabadell...). Algunas
    integraciones antiguas todavía cargan el dominio con el nombre
    viejo, sis.sermepa.es, no el nuevo.
    """
    html = HTML_BASE.format(extra='<script src="https://sis.sermepa.es/sis/realizarPago"></script>')
    resultado = comprobar_ecommerce(pagina(html))
    assert resultado["datos"]["pasarela_detectada"] == "Redsys (Sermepa)"


def test_reconoce_paycomet_y_addon_payments():
    """Pasarelas españolas habituales que faltaban en la lista original."""
    html = HTML_BASE.format(extra='<script src="https://api.paycomet.com/gateway/rest"></script>')
    resultado = comprobar_ecommerce(pagina(html))
    assert resultado["datos"]["pasarela_detectada"] == "PayComet"

    html2 = HTML_BASE.format(extra='<iframe src="https://pay.addonpayments.com/checkout"></iframe>')
    resultado2 = comprobar_ecommerce(pagina(html2))
    assert resultado2["datos"]["pasarela_detectada"] == "Addon Payments"


def test_pago_por_transferencia_no_es_un_fallo():
    """
    Un negocio pequeño o antiguo que cobra por transferencia bancaria
    no tiene ningún script de pasarela que dejar ver — eso no significa
    que le falte una forma de pagar, solo que no usa una digital. No
    debe tratarse igual que una tienda que no dice cómo se paga.
    """
    html = HTML_BASE.format(extra="<p>El pago se realiza por transferencia bancaria tras confirmar el pedido.</p>")
    resultado = comprobar_ecommerce(pagina(html))

    assert resultado["datos"]["pasarela_detectada"] is None
    assert resultado["datos"]["tiene_pago_manual"] is True
    # No debe quejarse de que falte una forma de pago — sí se detectó
    # una (el pago manual), aunque no sea una pasarela digital. El
    # único faltante posible aquí es la ausencia de datos de producto.
    assert "falta" not in resultado["detalle"].lower()


def test_contra_reembolso_tambien_cuenta_como_forma_de_pago():
    html = HTML_BASE.format(extra="<p>Aceptamos pago contra reembolso en toda España.</p>")
    resultado = comprobar_ecommerce(pagina(html))
    assert resultado["datos"]["tiene_pago_manual"] is True


def test_sin_pasarela_ni_pago_manual_avisa_pero_no_acusa_con_dureza():
    """
    Cuando de verdad no se detecta ninguna forma de pago (ni pasarela
    ni texto de pago manual), el aviso debe seguir siendo ámbar
    informativo — Pipo no puede saber si es un fallo real o solo que
    la web no lo explica con las palabras que busca el check.
    """
    html = HTML_BASE.format(extra="")
    resultado = comprobar_ecommerce(pagina(html))

    assert resultado["estado"] == "ambar"
    assert "forma de pago" in resultado["detalle"]
    # El texto debe explicar el motivo, no sonar a acusación seca.
    assert "no puede saber cómo cobras" in resultado["detalle"]


def test_stripe_y_paypal_siguen_reconociendose():
    """No se ha roto la detección original al ampliar la lista."""
    html = HTML_BASE.format(extra='<script src="https://js.stripe.com/v3/"></script>')
    resultado = comprobar_ecommerce(pagina(html))
    assert resultado["datos"]["pasarela_detectada"] == "Stripe"
