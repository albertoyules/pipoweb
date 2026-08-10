"""
Capa de IA — generación de soluciones (el "segundo botón").

A partir de los checks que NO están en verde, pide a la IA pasos
concretos y accionables para arreglarlos, y calcula (por código, no por
la IA) una nota estimada de "cómo quedaría la web si se aplican todas
las soluciones propuestas" — ver puntuacion.calcular_puntuacion_potencial.

Es una función deliberadamente separada de interpretar.py: no todo el
que pide un escaneo quiere ya los pasos técnicos para arreglarlo: puede
ser el propio dueño (que se lo pasa a su informático) o alguien que solo
quiere ver el diagnóstico primero. Separarlo en dos llamadas también deja
la puerta abierta a que "ver soluciones" sea una función de pago aparte
del informe básico, si el negocio lo pide así más adelante.
"""

import json

from app.ia.cliente import preguntar_ia
from app.puntuacion import calcular_puntuacion, calcular_puntuacion_potencial

INSTRUCCIONES_SISTEMA = """
Eres Pipo, un asistente que da soluciones prácticas y accionables para
problemas de seguridad y SEO detectados en la web de un pequeño negocio.

REGLAS ESTRICTAS, sin excepción:
1. Solo propones soluciones para los checks que se te pasan — no inventes
   problemas nuevos ni añadas checks que no están en los datos.
2. Debes devolver EXACTAMENTE una solución por cada check recibido,
   identificada por el mismo campo "check" (id) que traía.
3. Los pasos deben ser concretos y accionables (qué hacer, no solo "arregla
   esto"), pero sin inventar nombres de proveedores, precios o plazos que
   no te hayan dado.
4. Indica quién debería ejecutar cada paso: el propio dueño del negocio,
   su proveedor/informático web, o un profesional externo (p.ej. legal
   para temas de RGPD) — nunca te presentes tú mismo como quien lo va a
   hacer, ni como asesor legal.
5. Responde ÚNICAMENTE con JSON válido que cumpla el esquema pedido. Sin
   texto antes ni después.
""".strip()

ESQUEMA_ESPERADO = """
{
  "soluciones": [
    {
      "check": "id del check, igual que en los datos de entrada",
      "problema": "resumen de una frase del problema",
      "pasos": ["paso 1 concreto", "paso 2 concreto", "..."],
      "quien_lo_hace": "el dueño del negocio" | "el proveedor o informático web" | "un profesional externo (p.ej. legal)",
      "dificultad": "baja" | "media" | "alta"
    }
  ]
}
""".strip()


def generar_soluciones(resultado_escaneo: dict) -> dict:
    """
    Recibe el resultado crudo de ejecutar_escaneo() y devuelve soluciones
    solo para los checks que no están en verde, junto con la puntuación
    actual y una estimada tras aplicar los cambios (best case, por código).
    """
    checks = resultado_escaneo["checks"]
    checks_con_problemas = [c for c in checks if c["estado"] != "verde"]

    if not checks_con_problemas:
        # Nada que arreglar: no hace falta ni llamar a la IA.
        puntuacion = calcular_puntuacion(checks)
        return {
            "dominio": resultado_escaneo["dominio"],
            "puntuacion_actual": puntuacion,
            "puntuacion_estimada_tras_cambios": puntuacion,
            "soluciones": [],
            "mensaje": "No hay ningún check en ámbar o rojo: no hay soluciones que proponer.",
        }

    pregunta = (
        f"Checks con problemas (formato JSON):\n{json.dumps(checks_con_problemas, ensure_ascii=False)}\n\n"
        f"Devuelve las soluciones siguiendo EXACTAMENTE este esquema:\n{ESQUEMA_ESPERADO}"
    )

    resultado_ia = preguntar_ia(INSTRUCCIONES_SISTEMA, pregunta)
    soluciones = resultado_ia.get("soluciones", [])

    nombres_resueltos = {s["check"] for s in soluciones}

    return {
        "dominio": resultado_escaneo["dominio"],
        "puntuacion_actual": calcular_puntuacion(checks),
        "puntuacion_estimada_tras_cambios": calcular_puntuacion_potencial(checks, nombres_resueltos),
        "soluciones": soluciones,
    }
