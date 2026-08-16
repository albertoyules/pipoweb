"""
Tests de la validación del dominio de entrada.

Esta es la puerta de Pipo: lo que pase de aquí acaba en peticiones que
salen del servidor. Que rechace direcciones internas no es una manía —
sin ello, cualquiera podía usar Pipo para husmear la red del hosting
desde dentro (comprobado en producción el 13 ago 2026).
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.seguridad import (  # noqa: E402
    DominioNoValido,
    dominio_raiz,
    normalizar_dominio,
    variante_www,
)


@pytest.mark.parametrize(
    "entrada,esperado",
    [
        ("ejemplo.es", "ejemplo.es"),
        ("  EJEMPLO.ES  ", "ejemplo.es"),
        ("https://ejemplo.es", "ejemplo.es"),
        ("http://www.ejemplo.es/contacto?utm=1", "www.ejemplo.es"),
        ("ejemplo.es/", "ejemplo.es"),
        ("ejemplo.es.", "ejemplo.es"),
        ("https://ejemplo.es#seccion", "ejemplo.es"),
        ("mi-negocio.com", "mi-negocio.com"),
        ("tienda.ejemplo.co.uk", "tienda.ejemplo.co.uk"),
    ],
)
def test_dominios_que_se_aceptan_y_como_quedan(entrada, esperado):
    assert normalizar_dominio(entrada) == esperado


def test_los_dominios_con_enes_se_convierten_a_su_forma_tecnica():
    assert normalizar_dominio("peñalara.es") == "xn--pealara-5za.es"


@pytest.mark.parametrize(
    "entrada",
    [
        "",
        "   ",
        "localhost",
        "127.0.0.1",
        "169.254.169.254",          # dirección de metadatos de los hostings
        "10.0.0.5",
        "[::1]",
        "ejemplo.es:8080",          # un puerto ya no es "mirar la web"
        "servidor.local",
        "algo.internal",
        "sin-punto",
        "http://",
        "-mal.com",
    ],
)
def test_dominios_que_se_rechazan(entrada):
    with pytest.raises(DominioNoValido):
        normalizar_dominio(entrada)


def test_un_email_pegado_por_error_se_queda_con_el_dominio():
    """Alguien pega su email en la casilla; mejor entenderlo que fallar."""
    assert normalizar_dominio("paco@tallerpaco.es") == "tallerpaco.es"


# --- www: dominio_raiz y variante_www (16 ago 2026) -------------------
#
# SPF, DMARC, CAA, DNSSEC y WHOIS solo existen en el dominio registrado.
# Preguntarlos en "www." devuelve silencio, y Pipo tomaba ese silencio
# por una acusación: www.mchomeinmobiliaria.com salía con dns en ROJO
# teniendo SPF y DMARC (p=quarantine) perfectamente puestos.


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("www.tallerpaco.es", "tallerpaco.es"),
        ("tallerpaco.es", "tallerpaco.es"),
        # Un subdominio que NO es www se respeta: ahí el usuario está
        # pidiendo expresamente esa dirección, no la raíz.
        ("tienda.tallerpaco.es", "tienda.tallerpaco.es"),
        # "www" en medio no es el prefijo, no se toca.
        ("mi-www.tallerpaco.es", "mi-www.tallerpaco.es"),
    ],
)
def test_dominio_raiz_solo_quita_el_www_de_delante(entrada, esperado):
    assert dominio_raiz(entrada) == esperado


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("tallerpaco.es", "www.tallerpaco.es"),
        ("www.tallerpaco.es", "tallerpaco.es"),
    ],
)
def test_variante_www_alterna_las_dos_formas(entrada, esperado):
    assert variante_www(entrada) == esperado
