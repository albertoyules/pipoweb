"""
Envío de emails transaccionales: la confirmación privada al cliente
que pide un arreglo, y el aviso a Alberto de que hay una solicitud
nueva (ver CLAUDE.md, P2).

Usa Resend (API por HTTPS) desde el 13 ago 2026. Antes usaba Gmail por
SMTP, pero Railway bloquea el tráfico SMTP saliente por completo —
comprobado con curl real contra producción probando los dos puertos
estándar (465 y 587): los dos fallaban con el mismo patrón exacto de
timeout, la firma de un bloqueo de red, no de credenciales mal puestas
(ver CLAUDE.md para el diagnóstico completo). Resend manda el email con
una petición HTTP normal por el puerto 443, que ningún hosting bloquea
— es el mismo puerto por el que ya habla el resto de Pipo con Anthropic
o con Google PageSpeed.
"""

import httpx

from app.config import RESEND_API_KEY

URL_API = "https://api.resend.com/emails"

# Remitente de pruebas de Resend. Sin verificar un dominio propio (Pipo
# todavía no tiene uno decidido — ver CLAUDE.md), no se puede mandar
# desde una dirección con marca propia como "pipo@pipo.es": hay que
# usar este remitente genérico hasta que exista ese dominio y se
# verifique con sus registros DNS en el panel de Resend.
REMITENTE = "Pipo <onboarding@resend.dev>"


class ErrorEmail(Exception):
    """Se lanza cuando no se ha podido enviar el email."""


def enviar_email(destinatario: str, asunto: str, cuerpo: str) -> None:
    """
    Envío síncrono y bloqueante a propósito (usamos el cliente síncrono
    de httpx, no el asíncrono) — quien llame a esto debe mandarlo a un
    hilo aparte con asyncio.to_thread, igual que ya se hace con la IA y
    con WeasyPrint.
    """
    if not RESEND_API_KEY:
        raise ErrorEmail("Pipo no tiene configurado el envío de emails todavía.")

    try:
        respuesta = httpx.post(
            URL_API,
            headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
            json={
                "from": REMITENTE,
                "to": [destinatario],
                "subject": asunto,
                "text": cuerpo,
            },
            timeout=15,
        )
        respuesta.raise_for_status()
    except httpx.HTTPStatusError as error:
        # Resend explica el motivo del rechazo en el cuerpo de la
        # respuesta (email inválido, remitente no verificado...) —
        # se incluye tal cual, es mucho más útil que solo el código.
        raise ErrorEmail(
            f"Resend ha rechazado el email ({error.response.status_code}): {error.response.text}"
        ) from error
    except httpx.RequestError as error:
        raise ErrorEmail(f"No se ha podido conectar con Resend: {error}") from error
