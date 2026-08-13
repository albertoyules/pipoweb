"""
Cálculo de la puntuación del informe (0-100) y del resumen con semáforo.

Deliberadamente NO usa IA. La nota tiene que ser reproducible: los mismos
datos de entrada deben dar siempre la misma nota, sin que dependa de cómo
esté de "inspirado" un modelo de lenguaje ese día. La IA (ver app/ia/)
solo pone las palabras; el número lo pone esta fórmula fija.

REESCRITO EL 13 AGO 2026. Antes todos los checks pesaban lo mismo y el
peor de todos decidía el color global. El resultado, medido sobre los
escaneos reales guardados: TODAS las webs salían en rojo, incluida la de
Pipo. Un <title> tres caracteres más largo de lo recomendado teñía de
"crítico" el mismo informe que avisaba de un certificado caducado, así
que el semáforo dejaba de informar y el producto se leía como venta del
miedo. Ahora hay dos ideas nuevas:

1. PESOS: no todos los checks valen igual en la nota. Un certificado
   roto no puede pesar lo mismo que una etiqueta Open Graph.
2. FAMILIAS: los checks se agrupan en seguridad, cumplimiento y
   clientes. Dentro de seguridad sigue mandando el eslabón más débil
   (ahí es donde tiene sentido), pero un detalle de SEO ya no puede
   pintar de rojo el informe entero.
"""

# Puntos que aporta cada check según su color. Números redondos y fáciles
# de justificar ante un cliente que pregunte "¿por qué tengo un 62?".
PUNTOS_POR_ESTADO = {
    "verde": 100,
    "ambar": 60,
    "rojo": 20,
}

# Cuánto pesa cada check en la nota final. 3 = te puede costar dinero o
# un disgusto legal mañana; 2 = importa de verdad pero no es urgente;
# 1 = está bien tenerlo, no es un problema si falta.
PESOS = {
    # Seguridad
    "ssl": 3,
    "archivos_expuestos": 3,
    "headers": 2,
    "mixed_content": 2,
    "tecnologia": 2,
    "dns": 2,
    "dominio": 1,
    "whois": 1,
    # Cumplimiento
    "privacidad": 3,
    "accesibilidad": 1,
    # Clientes
    "seo": 2,
    "experiencia": 2,
    "rendimiento": 1,
}
PESO_POR_DEFECTO = 1

# Las tres familias, con el nombre que se le enseña al cliente. El orden
# importa: es el que usa el informe para pintarlas.
FAMILIAS = (
    ("seguridad", "Seguridad", ("ssl", "headers", "mixed_content", "tecnologia", "archivos_expuestos", "dns", "dominio", "whois")),
    ("cumplimiento", "Cumplimiento legal", ("privacidad", "accesibilidad")),
    ("clientes", "Clientes y visibilidad", ("seo", "experiencia", "rendimiento")),
)

# En qué familias un rojo tiñe de rojo el informe entero. En seguridad y
# en cumplimiento sí: ahí el eslabón débil pesa más que la media, y un
# problema legal no se compensa teniendo buen SEO. En "clientes" no: que
# la web cargue lenta es importante, pero no es una emergencia.
FAMILIAS_CRITICAS = {"seguridad", "cumplimiento"}

# Dentro incluso de las familias críticas, un rojo en un check de peso 1
# (detalle menor) no basta para teñir el informe entero: sube a ámbar.
PESO_MINIMO_PARA_ROJO_GLOBAL = 2


def peso_de(nombre_check: str) -> int:
    """Cuánto pesa un check en la nota. Los que no estén listados, 1."""
    return PESOS.get(nombre_check, PESO_POR_DEFECTO)


def calcular_puntuacion(checks: list[dict]) -> int:
    """
    Nota actual: media de los puntos de cada check, ponderada por su
    peso. Con 0 checks devuelve 0 en vez de dividir por cero.
    """
    if not checks:
        return 0
    peso_total = sum(peso_de(check["check"]) for check in checks)
    puntos = sum(PUNTOS_POR_ESTADO[check["estado"]] * peso_de(check["check"]) for check in checks)
    return round(puntos / peso_total)


def calcular_puntuacion_potencial(checks: list[dict], nombres_resueltos: set[str]) -> int:
    """
    Puntuación "si se aplican las soluciones propuestas": para los checks
    cuyo nombre está en nombres_resueltos, asumimos el mejor caso posible
    (pasan a verde) y recalculamos con la misma fórmula. Es una estimación
    optimista y se presenta como tal en el informe, nunca como una promesa.
    """
    if not checks:
        return 0
    peso_total = sum(peso_de(check["check"]) for check in checks)
    puntos = sum(
        (PUNTOS_POR_ESTADO["verde"] if check["check"] in nombres_resueltos else PUNTOS_POR_ESTADO[check["estado"]])
        * peso_de(check["check"])
        for check in checks
    )
    return round(puntos / peso_total)


def _peor_estado(estados: list[str]) -> str:
    """El color más grave de la lista. Sin datos, verde."""
    if "rojo" in estados:
        return "rojo"
    if "ambar" in estados:
        return "ambar"
    return "verde"


def _contar(checks: list[dict]) -> dict:
    conteo = {"verde": 0, "ambar": 0, "rojo": 0}
    for check in checks:
        conteo[check["estado"]] += 1
    return conteo


