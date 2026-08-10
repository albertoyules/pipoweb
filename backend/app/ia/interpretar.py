"""
Capa de IA — interpretación de hallazgos.

Coge el JSON crudo de un escaneo (lo que ya viste en /api/scan) y lo
convierte en algo que un dueño de peluquería o un taller pueda leer y
entender, sin jerga técnica. Es la Fase 3 del planning: "la IA coge
estos datos crudos y los traduce a lenguaje llano".

Blindaje anti-alucinación (punto 11 del planning — "la IA inventa
hallazgos" es el riesgo #1 de este tipo de producto):
- El prompt exige responder con EXACTAMENTE un hallazgo por cada check
  recibido, ni más ni menos, referenciado por su id.
- La prioridad de cada hallazgo la copia del dato original, no la inventa.
- La puntuación global NUNCA la pone la IA: la calcula puntuacion.py con
  una fórmula fija (ver ese módulo).
"""

import json

from app.ia.cliente import preguntar_ia
from app.puntuacion import calcular_puntuacion

INSTRUCCIONES_SISTEMA = """
Eres Pipo, un asistente que traduce resultados técnicos de seguridad y SEO
a lenguaje llano para dueños de pequeños negocios (peluquerías, talleres,
clínicas...) sin conocimientos técnicos.

REGLAS ESTRICTAS, sin excepción:
1. Solo puedes describir los hallazgos que aparecen en los datos que se te
   dan. No inventes problemas que no estén ahí, ni afirmes que algo está
   "todo perfecto" si no hay datos que lo confirmen.
2. Debes devolver EXACTAMENTE un hallazgo por cada check recibido en los
   datos de entrada, identificado por el mismo campo "check" (id) que
   traía. No añadas, no quites, no combines.
3. El campo "prioridad" de cada hallazgo debe copiarse tal cual del dato
   de entrada — nunca la cambies ni la inventes.
4. No eres abogado ni Delegado de Protección de Datos (DPO). Si un
   hallazgo toca temas legales (RGPD, cookies...), descríbelo como
   diagnóstico técnico, nunca como asesoramiento legal.
5. Lenguaje cercano y sin tecnicismos innecesarios, pero preciso: nada de
   inventar cifras o plazos que no estén en los datos.
6. Responde ÚNICAMENTE con JSON válido que cumpla el esquema pedido. Sin
   texto antes ni después, sin explicaciones fuera del JSON.
""".strip()

ESQUEMA_ESPERADO = """
{
  "resumen_ejecutivo": "2-3 frases sobre el estado general de la web, tono cercano",
  "hallazgos": [
    {
      "check": "id del check, igual que en los datos de entrada",
      "titulo": "titular corto (máx 8 palabras)",
      "explicacion_llana": "qué significa esto, en palabras sencillas",
      "impacto_negocio": "por qué le debería importar al dueño del negocio, una frase",
      "prioridad": "copiado tal cual del dato de entrada"
    }
  ]
}
""".strip()


def interpretar_hallazgos(resultado_escaneo: dict) -> dict:
    """
    Recibe el resultado crudo de ejecutar_escaneo() (ver scanner.py) y
    devuelve el informe interpretado: resumen, hallazgos en lenguaje
    llano, y la puntuación global (calculada por código, no por la IA).
    """
    checks = resultado_escaneo["checks"]

    pregunta = (
        f"Datos crudos del escaneo (formato JSON):\n{json.dumps(checks, ensure_ascii=False)}\n\n"
        f"Devuelve la interpretación siguiendo EXACTAMENTE este esquema:\n{ESQUEMA_ESPERADO}"
    )

    resultado_ia = preguntar_ia(INSTRUCCIONES_SISTEMA, pregunta)

    return {
        "dominio": resultado_escaneo["dominio"],
        "puntuacion_global": calcular_puntuacion(checks),
        "resumen_ejecutivo": resultado_ia.get("resumen_ejecutivo", ""),
        "hallazgos": resultado_ia.get("hallazgos", []),
    }
