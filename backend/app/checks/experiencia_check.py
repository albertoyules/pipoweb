"""
Check de experiencia de cliente: lo que un dueño de negocio comprueba
él mismo en su móvil en treinta segundos.

Categoría: Clientes y visibilidad (ver app/puntuacion.py, FAMILIAS).
Naturaleza: 100% pasivo (verde). Solo lee el HTML público de la home,
más una petición a la variante www del dominio para ver si también
responde. Es lo mismo que haría un cliente escribiendo la dirección.

Por qué existe: el resto de checks son de informático (cabeceras, SPF,
DNSSEC). Estos son los que el dueño de un taller entiende sin traducción
y le duelen en la caja:

- ¿Se ve bien en el móvil? (etiqueta viewport)
- ¿Se puede llamar o escribir por WhatsApp desde la web con un toque?
- ¿Tiene icono propio en la pestaña del navegador? (favicon)
- ¿Algún formulario manda los datos del cliente sin cifrar?
- ¿Pesa demasiado la página?
- Si alguien escribe www.tunegocio.es, ¿también llega?
"""

import re

import httpx
from bs4 import BeautifulSoup

# A partir de aquí el HTML solo (sin contar imágenes ni scripts) ya es
# lo bastante gordo como para notarse en un móvil con mala cobertura.
PESO_HTML_AVISO_KB = 400

TIMEOUT_WWW = 4.0


def _valor_rel(enlace) -> str:
    """
    El atributo rel de un <link>, siempre como texto en minúsculas.
    BeautifulSoup lo devuelve como lista (rel="shortcut icon" son dos
    valores), pero según la versión puede llegar como cadena suelta.
    """
    rel = enlace.get("rel") or []
    texto = " ".join(rel) if isinstance(rel, (list, tuple)) else str(rel)
    return texto.lower()


async def comprobar_experiencia(pagina: dict, dominio: str) -> dict:
    """
    Recibe la home ya descargada (ver pagina.py) para no volver a
    pedirla, y hace una única petición extra a la variante www.
    """
    if not pagina["ok"]:
        return _resultado(
            estado="sin_datos",
            prioridad="baja",
            detalle=f"No hemos podido leer la web para revisar la experiencia de cliente ({pagina['error']}). No cuenta para la nota.",
        )

    soup = BeautifulSoup(pagina["html"], "html.parser")
    graves: list[str] = []
    menores: list[str] = []

    # --- ¿Se ve bien en el móvil? ---
    viewport = soup.find("meta", attrs={"name": re.compile(r"^viewport$", re.I)})
    tiene_viewport = viewport is not None and "width" in (viewport.get("content") or "").lower()
    if not tiene_viewport:
        graves.append(
            "la web no declara adaptarse al móvil (falta la etiqueta viewport), así que en un teléfono "
            "se verá diminuta y habrá que ampliar con los dedos para leerla"
        )

    # --- ¿Se puede contactar con un toque? ---
    enlaces = soup.find_all("a", href=True)
    hrefs = [enlace["href"].strip().lower() for enlace in enlaces]
    tiene_telefono = any(h.startswith("tel:") for h in hrefs)
    tiene_whatsapp = any("wa.me" in h or "api.whatsapp.com" in h for h in hrefs)
    tiene_email = any(h.startswith("mailto:") for h in hrefs)
    if not (tiene_telefono or tiene_whatsapp):
        menores.append(
            "no hay ningún teléfono ni WhatsApp pulsable: desde el móvil, quien quiera llamar "
            "tiene que copiar el número a mano"
        )

    # --- Formularios que mandan datos sin cifrar ---
    formularios_inseguros = [
        form for form in soup.find_all("form")
        if (form.get("action") or "").strip().lower().startswith("http://")
    ]
    if formularios_inseguros:
        graves.append(
            f"{len(formularios_inseguros)} formulario(s) envían lo que escribe el cliente por una "
            "conexión sin cifrar (http://), incluidos su nombre, teléfono o email"
        )

    # --- Favicon ---
    # Ojo: no vale filtrar con soup.find("link", rel=lambda ...). BeautifulSoup
    # trata "rel" como atributo de varios valores y no le pasa a la función lo
    # que uno espera, así que ese filtro no encontraba NUNCA el favicon (lo
    # descubrió el test test_se_detecta_el_telefono_pulsable). Se recorren los
    # <link> a mano, que además cubre rel="shortcut icon" y "apple-touch-icon".
    tiene_favicon = any("icon" in _valor_rel(enlace) for enlace in soup.find_all("link"))
    if not tiene_favicon:
        menores.append("no hay icono propio (favicon): en las pestañas del navegador aparece un papel en blanco")

    # --- Peso del HTML ---
    peso_kb = round(len(pagina["html"].encode("utf-8")) / 1024)
    if peso_kb > PESO_HTML_AVISO_KB:
        menores.append(
            f"el texto de la página pesa {peso_kb} KB antes de contar imágenes, bastante más de lo "
            "habitual: en móviles con mala cobertura se nota al cargar"
        )

    # --- www / sin www ---
    www_ok = await _responde_variante_www(dominio)
    if www_ok is False:
        menores.append(
            "la otra forma de escribir la dirección (con o sin 'www.') no responde: quien la teclee "
            "así verá un error en vez de tu web"
        )

    datos = {
        "adaptada_a_movil": tiene_viewport,
        "telefono_pulsable": tiene_telefono,
        "whatsapp_pulsable": tiene_whatsapp,
        "email_pulsable": tiene_email,
        "tiene_favicon": tiene_favicon,
        "formularios_sin_cifrar": len(formularios_inseguros),
        "peso_html_kb": peso_kb,
        "variante_www_responde": www_ok,
    }

    return _evaluar(graves, menores, datos)


async def _responde_variante_www(dominio: str) -> bool | None:
    """
    Si el dominio es "tunegocio.es", prueba "www.tunegocio.es" (y al
    revés). Devuelve None si no se pudo comprobar, para no acusar a
    nadie por un fallo de red nuestro.
    """
    alterno = dominio[4:] if dominio.startswith("www.") else f"www.{dominio}"
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=TIMEOUT_WWW) as cliente:
            respuesta = await cliente.get(f"https://{alterno}")
    except httpx.RequestError:
        return False
    return respuesta.status_code < 400


def _evaluar(graves: list[str], menores: list[str], datos: dict) -> dict:
    """
    Los problemas se separan por gravedad en vez de contarse todos
    iguales: que no se vea en el móvil o que un formulario mande datos
    sin cifrar son cosas que cuestan clientes hoy; que falte el favicon,
    no.
    """
    if graves:
        return _resultado(
            estado="rojo",
            prioridad="alta",
            detalle="Hay problemas que te están costando clientes: " + "; ".join(graves) + ".",
            datos=datos,
        )

    if menores:
        return _resultado(
            estado="ambar",
            prioridad="media",
            detalle="Detalles que conviene pulir: " + "; ".join(menores) + ".",
            datos=datos,
        )

    return _resultado(
        estado="verde",
        prioridad="baja",
        detalle="La web se adapta al móvil, se puede contactar con un toque y los formularios van cifrados.",
        datos=datos,
    )


def _resultado(estado: str, prioridad: str, detalle: str, datos: dict | None = None) -> dict:
    """Mismo formato común que usa el resto de checks (ver ssl_check.py)."""
    return {
        "check": "experiencia",
        "estado": estado,
        "prioridad": prioridad,
        "detalle": detalle,
        "datos": datos or {},
    }
