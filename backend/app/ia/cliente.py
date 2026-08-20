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

import httpx

from app.config import ANTHROPIC_API_KEY

MODELO = "claude-haiku-4-5-20251001"

# Un informe son 11-13 hallazgos, cada uno con titular, explicación e
# impacto, en español. Cabe en 2048, pero justo — y pasarse no daba un
# error claro, daba un JSON cortado (ver abajo). Con 4096 hay margen sin
# que el coste cambie de forma apreciable: se paga por lo generado, no
# por el límite.
MAX_TOKENS = 4096

_CLIENTE = None


def _cliente():
    """
    El cliente de Anthropic, creado la primera vez que hace falta y
    reutilizado a partir de ahí (así se reaprovecha la conexión).

    El import va aquí dentro y no arriba, igual que el de WeasyPrint en
    app/pdf/generar_pdf.py, por dos motivos:

    - "import anthropic" arrastra un árbol de dependencias grande, y
      hasta ahora se ejecutaba al arrancar el servidor aunque nadie
      pidiera ningún informe. Cualquier problema ahí tumbaba el arranque
      entero, incluido /health, en vez de fallar solo el endpoint de IA
      (que además ya sabe devolver un 502 con su motivo).
    - Con el import arriba, los tests no se pueden ni recoger sin cargar
      el SDK entero. En el Mac de Alberto ese import se queda colgado y
      dejaba la suite inservible (20 ago 2026).

    trust_env=False: algunas plataformas (Railway incluida) inyectan
    variables HTTP_PROXY/HTTPS_PROXY para su propio tráfico interno.
    httpx las respeta por defecto, lo que puede romper la conexión hacia
    la API de Anthropic con un "Connection error" que no tiene nada que
    ver con la clave.
    """
    global _CLIENTE
    if _CLIENTE is None:
        import anthropic

        _CLIENTE = anthropic.Anthropic(
            api_key=ANTHROPIC_API_KEY or "sin-configurar",
            http_client=httpx.Client(trust_env=False, timeout=30.0),
            max_retries=2,
        )
    return _CLIENTE


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

    try:
        respuesta = _cliente().messages.create(
            model=MODELO,
            max_tokens=MAX_TOKENS,
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
        # Se incluye el tipo de excepción, no solo el mensaje: httpx a
        # veces da mensajes genéricos ("Connection error") que sin el
        # tipo y la causa real son imposibles de diagnosticar en remoto.
        causa = f" (causa: {error.__cause__})" if error.__cause__ else ""
        raise ErrorIA(
            f"No se ha podido contactar con la IA: [{type(error).__name__}] {error}{causa}"
        ) from error

    # Si el modelo se queda sin espacio, el JSON llega cortado por la mitad
    # y el error que salía era "la IA devolvió algo que no es JSON válido",
    # que manda a buscar donde no es. Mejor decir lo que pasó de verdad.
    if respuesta.stop_reason == "max_tokens":
        raise ErrorIA(
            f"La respuesta de la IA se ha cortado por llegar al límite de {MAX_TOKENS} tokens."
        )

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
