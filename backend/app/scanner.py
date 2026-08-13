"""
Orquestador de escaneo: lanza todos los checks de un dominio a la vez
y junta sus resultados en un único informe.

Esto es la Fase 2 del planning ("API + informe crudo"). Todavía no
hay capa de IA (Fase 3): lo que devuelve este módulo son los datos
crudos de cada check, sin interpretar. Es justo lo que hace falta
para empezar a ver el "informe" tomar forma.
"""

import asyncio
import time

from app.checks.accesibilidad_check import comprobar_accesibilidad
from app.checks.archivos_expuestos import comprobar_archivos_expuestos
from app.checks.dns_check import comprobar_dns
from app.checks.dominio_check import comprobar_dominio
from app.checks.experiencia_check import comprobar_experiencia
from app.checks.headers_check import comprobar_headers
from app.checks.mixed_content_check import comprobar_mixed_content
from app.checks.pagina import obtener_pagina
from app.checks.privacidad_check import comprobar_privacidad
from app.checks.rendimiento_check import comprobar_rendimiento
from app.checks.seo_check import comprobar_seo
from app.checks.ssl_check import comprobar_ssl
from app.checks.tecnologia_check import comprobar_tecnologia
from app.checks.whois_check import comprobar_whois
from app.puntuacion import resumir_checks


async def ejecutar_escaneo(
    dominio: str,
    incluir_archivos_expuestos: bool = False,
    incluir_rendimiento: bool = False,
) -> dict:
    """
    Lanza todos los checks en paralelo de verdad:
    - comprobar_ssl es una función normal (bloqueante), se manda a un
      hilo aparte con asyncio.to_thread para no frenar al resto.
    - obtener_pagina descarga la home UNA vez; su resultado se reparte
      entre seo, privacidad y mixed_content en vez de que cada uno
      vuelva a pedirle la página al servidor del cliente.
    - archivos_expuestos es ÁMBAR (ver su docstring): solo se incluye
      si incluir_archivos_expuestos=True, que representa el
      consentimiento explícito del usuario. Por defecto queda fuera,
      por ejemplo del escaneo gratis.
    - rendimiento (PageSpeed) puede tardar 20-30s por sí solo: solo se
      incluye si incluir_rendimiento=True, para no volver lento el
      escaneo rápido por defecto.
    """
    inicio = time.monotonic()

    tareas = [
        asyncio.to_thread(comprobar_ssl, dominio),
        comprobar_headers(dominio),
        comprobar_dns(dominio),
        comprobar_dominio(dominio),
        asyncio.to_thread(comprobar_whois, dominio),
    ]
    if incluir_archivos_expuestos:
        tareas.append(comprobar_archivos_expuestos(dominio))
    if incluir_rendimiento:
        tareas.append(comprobar_rendimiento(dominio))

    # La página se descarga en paralelo con el resto; los checks que
    # la necesitan (seo, privacidad, mixed_content, accesibilidad) se
    # lanzan después, en cuanto esa descarga termina.
    pagina, *resultados_iniciales = await asyncio.gather(obtener_pagina(dominio), *tareas)

    resultados_dependientes_de_pagina = await asyncio.gather(
        comprobar_seo(pagina),
        asyncio.to_thread(comprobar_privacidad, pagina),
        asyncio.to_thread(comprobar_mixed_content, pagina),
        comprobar_tecnologia(pagina),
        asyncio.to_thread(comprobar_accesibilidad, pagina),
        comprobar_experiencia(pagina, dominio),
    )

    checks = [*resultados_iniciales, *resultados_dependientes_de_pagina]
    duracion_segundos = round(time.monotonic() - inicio, 2)

    return {
        "dominio": dominio,
        "duracion_segundos": duracion_segundos,
        # El resumen (nota, semáforo global y desglose por familias) lo
        # calcula puntuacion.py, no este módulo: así hay un único sitio
        # donde se decide cuánto pesa cada cosa, y el mismo cálculo vale
        # para el informe, el PDF y los emails.
        "resumen": resumir_checks(checks),
        "checks": checks,
    }
