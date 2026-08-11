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


# Precio estimado del nivel "lo arreglamos nosotros" (ver CLAUDE.md, P2).
# Igual que la nota, esto NUNCA lo calcula la IA: sería fácil que un
# modelo "regalara" un precio bajo para parecer más simpático, o al
# revés. Puntos por dificultad real de arreglar cada cosa, no por lo
# grave que sea (un check rojo puede ser fácil de arreglar y uno ámbar
# puede no serlo) — solo cuentan los checks que no están ya en verde.
PRECIO_BASE_ARREGLO = 59
PRECIO_MAXIMO_ARREGLO = 99
PUNTOS_POR_PRIORIDAD = {
    "baja": 3,
    "media": 8,
    "alta": 15,
}


def calcular_precio_arreglo(checks: list[dict]) -> int:
    """
    Precio orientativo de que Pipo aplique las soluciones en vez del
    dueño del negocio. Se calcula a partir de los checks del escaneo
    (no de las soluciones interpretadas por IA), así que está disponible
    desde el momento del pedido, sin depender de haber llamado antes al
    botón de soluciones.
    """
    incremento = sum(
        PUNTOS_POR_PRIORIDAD.get(check["prioridad"], 0)
        for check in checks
        if check["estado"] != "verde"
    )
    return min(PRECIO_MAXIMO_ARREGLO, PRECIO_BASE_ARREGLO + incremento)
