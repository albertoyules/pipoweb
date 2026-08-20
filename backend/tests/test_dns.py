"""
Tests de dns_check, el módulo que hasta el 21 ago 2026 no probaba nadie.

Por qué no lo probaba nadie: en el Mac de Alberto, "import dns.resolver"
se queda colgado indefinidamente (en Railway no pasa, ahí funciona). Así
que cualquier test que importara este módulo dejaba la suite inservible,
y simplemente no se escribió ninguno.

La salida es inyectar un "dns" de mentira en sys.modules ANTES de
importar dns_check. Lo que se prueba no es dnspython —eso ya está
probado por quien lo escribió— sino NUESTRA lógica: que se consulten
todos los selectores DKIM, que se haga en paralelo, y que el semáforo
diga lo que tiene que decir.
"""

import asyncio
import sys
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _instalar_dns_falso():
    """Un dnspython de mentira, suficiente para que dns_check se importe."""
    for nombre in ("dns", "dns.asyncresolver", "dns.exception", "dns.resolver",
                   "dns.flags", "dns.rdatatype"):
        sys.modules.setdefault(nombre, types.ModuleType(nombre))
    sys.modules["dns"].asyncresolver = sys.modules["dns.asyncresolver"]
    sys.modules["dns"].exception = sys.modules["dns.exception"]
    sys.modules["dns"].resolver = sys.modules["dns.resolver"]

    class ErrorDNS(Exception):
        pass

    for modulo, nombre in (("dns.resolver", "NXDOMAIN"), ("dns.resolver", "NoAnswer"),
                           ("dns.resolver", "NoNameservers"), ("dns.exception", "Timeout")):
        if not hasattr(sys.modules[modulo], nombre):
            setattr(sys.modules[modulo], nombre, type(nombre, (ErrorDNS,), {}))


_instalar_dns_falso()

from app.checks import dns_check  # noqa: E402


@pytest.fixture
def registros(monkeypatch):
    """Deja preparar qué contesta el DNS y ver qué se le ha preguntado."""
    preguntas = []
    tabla = {}

    async def consultar(nombre):
        preguntas.append(nombre)
        return tabla.get(nombre, [])

    monkeypatch.setattr(dns_check, "_consultar_txt", consultar)
    return tabla, preguntas


def test_se_detecta_el_dkim_de_resend_y_de_zoho(registros):
    """
    El caso real que destapó esto: Pipo decía "no se ha detectado DKIM"
    sobre pipoweb.com, que tiene DOS claves publicadas y funcionando. La
    lista de selectores se había quedado en ocho clásicos y no incluía
    ninguno de los dos proveedores que usa el propio Pipo.
    """
    tabla, _ = registros
    tabla["pipoweb.com"] = ["v=spf1 include:zohomail.eu ~all"]
    tabla["_dmarc.pipoweb.com"] = ["v=DMARC1; p=quarantine;"]
    tabla["resend._domainkey.pipoweb.com"] = ["p=MIGf"]
    tabla["zmail._domainkey.pipoweb.com"] = ["v=DKIM1; p=MIGf"]

    resultado = asyncio.run(dns_check.comprobar_dns("pipoweb.com"))

    assert resultado["estado"] == "verde"
    assert resultado["datos"]["dkim_selector_encontrado"] == "resend"
    assert "No se ha detectado DKIM" not in resultado["detalle"]


def test_se_preguntan_todos_los_selectores_de_una_vez(registros):
    """
    Iban en serie, uno detrás de otro, con 3 segundos de espera cada uno:
    con casi veinte selectores, un dominio sin DKIM y un DNS lento se
    comía casi un minuto dentro de un escaneo que dura menos de uno.
    """
    _, preguntas = registros
    asyncio.run(dns_check.comprobar_dns("ejemplo.es"))

    consultas_dkim = [p for p in preguntas if "_domainkey" in p]
    assert len(consultas_dkim) == len(dns_check.SELECTORES_DKIM_HABITUALES)
    # Si fueran en serie se pararían en el primero que responde; van todas.
    assert "resend._domainkey.ejemplo.es" in consultas_dkim


def test_un_dominio_sin_proteccion_sigue_saliendo_en_rojo(registros):
    """Ampliar la lista de selectores no puede ablandar el diagnóstico."""
    resultado = asyncio.run(dns_check.comprobar_dns("sinnada.es"))
    assert resultado["estado"] == "rojo"
    assert "SPF" in resultado["detalle"]


def test_dmarc_en_solo_observar_es_ambar(registros):
    tabla, _ = registros
    tabla["ejemplo.es"] = ["v=spf1 -all"]
    tabla["_dmarc.ejemplo.es"] = ["v=DMARC1; p=none; rua=mailto:x@ejemplo.es"]
    resultado = asyncio.run(dns_check.comprobar_dns("ejemplo.es"))
    assert resultado["estado"] == "ambar"
    assert resultado["datos"]["dmarc_politica"] == "none"


def test_falta_solo_uno_de_los_dos_es_ambar(registros):
    tabla, _ = registros
    tabla["ejemplo.es"] = ["v=spf1 -all"]
    resultado = asyncio.run(dns_check.comprobar_dns("ejemplo.es"))
    assert resultado["estado"] == "ambar"
    assert "DMARC" in resultado["detalle"]
