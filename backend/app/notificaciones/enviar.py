"""
Envío de emails transaccionales: la confirmación privada al cliente
que pide el informe completo, y el aviso a Alberto de que hay un
pedido nuevo (ver CLAUDE.md, P2).

Usa Gmail por SMTP con una "contraseña de aplicación" (no la
contraseña normal de la cuenta — Gmail bloquea el login SMTP con la
contraseña normal por seguridad) en vez de un proveedor de email
transaccional (Resend, SendGrid...): es gratis, no exige darse de alta
en ningún sitio nuevo, y el volumen de esta fase — unos pocos pedidos
al día como mucho — está muy por debajo de cualquier límite de Gmail.
Si el volumen crece de verdad, esto es lo primero que habría que
cambiar (Gmail no está pensado para enviar cientos de emails/día).
"""

import smtplib
from email.mime.text import MIMEText

from app.config import GMAIL_APP_PASSWORD, GMAIL_EMAIL


class ErrorEmail(Exception):
    """Se lanza cuando no se ha podido enviar el email."""


def enviar_email(destinatario: str, asunto: str, cuerpo: str) -> None:
    """
    Envío síncrono y bloqueante a propósito (smtplib no tiene versión
    async) — quien llame a esto debe mandarlo a un hilo aparte con
    asyncio.to_thread, igual que ya se hace con la IA y con WeasyPrint.
    """
    if not GMAIL_EMAIL or not GMAIL_APP_PASSWORD:
        raise ErrorEmail("Pipo no tiene configurado el envío de emails todavía.")

    mensaje = MIMEText(cuerpo)
    mensaje["Subject"] = asunto
    mensaje["From"] = GMAIL_EMAIL
    mensaje["To"] = destinatario

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as servidor:
            servidor.login(GMAIL_EMAIL, GMAIL_APP_PASSWORD)
            servidor.send_message(mensaje)
    except Exception as error:  # noqa: BLE001 - cualquier fallo de red/SMTP se trata igual
        raise ErrorEmail(f"No se ha podido enviar el email: {error}") from error
