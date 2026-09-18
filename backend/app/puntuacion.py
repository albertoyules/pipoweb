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

AÑADIDO EL 14 AGO 2026: un check puede venir en estado "sin_datos" (hoy
solo lo usa whois_check.py cuando el registro del dominio no deja
consultar la caducidad). No es ni un aprobado ni un suspenso — es "no
lo sabemos" — así que se excluye del todo del cálculo de la nota: ni su
peso cuenta en el total, ni aporta ni resta puntos. Antes se marcaba
verde "para no acusar en falso", pero eso mentía por el otro lado
(sumaba puntos que no le correspondían) y el semáforo pintaba de verde
algo que en realidad no se había podido comprobar.
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
    # area_privada: peso 2, como headers — expone la puerta de acceso,
    # pero no es tan grave por sí solo como un certificado roto. Solo
    # aparece cuando perfil_sitio.py detecta tiene_login (ver
    # scanner.py); no penaliza a una web sin ninguna zona de acceso.
    "area_privada": 2,
    # Cumplimiento
    "privacidad": 3,
    "accesibilidad": 1,
    # ecommerce: peso 3, como privacidad — mezcla seguridad del pago
    # (HTTPS roto) y cumplimiento (condiciones de venta obligatorias
    # en España). Solo aparece si tiene_checkout=True.
    "ecommerce": 3,
    # Clientes
    "seo": 2,
    "experiencia": 2,
    "rendimiento": 1,
}
PESO_POR_DEFECTO = 1

