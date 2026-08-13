"""
Tests de la nota y del semáforo.

Por qué estos y no otros: aquí es donde vive la promesa del producto.
Si la fórmula se descalibra sin que nadie se entere, Pipo empieza a
decirle "crítico" a webs que están bien (o al revés), y eso no se nota
mirando la pantalla — se nota cuando un cliente deja de creerte.

Se ejecutan con:  cd backend && .venv/bin/pytest
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.puntuacion import (  # noqa: E402
    calcular_precio_arreglo,
    calcular_puntuacion,
    comparar_escaneos,
    resumir_checks,
)


def check(nombre, estado, prioridad="media"):
    """Un check de mentira, con lo mínimo que mira la puntuación."""
    return {"check": nombre, "estado": estado, "prioridad": prioridad, "detalle": "", "datos": {}}


TODO_VERDE = [
    check(n, "verde", "baja")
    for n in ("ssl", "headers", "dns", "dominio", "whois", "seo", "privacidad",
              "mixed_content", "tecnologia", "accesibilidad", "experiencia")
]


def con(nombre, estado, prioridad="media"):
    """La lista completa en verde, cambiando solo un check."""
    return [check(c["check"], estado, prioridad) if c["check"] == nombre else c for c in TODO_VERDE]


# --- Nota -----------------------------------------------------------

def test_todo_verde_es_cien():
    assert calcular_puntuacion(TODO_VERDE) == 100


def test_sin_checks_no_revienta():
    assert calcular_puntuacion([]) == 0


def test_los_checks_graves_pesan_mas_que_los_menores():
    """Un certificado roto tiene que bajar más la nota que un WHOIS raro."""
    nota_ssl_roto = calcular_puntuacion(con("ssl", "rojo"))
    nota_whois_roto = calcular_puntuacion(con("whois", "rojo"))
    assert nota_ssl_roto < nota_whois_roto


# --- Semáforo global ------------------------------------------------

def test_un_detalle_de_seo_no_pinta_el_informe_de_rojo():
    """
    El caso real que motivó la reescritura del 13 ago 2026: un <title>
    tres caracteres más largo de lo recomendado dejaba el informe entero
    en "crítico". Ahora un rojo de SEO llega a ámbar, no a rojo.
    """
    assert resumir_checks(con("seo", "rojo"))["estado_global"] == "ambar"


def test_un_problema_de_seguridad_si_pinta_el_informe_de_rojo():
    assert resumir_checks(con("ssl", "rojo"))["estado_global"] == "rojo"


def test_un_problema_legal_tambien_pinta_de_rojo():
    assert resumir_checks(con("privacidad", "rojo"))["estado_global"] == "rojo"


def test_un_rojo_en_un_check_menor_de_seguridad_se_queda_en_ambar():
    """DNSSEC o WHOIS son detalles: no convierten una web en un peligro."""
    assert resumir_checks(con("dominio", "rojo"))["estado_global"] == "ambar"


def test_todo_verde_es_verde():
    assert resumir_checks(TODO_VERDE)["estado_global"] == "verde"


def test_el_resumen_agrupa_en_las_tres_familias():
    familias = resumir_checks(TODO_VERDE)["familias"]
    assert [f["clave"] for f in familias] == ["seguridad", "cumplimiento", "clientes"]
    assert all(f["puntuacion"] == 100 for f in familias)


def test_una_familia_puede_estar_mal_sin_arrastrar_a_las_demas():
    resumen = resumir_checks(con("privacidad", "rojo"))
    por_clave = {f["clave"]: f for f in resumen["familias"]}
    assert por_clave["cumplimiento"]["estado"] == "rojo"
    assert por_clave["seguridad"]["estado"] == "verde"


# --- Comparación entre escaneos -------------------------------------

def test_comparacion_detecta_mejoras_y_empeoramientos():
    antes = {"checks": con("seo", "rojo"), "resumen": resumir_checks(con("seo", "rojo")), "fecha": "2026-08-01"}
    ahora = {"checks": con("ssl", "ambar"), "resumen": resumir_checks(con("ssl", "ambar"))}

    comparacion = comparar_escaneos(antes, ahora)
    assert {"check": "seo", "antes": "rojo", "ahora": "verde"} in comparacion["mejoras"]
    assert {"check": "ssl", "antes": "verde", "ahora": "ambar"} in comparacion["empeoramientos"]
    assert comparacion["fecha_anterior"] == "2026-08-01"


def test_comparacion_sin_cambios_no_inventa_nada():
    escaneo = {"checks": TODO_VERDE, "resumen": resumir_checks(TODO_VERDE), "fecha": "2026-08-01"}
    comparacion = comparar_escaneos(escaneo, escaneo)
    assert comparacion["diferencia"] == 0
    assert comparacion["mejoras"] == [] and comparacion["empeoramientos"] == []


# --- Precio del arreglo ---------------------------------------------

def test_una_web_perfecta_cuesta_el_precio_base():
    assert calcular_precio_arreglo(TODO_VERDE) == 89


def test_el_precio_sube_con_los_problemas_pero_tiene_tope():
    todo_roto = [check(c["check"], "rojo", "alta") for c in TODO_VERDE]
    assert calcular_precio_arreglo(todo_roto) == 149


def test_una_web_normal_no_cae_siempre_en_el_tope():
    """Si todas las webs dieran 149€, el número no significaría nada."""
    unos_cuantos = con("seo", "ambar", "media")
    unos_cuantos = [check(c["check"], "ambar", "media") if c["check"] in ("dns", "privacidad") else c for c in unos_cuantos]
    precio = calcular_precio_arreglo(unos_cuantos)
    assert 89 < precio < 149
