"""
Cliente de la capa de IA, envuelto en una función única.

Hoy llama a Google Gemini. El resto del código (interpretar.py,
soluciones.py) no sabe nada de la librería concreta que hay detrás —
solo llama a preguntar_ia(...) y recibe un diccionario. Si en el futuro
se cambia de proveedor (p.ej. a Claude, cuando se resuelva el pago), este
es el único archivo que hay que tocar.
"""

import json

from google import genai
from google.genai import types

from app.config import GOOGLE_GEMINI_API_KEY

MODELO = "gemini-3.5-flash"


class ErrorIA(Exception):
    """Se lanza cuando la IA no puede responder o responde algo no usable."""


def preguntar_ia(instrucciones_sistema: str, pregunta: str) -> dict:
    """
    Envía una pregunta a Gemini con instrucciones de sistema estrictas y
    pide la respuesta en JSON. response_mime_type="application/json"
    obliga al modelo a devolver JSON válido (no hace falta parsear texto
    libre ni rezar por que no meta explicaciones antes o después).
    """
    if not GOOGLE_GEMINI_API_KEY:
        raise ErrorIA("Pipo no tiene configurada la clave de IA todavía.")

    cliente = genai.Client(api_key=GOOGLE_GEMINI_API_KEY)

    try:
        respuesta = cliente.models.generate_content(
            model=MODELO,
            contents=pregunta,
            config=types.GenerateContentConfig(
                system_instruction=instrucciones_sistema,
                response_mime_type="application/json",
                # Temperatura baja: queremos interpretación fiel a los
                # datos, no creatividad. No es un generador de ideas.
                temperature=0.3,
            ),
        )
    except Exception as error:  # noqa: BLE001 - cualquier fallo de red/API se trata igual
        raise ErrorIA(f"No se ha podido contactar con la IA: {error}") from error

    try:
        return json.loads(respuesta.text)
    except (json.JSONDecodeError, TypeError) as error:
        raise ErrorIA(f"La IA devolvió algo que no es JSON válido: {error}") from error
