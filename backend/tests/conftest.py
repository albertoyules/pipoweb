"""
Deja los tests sin red.

El docstring de test_checks.py decía desde el principio "no tocan la
red", y era mentira a medias: comprobar_seo pedía de verdad
ejemplo.es/robots.txt y ejemplo.es/sitemap.xml, y comprobar_experiencia
pedía de verdad www.ejemplo.es. Medido el 20 ago 2026: los 69 tests
tardaban 83 segundos, 18 de ellos un solo test de SEO esperando
timeouts.

Eso no es solo lentitud. Significaba que la suite dependía de que
hubiera internet, de que ese dominio siguiera comportándose igual, y de
que nadie manipulara la petición por el camino — cosa que sabemos que
pasa en la red de casa de Alberto. Un test que puede fallar por el
router no prueba nada del código.

Aquí se sustituyen esas dos llamadas por respuestas fijas. Un test que
quiera otra cosa solo tiene que volver a parchearlas él mismo.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.checks import experiencia_check, pagina, seo_check, tecnologia_check  # noqa: E402


@pytest.fixture(autouse=True)
def sin_red(monkeypatch):
    """Ningún test toca la red salvo que lo pida expresamente."""

    async def no_existe(url_base, ruta):
        return False

    async def www_desconocido(dominio):
        return None

    async def sin_readme(url_base):
        return None

    async def ultima_version_fija():
        return tecnologia_check.ULTIMA_VERSION_WP_RESPALDO

    monkeypatch.setattr(seo_check, "_existe", no_existe)
    monkeypatch.setattr(experiencia_check, "_responde_variante_www", www_desconocido)
    monkeypatch.setattr(tecnologia_check, "_version_wordpress_desde_readme", sin_readme)
    monkeypatch.setattr(tecnologia_check, "_ultima_version_estable_wordpress", ultima_version_fija)
    # Sin esto, cualquier test que mockee un 403/429/503 (obtener_pagina
    # reintenta esos códigos, ver pagina.py) espera de verdad 1.5s reales
    # por cada reintento — un test no debe tardar lo mismo que la red.
    monkeypatch.setattr(pagina, "ESPERA_REINTENTO_SEGUNDOS", 0)