def resumir_checks(checks: list[dict]) -> dict:
    """
    El resumen que ve el cliente: nota global, semáforo global y el
    desglose por familias.

    El color global se decide así:
    - Rojo si hay un rojo en un check importante (peso >= 2) de una
      familia crítica (seguridad o cumplimiento). Eso es lo que de
      verdad merece la palabra "crítico".
    - Ámbar si hay cualquier otro rojo, o cualquier ámbar.
    - Verde si está todo en verde.
    """
    por_familia = []
    for clave, nombre, nombres_checks in FAMILIAS:
        de_esta_familia = [c for c in checks if c["check"] in nombres_checks]
        if not de_esta_familia:
            continue
        por_familia.append(
            {
                "clave": clave,
                "nombre": nombre,
                "estado": _peor_estado([c["estado"] for c in de_esta_familia]),
                "puntuacion": calcular_puntuacion(de_esta_familia),
                "conteo": _contar(de_esta_familia),
                "checks": [c["check"] for c in de_esta_familia],
            }
        )

    familia_de = {
        nombre_check: clave for clave, _, nombres in FAMILIAS for nombre_check in nombres
    }

    hay_rojo_grave = any(
        check["estado"] == "rojo"
        and familia_de.get(check["check"]) in FAMILIAS_CRITICAS
        and peso_de(check["check"]) >= PESO_MINIMO_PARA_ROJO_GLOBAL
        for check in checks
    )
    conteo = _contar(checks)

    if hay_rojo_grave:
        estado_global = "rojo"
    elif conteo["rojo"] or conteo["ambar"]:
        estado_global = "ambar"
    else:
        estado_global = "verde"

    return {
        "estado_global": estado_global,
        "puntuacion": calcular_puntuacion(checks),
        "conteo": conteo,
        "familias": por_familia,
    }


def comparar_escaneos(anterior: dict, actual: dict) -> dict:
    """
    Qué ha cambiado desde el escaneo anterior del mismo dominio.

    Es el 80% del valor del futuro nivel de vigilancia sin necesitar
    todavía ninguna tarea programada: aparece solo cuando alguien vuelve
    a analizar una web que ya habíamos visto. Y es la prueba de que un
    arreglo funcionó, que es justo lo que hay que enseñar después de
    cobrarlo.
    """
    estados_antes = {c["check"]: c["estado"] for c in anterior.get("checks", [])}
    nota_antes = anterior.get("resumen", {}).get("puntuacion")
    if nota_antes is None:  # escaneos guardados antes de que la nota viviera en el resumen
        nota_antes = calcular_puntuacion(anterior.get("checks", []))
    nota_ahora = actual["resumen"]["puntuacion"]

    orden = {"rojo": 0, "ambar": 1, "verde": 2}
    mejoras, empeoramientos = [], []
    for check in actual["checks"]:
        antes = estados_antes.get(check["check"])
        if antes is None or antes == check["estado"]:
            continue
        cambio = {"check": check["check"], "antes": antes, "ahora": check["estado"]}
        if orden[check["estado"]] > orden[antes]:
            mejoras.append(cambio)
        else:
            empeoramientos.append(cambio)

    return {
        "fecha_anterior": anterior.get("fecha"),
        "nota_anterior": nota_antes,
        "nota_actual": nota_ahora,
        "diferencia": nota_ahora - nota_antes,
        "mejoras": mejoras,
        "empeoramientos": empeoramientos,
    }


# Precio estimado del servicio "lo arreglamos nosotros" (ver CLAUDE.md,
# P2). Igual que la nota, esto NUNCA lo calcula la IA: sería fácil que un
# modelo "regalara" un precio bajo para parecer más simpático, o al
# revés. Puntos por dificultad real de arreglar cada cosa, no por lo
# grave que sea (un check rojo puede ser fácil de arreglar y uno ámbar
# puede no serlo) — solo cuentan los checks que no están ya en verde.
#
# El rango subió de 59-99€ a 89-149€ el 13 ago 2026, al pasar a ser el
# producto principal en vez de un añadido: es trabajo manual de una
# persona, y por debajo de eso no compensa el tiempo que lleva.
PRECIO_BASE_ARREGLO = 89
PRECIO_MAXIMO_ARREGLO = 149
# Calibrado para que una web normal (con media docena de cosas a
# corregir) caiga por el medio del rango y no siempre en el tope: si
# todas las webs dieran 149€, el número dejaría de significar nada.
PUNTOS_POR_PRIORIDAD = {
    "baja": 2,
    "media": 5,
    "alta": 9,
}


def calcular_precio_arreglo(checks: list[dict]) -> int:
    """
    Precio orientativo de que Pipo aplique las soluciones en vez del
    dueño del negocio. Se calcula a partir de los checks del escaneo
    (no de las soluciones interpretadas por IA), así que está disponible
    desde el momento de la solicitud, sin depender de haber generado
    antes las soluciones.
    """
    incremento = sum(
        PUNTOS_POR_PRIORIDAD.get(check["prioridad"], 0)
        for check in checks
        if check["estado"] != "verde"
    )
    return min(PRECIO_MAXIMO_ARREGLO, PRECIO_BASE_ARREGLO + incremento)
