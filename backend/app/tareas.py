"""
Motor del nivel "Tranquilidad" (re-escaneo mensual, ver CLAUDE.md, P3):
recorre las suscripciones activas a las que les toca revisión, vuelve a
escanear su dominio, compara con el escaneo anterior y manda el resumen
por email. Sin cobro automático todavía — Alberto da de alta cada
suscripción a mano desde el panel cuando cierra un cliente.

Este módulo NO tiene su propio scheduler: no hay ningún proceso de
Pipo que se despierte solo cada mes. Lo dispara un cron EXTERNO (ver
CLAUDE.md) llamando a POST /api/tareas/re-escanear-suscripciones con
la clave de admin, igual de a menudo que se quiera (a diario es lo
razonable) — el propio `suscripciones_pendientes_de_re_escaneo` decide
a quién le toca de verdad por fecha, así que llamarlo de más nunca
duplica un re-escaneo.
"""

import logging

from app.database import (
    escaneo_anterior,
    guardar_escaneo,
    marcar_ejecutada_suscripcion,
    suscripciones_pendientes_de_re_escaneo,
)
from app.notificaciones.enviar import ErrorEmail, enviar_email
from app.notificaciones.mensajes import mensaje_resumen_mensual
from app.puntuacion import comparar_escaneos
from app.scanner import ejecutar_escaneo

logger = logging.getLogger("pipo.tareas")


async def _procesar_suscripcion(suscripcion: dict) -> dict:
    """
    Re-escanea un dominio suscrito, guarda el resultado como un escaneo
    normal (así el cliente puede seguir usando su enlace de siempre) y
    manda el resumen. Nunca lanza: un dominio caído o un email que
    rebota no debe tumbar el resto de la cola, así que cualquier fallo
    se captura y se informa en el resultado de esta fila.
    """
    dominio = suscripcion["dominio"]
    try:
        anterior = escaneo_anterior(dominio)
        resultado = await ejecutar_escaneo(dominio)
        resultado["comparacion"] = comparar_escaneos(anterior, resultado) if anterior else None

        id_escaneo, _token = guardar_escaneo(
            dominio=dominio,
            estado_global=resultado["resumen"]["estado_global"],
            resultado=resultado,
        )
        marcar_ejecutada_suscripcion(suscripcion["id"], id_escaneo)

        asunto, cuerpo, html = mensaje_resumen_mensual(
            dominio=dominio,
            nota_actual=resultado["resumen"]["puntuacion"],
            comparacion=resultado["comparacion"],
        )
        try:
            enviar_email(suscripcion["email"], asunto, cuerpo, html)
            email_enviado = True
        except ErrorEmail as error:
            # El re-escaneo ya se guardó y la suscripción ya quedó
            # marcada como ejecutada este mes: un email que falla no
            # debe forzar un segundo escaneo del mismo dominio mañana.
            logger.warning("No se pudo enviar el resumen mensual a %s (%s): %s", suscripcion["email"], dominio, error)
            email_enviado = False

        return {
            "id_suscripcion": suscripcion["id"],
            "dominio": dominio,
            "id_escaneo": id_escaneo,
            "email_enviado": email_enviado,
            "error": None,
        }
    except Exception as error:  # noqa: BLE001 - una web caída no debe parar la cola entera
        logger.warning("Fallo re-escaneando la suscripción %s (%s): %s", suscripcion["id"], dominio, error)
        return {
            "id_suscripcion": suscripcion["id"],
            "dominio": dominio,
            "id_escaneo": None,
            "email_enviado": False,
            "error": f"{type(error).__name__}: {error}",
        }


async def ejecutar_re_escaneos_pendientes(dias: int = 30) -> list[dict]:
    """
    Procesa, una a una, todas las suscripciones a las que les toca
    revisión. Secuencial y no en paralelo a propósito: cada re-escaneo
    ya lanza sus checks en paralelo por dentro (ver scanner.py), y
    escanear muchos dominios ajenos a la vez desde el mismo proceso es
    justo el patrón de tráfico que seguridad.py existe para evitar.
    """
    pendientes = suscripciones_pendientes_de_re_escaneo(dias=dias)
    return [await _procesar_suscripcion(suscripcion) for suscripcion in pendientes]
