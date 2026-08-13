"""
Tests de los checks que leen HTML, con páginas de mentira escritas aquí
mismo. No tocan la red: le damos a cada check el HTML ya "descargado",
igual que hace pagina.py en el escaneo real.

Lo que se prueba a propósito son los casos donde Pipo puede EQUIVOCARSE
acusando de más — que es lo que le costaría credibilidad delante de un
cliente: decir que no hay banner de cookies cuando sí lo hay, o dar por
malo el SEO de una web que se dibuja con JavaScript.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.checks.accesibilidad_check import comprobar_accesibilidad  # noqa: E402
from app.checks.experiencia_check import comprobar_experiencia  # noqa: E402
from app.checks.pagina import parece_dibujada_con_javascript  # noqa: E402
from app.checks.privacidad_check import comprobar_privacidad  # noqa: E402
from app.checks.seo_check import comprobar_seo  # noqa: E402


def pagina(html: str, url: str = "https://ejemplo.es") -> dict:
    """El mismo formato que devuelve obtener_pagina()."""
    return {"ok": True, "error": None, "url": url, "html": html, "headers": {}}


PAGINA_COMPLETA = """
<!DOCTYPE html><html lang="es"><head>
<title>Taller Paco — mecánica rápida en Málaga</title>
<meta name="description" content="Taller mecánico en Málaga con más de veinte años de experiencia: revisiones, neumáticos y pre-ITV sin cita previa.">
<meta property="og:title" content="Taller Paco"><meta property="og:image" content="/og.png">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="/favicon.ico">
<script type="application/ld+json">{"@type":"AutoRepair"}</script>
</head><body>
<h1>Taller Paco</h1>
<p>Somos un taller de barrio en Málaga desde 1998. Hacemos revisiones, cambio de neumáticos,
pre-ITV y diagnosis. Ven sin cita previa de lunes a viernes.</p>
<a href="tel:+34600111222">Llámanos</a>
<a href="/aviso-legal">Aviso legal</a>
<a href="/privacidad">Política de privacidad</a>
<a href="/cookies">Política de cookies</a>
<form action="https://ejemplo.es/contacto"><label for="n">Nombre</label><input id="n" type="text"></form>
</body></html>
"""

# Web moderna típica: el HTML llega vacío y el contenido lo pinta el
# navegador. Pipo no ejecuta JavaScript, así que aquí NO puede juzgar.
PAGINA_JAVASCRIPT = """
<!DOCTYPE html><html><head><title>Cargando</title></head>
<body><div id="root"></div><script src="/app.js"></script></body></html>
"""


# --- Webs dibujadas con JavaScript ----------------------------------

def test_se_reconoce_una_web_dibujada_con_javascript():
    assert parece_dibujada_con_javascript(PAGINA_JAVASCRIPT) is True
    assert parece_dibujada_con_javascript(PAGINA_COMPLETA) is False


def test_seo_no_acusa_a_una_web_de_javascript():
    resultado = asyncio.run(comprobar_seo(pagina(PAGINA_JAVASCRIPT)))
    assert resultado["estado"] == "ambar"
    assert resultado["datos"]["verificable_sin_javascript"] is False
    assert "javascript" in resultado["detalle"].lower()


def test_privacidad_no_acusa_a_una_web_de_javascript():
    resultado = comprobar_privacidad(pagina(PAGINA_JAVASCRIPT))
    assert resultado["estado"] == "ambar"
    assert resultado["datos"]["verificable_sin_javascript"] is False


def test_accesibilidad_no_acusa_a_una_web_de_javascript():
    resultado = comprobar_accesibilidad(pagina(PAGINA_JAVASCRIPT))
    assert resultado["estado"] == "ambar"


# --- Privacidad / cookies -------------------------------------------

def test_se_detecta_el_gestor_de_cookies_aunque_el_banner_lo_pinte_javascript():
    """
    El fallo que más credibilidad costaría: casi ningún banner de
    cookies real está escrito en el HTML, lo inyecta un gestor con
    JavaScript. Reconocer su script evita decir "no tienes banner" a
    una web que sí cumple.
    """
    html = PAGINA_COMPLETA.replace(
        "</head>", '<script src="https://consent.cookiebot.com/uc.js"></script></head>'
    ).replace('<a href="tel:+34600111222">Llámanos</a>',
              '<a href="tel:+34600111222">Llámanos</a><script src="https://www.googletagmanager.com/gtm.js"></script>')

    resultado = comprobar_privacidad(pagina(html))
    assert resultado["datos"]["gestor_de_cookies"] == "Cookiebot"
    assert resultado["datos"]["indicio_banner_cookies"] is True
    assert resultado["estado"] == "verde"


def test_trackers_sin_banner_y_sin_paginas_legales_es_rojo():
    html = PAGINA_COMPLETA.replace('<a href="/aviso-legal">Aviso legal</a>', "") \
                          .replace('<a href="/privacidad">Política de privacidad</a>', "") \
                          .replace('<a href="/cookies">Política de cookies</a>', "") \
                          .replace("</body>", '<script src="https://www.google-analytics.com/ga.js"></script></body>')
    resultado = comprobar_privacidad(pagina(html))
    assert resultado["estado"] == "rojo"
    assert "Google Analytics" in resultado["datos"]["trackers_detectados"]


def test_una_web_con_sus_paginas_legales_esta_en_verde():
    assert comprobar_privacidad(pagina(PAGINA_COMPLETA))["estado"] == "verde"


# --- SEO --------------------------------------------------------------

def test_un_title_largo_de_mas_no_es_critico():
    """El caso real que puso 'crítico' a una web por 3 caracteres."""
    html = PAGINA_COMPLETA.replace(
        "<title>Taller Paco — mecánica rápida en Málaga</title>",
        "<title>Taller Paco — mecánica rápida y neumáticos en Málaga capital desde 1998</title>",
    )
    resultado = asyncio.run(comprobar_seo(pagina(html)))
    assert resultado["estado"] == "ambar"


def test_sin_title_ni_description_si_es_critico():
    html = PAGINA_COMPLETA.replace("<title>Taller Paco — mecánica rápida en Málaga</title>", "")
    html = html.replace(html[html.find('<meta name="description"'):html.find('">', html.find('<meta name="description"')) + 2], "")
    resultado = asyncio.run(comprobar_seo(pagina(html)))
    assert resultado["estado"] == "rojo"


# --- Experiencia de cliente ------------------------------------------

def test_una_web_sin_viewport_pierde_clientes_en_el_movil():
    html = PAGINA_COMPLETA.replace('<meta name="viewport" content="width=device-width, initial-scale=1">', "")
    resultado = asyncio.run(comprobar_experiencia(pagina(html), "ejemplo.es"))
    assert resultado["estado"] == "rojo"
    assert resultado["datos"]["adaptada_a_movil"] is False


def test_un_formulario_sin_cifrar_es_grave():
    html = PAGINA_COMPLETA.replace('action="https://ejemplo.es/contacto"', 'action="http://ejemplo.es/contacto"')
    resultado = asyncio.run(comprobar_experiencia(pagina(html), "ejemplo.es"))
    assert resultado["estado"] == "rojo"
    assert resultado["datos"]["formularios_sin_cifrar"] == 1


def test_se_detecta_el_telefono_pulsable():
    resultado = asyncio.run(comprobar_experiencia(pagina(PAGINA_COMPLETA), "ejemplo.es"))
    assert resultado["datos"]["telefono_pulsable"] is True
    assert resultado["datos"]["tiene_favicon"] is True
