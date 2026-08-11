"""
Cliente de la capa de IA, envuelto en una función única.

Hoy llama a Claude (Anthropic). El resto del código (interpretar.py,
soluciones.py) no sabe nada de la librería concreta que hay detrás —
solo llama a preguntar_ia(...) y recibe un diccionario. Si en el futuro
se cambia de proveedor otra vez, este es el único archivo que hay que
tocar.

Antes usaba Google Gemini, pero su plan gratuito solo daba 20
peticiones/día — se cambió el 11 ago 2026 al resolverse el problema de
pago con Anthropic (ver CLAUDE.md, decisión #5).
"""

import json

import anthropic

from app.config import ANTHROPIC_API_KEY

MODELO = "claude-haiku-4-5-20251001"


class ErrorIA(Exception):
    """Se lanza cuando la IA no puede responder o responde algo no usable."""


def preguntar_ia(instrucciones_sistema: str, pregunta: str) -> dict:
    """
    Envía una pregunta a Claude con instrucciones de sistema estrictas y
    le pide que devuelva JSON. A diferencia de Gemini, la API de Claude
    no tiene un "modo JSON forzado" — se lo pedimos explícitamente en las
    instrucciones de sistema y parseamos el texto que devuelve.
    """
    if not ANTHROPIC_API_KEY:
        raise ErrorIA("Pipo no tiene configurada la clave de IA todavía.")

    cliente = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    try:
        respuesta = cliente.messages.create(
            model=MODELO,
            max_tokens=2048,
            # Temperatura baja: queremos interpretación fiel a los
            # datos, no creatividad. No es un generador de ideas.
            temperature=0.3,
            system=(
                instrucciones_sistema
                + "\n\nResponde ÚNICAMENTE con JSON válido, sin texto antes"
                " ni después, sin bloques de código markdown ni ```json."
            ),
            messages=[{"role": "user", "content": pregunta}],
        )
    except Exception as error:  # noqa: BLE001 - cualquier fallo de red/API se trata igual
        raise ErrorIA(f"No se ha podido contactar con la IA: {error}") from error

    texto = respuesta.content[0].text.strip()
    # Por si acaso el modelo se envuelve en un bloque de código a pesar
    # de que se le ha pedido que no lo haga.
    if texto.startswith("```"):
        texto = texto.strip("`")
        if texto.startswith("json"):
            texto = texto[4:]
        texto = texto.strip()

    try:
        return json.loads(texto)
    except (json.JSONDecodeError, TypeError) as error:
        raise ErrorIA(f"La IA devolvió algo que no es JSON válido: {error}") from error
