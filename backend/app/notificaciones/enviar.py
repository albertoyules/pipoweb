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

from app.config import REMITENTE_EMAIL, RESEND_API_KEY, RESPONDER_A

URL_API = "https://api.resend.com/emails"


class ErrorEmail(Exception):
    """Se lanza cuando no se ha podido enviar el email."""


def enviar_email(destinatario: str, asunto: str, cuerpo: str, html: str | None = None) -> None:
    """
    Envío síncrono y bloqueante a propósito (usamos el cliente síncrono
    de httpx, no el asíncrono) — quien llame a esto debe mandarlo a un
    hilo aparte con asyncio.to_thread, igual que ya se hace con la IA y
    con WeasyPrint.

    `cuerpo` (texto plano) es SIEMPRE obligatorio, `html` es opcional.
    Cuando se manda `html`, Resend lo entrega como multipart/alternative
    (igual que cualquier email normal): los clientes de correo modernos
    enseñan la versión bonita, y los que no soportan HTML —o alguien que
    lo abre en un lector de texto— caen automáticamente al texto plano.
    Por eso `cuerpo` no se recorta ni se toca aunque exista `html`: es
    el plan B real, no un adorno.
    """
    if not RESEND_API_KEY:
        raise ErrorEmail("Pipo no tiene configurado el envío de emails todavía.")

    cuerpo_peticion = {
        "from": REMITENTE_EMAIL,
        "to": [destinatario],
        "subject": asunto,
        "text": cuerpo,
    }
    if html:
        cuerpo_peticion["html"] = html
    if RESPONDER_A:
        cuerpo_peticion["reply_to"] = RESPONDER_A

    try:
        respuesta = httpx.post(
            URL_API,
            headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
            json=cuerpo_peticion,
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