# Las tres familias, con el nombre que se le enseña al cliente. El orden
# importa: es el que usa el informe para pintarlas. ecommerce y
# area_privada son checks condicionales (ver perfil_sitio.py): solo
# aparecen en checks[] cuando el perfil detectado los activa, así que
# listarlos aquí no penaliza a quien no los tiene — simplemente no
# aparecen en esa fila del desglose (ver resumir_checks).
FAMILIAS = (
    ("seguridad", "Seguridad", ("ssl", "headers", "mixed_content", "tecnologia", "archivos_expuestos", "dns", "dominio", "whois", "area_privada")),
    ("cumplimiento", "Cumplimiento legal", ("privacidad", "accesibilidad", "ecommerce")),
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

    Los checks en "sin_datos" se excluyen del todo: ni su peso entra en
    el total, ni aportan puntos. Si TODOS los checks recibidos están en
    "sin_datos" (caso de borde, no debería pasar en un escaneo real),
    también devuelve 0 en vez de dividir por cero.
    """
    contables = [c for c in checks if c["estado"] != "sin_datos"]
    if not contables:
        return 0
    peso_total = sum(peso_de(check["check"]) for check in contables)
    puntos = sum(PUNTOS_POR_ESTADO[check["estado"]] * peso_de(check["check"]) for check in contables)
    return round(puntos / peso_total)


def calcular_puntuacion_potencial(checks: list[dict], nombres_resueltos: set[str]) -> int:
    """
    Puntuación "si se aplican las soluciones propuestas": para los checks
    cuyo nombre está en nombres_resueltos, asumimos el mejor caso posible
    (pasan a verde) y recalculamos con la misma fórmula. Es una estimación
    optimista y se presenta como tal en el informe, nunca como una promesa.

    Los "sin_datos" se excluyen igual que en calcular_puntuacion: no hay
    "solución" posible para un dato que no se puede consultar, así que
    nunca deberían llegar aquí dentro de nombres_resueltos (soluciones.py
    ya los aparta antes de pedirle nada a la IA), pero se filtran también
    aquí por si acaso, para que la fórmula sea igual de fiable la llame
    quien la llame.
    """
    contables = [c for c in checks if c["estado"] != "sin_datos"]
    if not contables:
        return 0
    peso_total = sum(peso_de(check["check"]) for check in contables)
    puntos = sum(
        (PUNTOS_POR_ESTADO["verde"] if check["check"] in nombres_resueltos else PUNTOS_POR_ESTADO[check["estado"]])
        * peso_de(check["check"])
        for check in contables
    )
    return round(puntos / peso_total)


def _peor_estado(estados: list[str]) -> str:
    """
    El color más grave de la lista, para pintar una familia o el global.
    "sin_datos" no cuenta aquí tampoco: no es ni el mejor ni el peor
    caso, así que una familia nunca se pinta de gris solo porque uno de
    sus checks no se pudo comprobar — se pinta del peor de los que SÍ se
    pudieron comprobar. Sin ningún dato real, verde (nada que reprochar).
    """
    estados_reales = [e for e in estados if e != "sin_datos"]
    if "rojo" in estados_reales:
        return "rojo"
    if "ambar" in estados_reales:
        return "ambar"
    return "verde"


def _contar(checks: list[dict]) -> dict:
    conteo = {"verde": 0, "ambar": 0, "rojo": 0, "sin_datos": 0}
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
        # "sin_datos" no tiene un lugar en la escala rojo/ámbar/verde: no
        # se puede decir si pasar de "no lo sabíamos" a "verde" es una
        # mejora o si es al revés. Se omite del comparador en vez de
        # forzarlo a un orden que no le corresponde.
        if "sin_datos" in (antes, check["estado"]):
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

# Recargo por complejidad ESTRUCTURAL del sitio (18 sep 2026), no por
# cuántos checks fallan — eso ya lo cubre PUNTOS_POR_PRIORIDAD y el tope
# PRECIO_MAXIMO_ARREGLO de arriba, que no se tocan. Una tienda con
# pasarela de pago real es más delicada de tocar que un formulario de
# contacto, tenga los mismos fallos o no: hay que probar que el cambio
# no rompa una venta de verdad. Un sitio grande multiplica el tiempo de
# verificación porque el mismo fallo puede repetirse en muchas páginas.
# Se suma DESPUÉS de aplicar el tope de dificultad, no antes: si no, una
# web normal muy rota y una tienda muy rota acabarían en el mismo tope y
# el recargo no significaría nada en el caso que más lo necesita.
RECARGO_TIENDA = 20
RECARGO_SITIO_GRANDE = 10
PAGINAS_SITIO_GRANDE = 30


def calcular_precio_arreglo(checks: list[dict], perfil_sitio: dict | None = None) -> int:
    """
    Precio orientativo de que Pipo aplique las soluciones en vez del
    dueño del negocio. Se calcula a partir de los checks del escaneo
    (no de las soluciones interpretadas por IA), así que está disponible
    desde el momento de la solicitud, sin depender de haber generado
    antes las soluciones.

    perfil_sitio es opcional (compatible con escaneos guardados antes
    del 18 sep 2026, que no lo tienen): sin él, el precio es el de
    siempre, solo por dificultad de los checks.
    """
    # "sin_datos" queda fuera igual que en la nota: si una web no se deja
    # descargar, seis checks caen ahí y le añadían puntos al precio por un
    # trabajo que nadie va a hacer, porque no hay nada roto que arreglar.
    incremento = sum(
        PUNTOS_POR_PRIORIDAD.get(check["prioridad"], 0)
        for check in checks
        if check["estado"] not in ("verde", "sin_datos")
    )
    precio_por_dificultad = min(PRECIO_MAXIMO_ARREGLO, PRECIO_BASE_ARREGLO + incremento)

    senales = (perfil_sitio or {}).get("senales") or {}
    recargo = 0
    if senales.get("tiene_checkout"):
        recargo += RECARGO_TIENDA
    paginas_aprox = (perfil_sitio or {}).get("tamano", {}).get("paginas_aprox")
    if paginas_aprox is not None and paginas_aprox > PAGINAS_SITIO_GRANDE:
        recargo += RECARGO_SITIO_GRANDE

    return precio_por_dificultad + recargo
