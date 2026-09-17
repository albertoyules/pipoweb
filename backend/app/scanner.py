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
from app.checks.area_privada_check import comprobar_area_privada
from app.checks.dns_check import comprobar_dns
from app.checks.dominio_check import comprobar_dominio
from app.checks.ecommerce_check import comprobar_ecommerce
from app.checks.experiencia_check import comprobar_experiencia
from app.checks.headers_check import comprobar_headers
from app.checks.mixed_content_check import comprobar_mixed_content
from app.checks.pagina import obtener_pagina
from app.checks.perfil_sitio import detectar_perfil
from app.checks.privacidad_check import comprobar_privacidad
from app.checks.rendimiento_check import comprobar_rendimiento
from app.checks.seo_check import comprobar_seo
from app.checks.ssl_check import comprobar_ssl
from app.checks.tecnologia_check import comprobar_tecnologia
from app.checks.whois_check import comprobar_whois
from app.puntuacion import resumir_checks
from app.seguridad import dominio_raiz


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

    # SPF, DMARC, CAA, DNSSEC y el WHOIS viven en el dominio registrado,
    # nunca en el subdominio "www". Si se les pasa "www.ejemplo.com"
    # preguntan donde no puede haber respuesta y toman el silencio por
    # un fallo del negocio (ver dominio_raiz en seguridad.py). El resto
    # de checks sí usan el host tal cual lo pidió el usuario: el
    # certificado y las cabeceras son de ese host concreto.
    raiz = dominio_raiz(dominio)

    tareas = [
        asyncio.to_thread(comprobar_ssl, dominio),
        comprobar_headers(dominio),
        comprobar_dns(raiz),
        comprobar_dominio(raiz),
        asyncio.to_thread(comprobar_whois, raiz),
    ]
    if incluir_archivos_expuestos:
        tareas.append(comprobar_archivos_expuestos(dominio))
    if incluir_rendimiento:
        tareas.append(comprobar_rendimiento(dominio))

    # La página se descarga en paralelo con el resto; los checks que
    # la necesitan (seo, privacidad, mixed_content, accesibilidad) se
    # lanzan después, en cuanto esa descarga termina.
    pagina, *resultados_iniciales = await asyncio.gather(obtener_pagina(dominio), *tareas)

    resultados_dependientes_de_pagina, perfil_sitio = await asyncio.gather(
        asyncio.gather(
            comprobar_seo(pagina),
            asyncio.to_thread(comprobar_privacidad, pagina),
            asyncio.to_thread(comprobar_mixed_content, pagina),
            comprobar_tecnologia(pagina),
            asyncio.to_thread(comprobar_accesibilidad, pagina),
            comprobar_experiencia(pagina, dominio),
        ),
        # Metadata, no un check: no tiene semáforo ni entra en la nota
        # (ver puntuacion.py). Se calcula aquí, no dentro de un check
        # concreto, porque decide qué checks condicionales se añaden a
        # continuación (tienda online, área privada...).
        detectar_perfil(pagina),
    )

    # Módulos condicionales: solo se lanzan si el perfil detectó la
    # señal correspondiente. Una landing sin carrito ni login no gana
    # ni pierde nada por no tener estos checks — simplemente no
    # aparecen (ver puntuacion.py sobre cómo se combina la nota).
    tareas_condicionales = []
    if perfil_sitio["senales"].get("tiene_checkout"):
        tareas_condicionales.append(asyncio.to_thread(comprobar_ecommerce, pagina))
    if perfil_sitio["senales"].get("tiene_login"):
        tareas_condicionales.append(asyncio.to_thread(comprobar_area_privada, pagina))

    resultados_condicionales = await asyncio.gather(*tareas_condicionales)

    checks = [*resultados_iniciales, *resultados_dependientes_de_pagina, *resultados_condicionales]
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
        "perfil_sitio": perfil_sitio,
    }
