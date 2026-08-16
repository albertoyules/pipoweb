"""
Check de cabeceras de seguridad HTTP.

Categoría: Seguridad básica (ver PIPO_PLANNING.md, sección 2).
Naturaleza: 100% pasivo (verde). Hacemos una única petición HTTP GET
normal, la misma que hace un navegador al entrar en la web, y leemos
las cabeceras que el servidor decide mandar en su respuesta. No
forzamos nada ni probamos rutas que no existan.

Qué comprobamos:
- La presencia de 4 cabeceras de seguridad "core" (cuentan para el
  semáforo, igual que antes).
- Dos cabeceras adicionales recomendadas (Referrer-Policy,
  Permissions-Policy) y las flags de seguridad de las cookies que
  ponga el servidor — se muestran como aviso informativo, sin bajar
  el semáforo por sí solas, para no penalizar doble por cosas que
  las 4 cabeceras "core" ya cubren en la práctica.
- Si el servidor anuncia la versión exacta de su software en
  Server/X-Powered-By (p.ej. "Apache/2.4.41"), lo señalamos como fuga
  de información: no es grave por sí solo, pero le da a un atacante
  una pista gratis de qué vulnerabilidades conocidas probar primero.
"""

import httpx

from app.checks.pagina import USER_AGENT_PIPO

# Nombre de la cabecera -> qué protege, en una frase que se pueda
# mostrar tal cual en el informe.
CABECERAS_ESPERADAS = {
    "strict-transport-security": "Fuerza siempre HTTPS, evita que alguien rebaje la conexión a HTTP sin cifrar.",
    "x-frame-options": "Evita que otra web te incruste en un iframe invisible (clickjacking).",
    "content-security-policy": "Limita qué código puede ejecutarse en la página si hay una vulnerabilidad.",
    "x-content-type-options": "Evita que el navegador \"adivine\" mal el tipo de un archivo y lo ejecute.",
}

# Recomendadas pero no "core": no bajan el semáforo, solo se listan
# como aviso informativo en los datos del check.
CABECERAS_RECOMENDADAS = {
    "referrer-policy": "Controla cuánta información de la página de origen se envía al hacer clic en un enlace externo.",
    "permissions-policy": "Restringe qué funciones del navegador (cámara, ubicación...) puede usar la página.",
}

# Cabeceras que, si el servidor las manda con un número de versión,
# regalan información útil a un atacante.
CABECERAS_VERSION = ["server", "x-powered-by"]


def _cookies_sin_flags_seguras(respuesta: httpx.Response) -> list[str]:
    """
    httpx no expone Set-Cookie repetidas como lista directamente desde
    .headers (varias cookies pueden venir en líneas separadas), así que
    se lee de raw_headers para no perder ninguna. Solo miramos si
    faltan las flags — no leemos ni guardamos el valor de la cookie.
    """
    nombres_con_problema = []
    for clave, valor in respuesta.headers.raw:
        if clave.decode().lower() != "set-cookie":
            continue
        texto = valor.decode()
        nombre_cookie = texto.split("=", 1)[0].strip()
        texto_min = texto.lower()
        faltan = []
        if "secure" not in texto_min:
            faltan.append("Secure")
        if "httponly" not in texto_min:
            faltan.append("HttpOnly")
        if "samesite" not in texto_min:
            faltan.append("SameSite")
        if faltan:
            nombres_con_problema.append(f"{nombre_cookie} (falta {', '.join(faltan)})")
    return nombres_con_problema


async def comprobar_headers(dominio: str, timeout: float = 5.0) -> dict:
    """
    Pide la home del dominio por HTTPS y examina qué cabeceras de
    seguridad trae la respuesta. Devuelve el mismo formato que el
    resto de checks: estado, prioridad, detalle y datos.
    """
    url = f"https://{dominio}"

    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=timeout,
            headers={"User-Agent": USER_AGENT_PIPO},
        ) as cliente:
            respuesta = await cliente.get(url)
    except httpx.RequestError as error:
        # Mismo criterio que los checks de contenido (ver pagina.py): no
        # haber podido mirar no es lo mismo que estar mal, así que no
        # cuenta para la nota en vez de contar como el peor caso.
        return _resultado(
            estado="sin_datos",
            prioridad="baja",
            detalle=f"No hemos podido leer las cabeceras de la web ({error}). No cuenta para la nota.",
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

    recomendadas_faltantes = [c for c in CABECERAS_RECOMENDADAS if c not in respuesta.headers]
    cookies_inseguras = _cookies_sin_flags_seguras(respuesta)
    fuga_version = {
        cabecera: respuesta.headers[cabecera]
        for cabecera in CABECERAS_VERSION
        if cabecera in respuesta.headers and any(c.isdigit() for c in respuesta.headers[cabecera])
    }

    datos = {
        "url_analizada": str(respuesta.url),
        "presentes": presentes,
        "faltantes": [f["cabecera"] for f in faltantes],
        "recomendadas_faltantes": recomendadas_faltantes,
        "cookies_sin_flags_seguras": cookies_inseguras,
        "fuga_version_servidor": fuga_version,
    }

    avisos_extra = []
    if cookies_inseguras:
        avisos_extra.append(f"{len(cookies_inseguras)} cookie(s) sin todas las flags de seguridad")
    if fuga_version:
        avisos_extra.append(f"el servidor anuncia su versión exacta ({', '.join(fuga_version.values())})")
    nota_extra = f" Aviso aparte: {'; '.join(avisos_extra)}." if avisos_extra else ""

    num_faltantes = len(faltantes)

    if num_faltantes == 0:
        return _resultado(
            estado="verde",
            prioridad="baja",
            detalle=f"Las 4 cabeceras de seguridad recomendadas están presentes.{nota_extra}",
            datos=datos,
        )

    if num_faltantes <= 2:
        nombres = ", ".join(f["cabecera"] for f in faltantes)
        return _resultado(
            estado="ambar",
            prioridad="media",
            detalle=f"Faltan {num_faltantes} cabeceras de seguridad recomendadas: {nombres}.{nota_extra}",
            datos=datos,
        )

    nombres = ", ".join(f["cabecera"] for f in faltantes)
    return _resultado(
        estado="rojo",
        prioridad="alta",
        detalle=f"Faltan la mayoría de cabeceras de seguridad recomendadas: {nombres}.{nota_extra}",
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
