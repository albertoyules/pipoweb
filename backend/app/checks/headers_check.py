"""
Check de cabeceras de seguridad HTTP.

Categoría: Seguridad básica (ver PIPO_PLANNING.md, sección 2).
Naturaleza: 100% pasivo (verde). Hacemos una única petición HTTP GET
normal, la misma que hace un navegador al entrar en la web, y leemos
las cabeceras que el servidor decide mandar en su respuesta. No
forzamos nada ni probamos rutas que no existan.

Qué comprobamos: la presencia de 4 cabeceras de seguridad estándar.
Cada una protege contra un tipo de ataque distinto; no tenerlas no
significa que la web esté "hackeada", significa que le falta una capa
de protección recomendada.
"""

import httpx

# Nombre de la cabecera -> qué protege, en una frase que se pueda
# mostrar tal cual en el informe.
CABECERAS_ESPERADAS = {
    "strict-transport-security": "Fuerza siempre HTTPS, evita que alguien rebaje la conexión a HTTP sin cifrar.",
    "x-frame-options": "Evita que otra web te incruste en un iframe invisible (clickjacking).",
    "content-security-policy": "Limita qué código puede ejecutarse en la página si hay una vulnerabilidad.",
    "x-content-type-options": "Evita que el navegador \"adivine\" mal el tipo de un archivo y lo ejecute.",
}


async def comprobar_headers(dominio: str, timeout: float = 5.0) -> dict:
    """
    Pide la home del dominio por HTTPS y examina qué cabeceras de
    seguridad trae la respuesta. Devuelve el mismo formato que el
    resto de checks: estado, prioridad, detalle y datos.
    """
    url = f"https://{dominio}"

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as cliente:
            respuesta = await cliente.get(url)
    except httpx.RequestError as error:
        return _resultado(
            estado="rojo",
            prioridad="alta",
            detalle=f"No se ha podido acceder a la web para revisar sus cabeceras ({error}).",
        )

    # httpx.Headers ya ignora mayúsculas/minúsculas al comparar, igual
    # que hace el propio protocolo HTTP.
    presentes = []
    faltantes = []
    for cabecera, explicacion in CABECERAS_ESPERADAS.items():
        if cabecera in respuesta.headers:
            presentes.append(cabecera)
        else:
            faltantes.append({"cabecera": cabecera, "riesgo": explicacion})

    datos = {
        "url_analizada": str(respuesta.url),
        "presentes": presentes,
        "faltantes": [f["cabecera"] for f in faltantes],
    }

    num_faltantes = len(faltantes)

    if num_faltantes == 0:
        return _resultado(
            estado="verde",
            prioridad="baja",
            detalle="Las 4 cabeceras de seguridad recomendadas están presentes.",
            datos=datos,
        )

    if num_faltantes <= 2:
        nombres = ", ".join(f["cabecera"] for f in faltantes)
        return _resultado(
            estado="ambar",
            prioridad="media",
            detalle=f"Faltan {num_faltantes} cabeceras de seguridad recomendadas: {nombres}.",
            datos=datos,
        )

    nombres = ", ".join(f["cabecera"] for f in faltantes)
    return _resultado(
        estado="rojo",
        prioridad="alta",
        detalle=f"Faltan la mayoría de cabeceras de seguridad recomendadas: {nombres}.",
        datos=datos,
    )


def _resultado(estado: str, prioridad: str, detalle: str, datos: dict | None = None) -> dict:
    """Mismo formato común que usa el resto de checks (ver ssl_check.py)."""
    return {
        "check": "headers",
        "estado": estado,
        "prioridad": prioridad,
        "detalle": detalle,
        "datos": datos or {},
    }
