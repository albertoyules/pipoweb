"""
Check de archivos sensibles expuestos públicamente.

Categoría: Seguridad básica (ver PIPO_PLANNING.md, sección 2).
Naturaleza: ÁMBAR, no verde como el resto. No vulneramos ninguna
medida de seguridad (no hay login que saltarse, no probamos
credenciales, no explotamos nada): solo pedimos rutas concretas, algo
que cualquier visitante o bot puede hacer. Pero a diferencia de los
demás checks, aquí SÍ estamos adivinando rutas que nadie nos ha
publicado, y eso se lee en un log de servidor como "esto parece un
escáner". Por eso:

- Lista corta y fija de rutas, una única petición por ruta, nunca en bucle.
- User-Agent identificable (PipoBot/1.0): quien no se esconde no
  parece un atacante.
- Solo se guarda el código de estado (200/404). Nunca se descarga ni
  se almacena el contenido del archivo.

DECISIÓN DE PRODUCTO (no de este módulo): este check debe quedar
fuera del escaneo gratis y solo ejecutarse cuando el usuario haya
marcado el checkbox de consentimiento de titularidad (ver planning,
punto 8). Ese control se aplica en la capa que orquesta el escaneo,
no aquí — este módulo solo sabe hacer el check en sí.
"""

import httpx

# El User-Agent vive en pagina.py, el módulo que centraliza las
# descargas. Antes había aquí una copia que apuntaba a pipo.es, un
# dominio que no es de Pipo: un bot que se identifica con una URL
# falsa es peor que uno que no se identifica.
from app.checks.pagina import USER_AGENT_PIPO  # noqa: E402

# Lista corta y fija a propósito. Backups y archivos de configuración
# clásicos que a veces quedan expuestos por error al desplegar.
RUTAS_SENSIBLES = [
    "/.env",
    "/.git/config",
    "/wp-config.php.bak",
    "/backup.zip",
    "/.DS_Store",
    "/config.php.bak",
]


async def comprobar_archivos_expuestos(dominio: str, timeout: float = 4.0) -> dict:
    """
    Para cada ruta de RUTAS_SENSIBLES, hace UNA petición HEAD (pide
    solo las cabeceras, no el cuerpo del archivo, más ligero y
    suficiente para saber si existe) y anota si respondió 200 (existe
    y es público) o cualquier otra cosa (no expuesto).
    """
    url_base = f"https://{dominio}"
    expuestos = []

    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=False,  # una redirección a la home en vez de un 404 no cuenta como "expuesto"
            headers={"User-Agent": USER_AGENT_PIPO},
        ) as cliente:
            for ruta in RUTAS_SENSIBLES:
                try:
                    respuesta = await cliente.head(url_base + ruta)
                    if respuesta.status_code == 200:
                        expuestos.append(ruta)
                except httpx.RequestError:
                    # Un fallo puntual en una ruta no detiene el resto;
                    # simplemente no la contamos como expuesta.
                    continue
    except Exception as error:  # noqa: BLE001 - fallo de conexión general al dominio
        return _resultado(
            estado="rojo",
            prioridad="alta",
            detalle=f"No se ha podido conectar con el dominio para revisar archivos expuestos ({error}).",
        )

    datos = {"rutas_comprobadas": len(RUTAS_SENSIBLES), "expuestos": expuestos}

    if not expuestos:
        return _resultado(
            estado="verde",
            prioridad="baja",
            detalle="No se detecta ninguno de los archivos sensibles habituales expuesto públicamente.",
            datos=datos,
        )

    return _resultado(
        estado="rojo",
        prioridad="alta",
        detalle=f"Hay {len(expuestos)} archivo(s) sensible(s) accesibles públicamente: {', '.join(expuestos)}.",
        datos=datos,
    )


def _resultado(estado: str, prioridad: str, detalle: str, datos: dict | None = None) -> dict:
    """Mismo formato común que usa el resto de checks (ver ssl_check.py)."""
    return {
        "check": "archivos_expuestos",
        "estado": estado,
        "prioridad": prioridad,
        "detalle": detalle,
        "datos": datos or {},
    }
