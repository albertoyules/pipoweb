"""
Cálculo de la puntuación del informe (0-100).

Deliberadamente NO usa IA. La nota tiene que ser reproducible: los mismos
datos de entrada deben dar siempre la misma nota, sin que dependa de cómo
esté de "inspirado" un modelo de lenguaje ese día. La IA (ver app/ia/)
solo pone las palabras; el número lo pone esta fórmula fija.
"""

# Puntos que aporta cada check según su color. Números redondos y fáciles
# de justificar ante un cliente que pregunte "¿por qué tengo un 62?".
PUNTOS_POR_ESTADO = {
    "verde": 100,
    "ambar": 60,
    "rojo": 20,
}


def calcular_puntuacion(checks: list[dict]) -> int:
    """
    Puntuación actual: la media de los puntos de cada check, redondeada.
    Con 0 checks devuelve 0 en vez de dividir por cero.
    """
    if not checks:
        return 0
    total = sum(PUNTOS_POR_ESTADO[check["estado"]] for check in checks)
    return round(total / len(checks))


def calcular_puntuacion_potencial(checks: list[dict], nombres_resueltos: set[str]) -> int:
    """
    Puntuación "si se aplican las soluciones propuestas": para los checks
    cuyo nombre está en nombres_resueltos, asumimos el mejor caso posible
    (pasan a verde) y recalculamos con la misma fórmula. Es una estimación
    optimista y se presenta como tal en el informe, nunca como una promesa.
    """
    if not checks:
        return 0
    total = sum(
        PUNTOS_POR_ESTADO["verde"] if check["check"] in nombres_resueltos else PUNTOS_POR_ESTADO[check["estado"]]
        for check in checks
    )
    return round(total / len(checks))
