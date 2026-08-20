"""
Tests de los arreglos del 20 ago 2026.

Todos son de la misma familia, la que más veces ha mordido a este
proyecto: Pipo dando por malo algo que no ha podido comprobar, o
reprochando por un fallo nuestro. Cada test aquí corresponde a un fallo
que estaba en el código y que se reprodujo antes de tocarlo.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.checks import experiencia_check, rendimiento_check, seo_check  # noqa: E402
from app.checks.pagina import raiz_del_sitio  # noqa: E402
from app.checks.tecnologia_check import comprobar_tecnologia  # noqa: E402
from app.ia.interpretar import _hallazgos_verificados  # noqa: E402
from app.notificaciones.mensajes import _checks_a_mejorar  # noqa: E402
from app.puntuacion import calcular_precio_arreglo  # noqa: E402


# Se guarda antes de que el fixture de conftest.py lo sustituya.
_EXISTE_REAL = seo_check._existe


def pagina(html: str, url: str = "https://ejemplo.es") -> dict:
    return {"ok": True, "error": None, "url": url, "html": html, "headers": {}}


# --------------------------------------------------------------------
# robots.txt y sitemap.xml se buscaban sobre la URL final, con su path
# --------------------------------------------------------------------

def test_la_raiz_del_sitio_ignora_el_subdirectorio_de_idioma():
    assert raiz_del_sitio("https://ejemplo.es/es/") == "https://ejemplo.es"
    assert raiz_del_sitio("https://ejemplo.es") == "https://ejemplo.es"
    assert raiz_del_sitio("https://www.ejemplo.es/es/inicio?a=1") == "https://www.ejemplo.es"


def test_robots_se_pide_en_la_raiz_aunque_la_home_redirija_a_un_idioma(monkeypatch):
    # conftest.py deja _existe apagado para todos los tests; este necesita
    # el de verdad, porque el arreglo que se prueba vive dentro de él.
    monkeypatch.setattr(seo_check, "_existe", _EXISTE_REAL)
    """
    Una web multiidioma manda la home a /es/. Pipo pedía /es/robots.txt,
    no lo encontraba, y acusaba de no tener robots ni sitemap a quien
    tiene los dos.
    """
    pedidas = []

    # Se espía la petición HTTP de verdad, no _existe: el arreglo vive
    # DENTRO de _existe, así que parchear _existe no probaría nada.
    class ClienteEspia:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, url):
            pedidas.append(url)

            class Respuesta:
                status_code = 200

            return Respuesta()

    monkeypatch.setattr(seo_check.httpx, "AsyncClient", lambda **k: ClienteEspia())
    html = "<html lang='es'><head><title>Hola que tal</title></head><body><h1>x</h1></body></html>"
    asyncio.run(seo_check.comprobar_seo(pagina(html, url="https://ejemplo.es/es/")))

    assert pedidas == ["https://ejemplo.es/robots.txt", "https://ejemplo.es/sitemap.xml"]


# --------------------------------------------------------------------
# el aviso del www salía también cuando el fallo de red era nuestro
# --------------------------------------------------------------------

def test_un_fallo_de_red_nuestro_no_se_convierte_en_un_reproche(monkeypatch):
    """
    El docstring prometía None desde el principio; el código devolvía
    False ante cualquier error de red y eso acababa en "la otra forma de
    escribir la dirección no responde".
    """
    import httpx

    class ClienteQueFalla:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, url): raise httpx.ConnectTimeout("timeout")

    monkeypatch.setattr(httpx, "AsyncClient", lambda **k: ClienteQueFalla())
    assert asyncio.run(experiencia_check._responde_variante_www("ejemplo.es")) is None


def test_no_se_pregunta_por_el_www_de_un_subdominio():
    """Nadie escribe www.tienda.ejemplo.es, y www.ejemplo.es es otra web."""
    assert asyncio.run(experiencia_check._responde_variante_www("tienda.ejemplo.es")) is None


def test_sin_saber_si_el_www_responde_no_se_menciona(monkeypatch):
    async def desconocido(dominio): return None
    monkeypatch.setattr(experiencia_check, "_responde_variante_www", desconocido)
    html = """<html lang="es"><head><title>Taller</title>
    <meta name="viewport" content="width=device-width"><link rel="icon" href="/f.ico">
    </head><body><h1>Taller</h1><a href="tel:+34600000000">Llamar</a></body></html>"""
    resultado = asyncio.run(experiencia_check.comprobar_experiencia(pagina(html), "ejemplo.es"))
    assert "'www.'" not in resultado["detalle"]
    assert resultado["datos"]["variante_www_responde"] is None


# --------------------------------------------------------------------
# el botón de velocidad reventaba si Google no mandaba la nota
# --------------------------------------------------------------------

def test_si_google_no_da_la_nota_de_velocidad_no_revienta(monkeypatch):
    async def auditoria_sin_nota(dominio, estrategia, timeout):
        return {"rendimiento": None, "accesibilidad": 90, "practicas": 90, "seo": 90,
                "fcp": None, "lcp": None, "cls": None, "tbt": None, "speed_index": None}

    monkeypatch.setattr(rendimiento_check, "_auditar", auditoria_sin_nota)
    monkeypatch.setattr(rendimiento_check, "GOOGLE_PAGESPEED_API_KEY", "clave-de-prueba")
    resultado = asyncio.run(rendimiento_check.comprobar_rendimiento("ejemplo.es"))
    assert resultado["estado"] == "sin_datos"


def test_que_nos_falte_la_clave_de_pagespeed_no_le_baja_la_nota_a_nadie(monkeypatch):
    monkeypatch.setattr(rendimiento_check, "GOOGLE_PAGESPEED_API_KEY", None)
    resultado = asyncio.run(rendimiento_check.comprobar_rendimiento("ejemplo.es"))
    assert resultado["estado"] == "sin_datos"


# --------------------------------------------------------------------
# "sin_datos" no es un problema: ni encarece, ni entra en los deberes
# --------------------------------------------------------------------

def _check(nombre, estado, prioridad):
    return {"check": nombre, "estado": estado, "prioridad": prioridad, "detalle": f"detalle de {nombre}", "datos": {}}


def test_lo_que_no_se_pudo_comprobar_no_encarece_el_presupuesto():
    solo_verdes = [_check("ssl", "verde", "baja")]
    con_sin_datos = solo_verdes + [_check("whois", "sin_datos", "baja") for _ in range(6)]
    assert calcular_precio_arreglo(con_sin_datos) == calcular_precio_arreglo(solo_verdes)


def test_el_email_al_cliente_no_lista_lo_que_no_se_pudo_comprobar():
    checks = [
        _check("ssl", "verde", "baja"),
        _check("whois", "sin_datos", "info"),
        _check("headers", "rojo", "alta"),
    ]
    pendientes = _checks_a_mejorar(checks)
    assert pendientes == ["detalle de headers"]


# --------------------------------------------------------------------
# las plataformas que se actualizan solas pueden aprobar
# --------------------------------------------------------------------

def test_una_web_de_wix_no_arrastra_un_ambar_que_nadie_puede_arreglar():
    html = """<html lang="es"><head><title>Peluqueria</title>
    <meta name="generator" content="Wix.com Website Builder"></head>
    <body><h1>Peluqueria</h1></body></html>"""
    resultado = asyncio.run(comprobar_tecnologia(pagina(html)))
    assert resultado["estado"] == "verde"
    assert resultado["datos"]["cms_detectado"] == "Wix"


# --------------------------------------------------------------------
# el blindaje anti-alucinación, ahora comprobado por código
# --------------------------------------------------------------------

def test_la_ia_no_puede_colar_un_hallazgo_de_un_check_que_no_existe():
    checks = [_check("ssl", "verde", "baja")]
    inventados = [
        {"check": "ssl", "titulo": "Todo bien", "explicacion_llana": "x", "impacto_negocio": "y", "prioridad": "baja"},
        {"check": "brechas_conocidas", "titulo": "Tus datos se han filtrado", "prioridad": "alta"},
    ]
    verificados = _hallazgos_verificados(inventados, checks)
    assert [h["check"] for h in verificados] == ["ssl"]


def test_la_ia_no_puede_subir_la_prioridad_para_asustar():
    checks = [_check("seo", "ambar", "media")]
    exagerado = [{"check": "seo", "titulo": "URGENTE", "explicacion_llana": "x", "prioridad": "alta"}]
    assert _hallazgos_verificados(exagerado, checks)[0]["prioridad"] == "media"


def test_si_la_ia_se_deja_un_check_el_cliente_no_lo_pierde():
    checks = [_check("ssl", "verde", "baja"), _check("dns", "rojo", "alta")]
    incompleto = [{"check": "ssl", "titulo": "Certificado bien", "prioridad": "baja"}]
    verificados = _hallazgos_verificados(incompleto, checks)
    assert [h["check"] for h in verificados] == ["ssl", "dns"]
    assert "detalle de dns" in verificados[1]["explicacion_llana"]
