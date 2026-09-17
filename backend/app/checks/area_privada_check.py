"""
Check condicional: exposición de la puerta de acceso a un área
privada (panel de cliente, backoffice, wp-admin...). Solo se ejecuta
si perfil_sitio.py detecta tiene_login=True (ver scanner.py) — no
tiene sentido preguntar esto a una web sin ninguna zona de acceso.

Categoría: seguridad del acceso (ver app/puntuacion.py, FAMILIAS).
Naturaleza: 100% pasivo (verde). Las cabeceras de seguridad relevantes
(CSP, HSTS, X-Frame-Options) ya las comprueba headers_check.py para
CUALQUIER web, así que este check no las repite — se centra en lo
específico de tener una puerta de acceso: si esa puerta aparece
enlazada desde la propia home sin ningún "noindex" cerca, cualquier
buscador puede indexarla y ponerla a un clic de cualquiera.

IMPORTANTE — lo que este check NO hace, a propósito: no adivina rutas
como /wp-admin o /admin pidiéndolas directamente. Eso es justo lo que
hace archivos_expuestos.py, y por eso ESE check es ámbar y solo se
activa con consentimiento explícito (ver su docstring) — pedir rutas
que nadie nos ha publicado se lee en un log de servidor como "esto
parece un escáner", aunque sea legal. Este check solo mira si el
ENLACE ya está en el HTML público que cualquier visitante ve, que es
justo lo mismo que ya hace perfil_sitio.py para detectar tiene_login.
"""

from bs4 import BeautifulSoup

# Mismas rutas que perfil_sitio.py usa para detectar tiene_login — se
# repiten aquí (no se importan) porque el criterio de "está indexable"
# es más estricto: aquí además importa si hay algún <meta robots
# noindex> cerca, algo que perfil_sitio.py no necesita saber.
RUTAS_LOGIN = ("/wp-login.php", "/mi-cuenta", "/my-account", "/login", "/acceso", "/area-cliente", "/area-privada", "/wp-admin")


def comprobar_area_privada(pagina: dict) -> dict:
    """
    Recibe la home ya descargada (ver pagina.py) para no volver a
    pedirla. Solo se llama cuando perfil_sitio.py ya ha detectado
    tiene_login=True — scanner.py decide si esta función se lanza.
    """
    if not pagina["ok"]:
        return _resultado(
            estado="sin_datos",
            prioridad="baja",
            detalle=f"No hemos podido leer la web para revisar el acceso privado ({pagina['error']}). No cuenta para la nota.",
        )

    soup = BeautifulSoup(pagina["html"], "html.parser")

    enlaces_a_login = [
        enlace["href"]
        for enlace in soup.find_all("a", href=True)
        if any(ruta in enlace["href"].lower() for ruta in RUTAS_LOGIN)
    ]

    meta_robots = soup.find("meta", attrs={"name": "robots"})
    contenido_robots = (meta_robots.get("content", "") if meta_robots else "").lower()
    pagina_tiene_noindex = "noindex" in contenido_robots

    # Un formulario de login visible en la propia home (no solo un
    # enlace a otra página) es la situación más expuesta: cualquiera
    # que visite la web ve la puerta directamente, sin ni siquiera
    # tener que seguir un enlace.
    tiene_formulario_login_en_home = any(
        formulario.find("input", attrs={"type": "password"}) for formulario in soup.find_all("form")
    )

    datos = {
        "ruta_login_enlazada": enlaces_a_login[0] if enlaces_a_login else None,
        "pagina_tiene_noindex": pagina_tiene_noindex,
        "formulario_login_en_home": tiene_formulario_login_en_home,
    }

    return _evaluar(datos)


def _evaluar(datos: dict) -> dict:
    if datos["formulario_login_en_home"] and not datos["pagina_tiene_noindex"]:
        return _resultado(
            estado="ambar",
            prioridad="media",
            detalle=(
                "La página de acceso está indexable por buscadores y el formulario de inicio de "
                "sesión es visible sin ninguna barrera previa. No es un fallo grave por sí solo, "
                "pero facilita que la puerta de acceso aparezca en resultados de búsqueda."
            ),
            datos=datos,
        )

    if datos["ruta_login_enlazada"] and not datos["pagina_tiene_noindex"]:
        return _resultado(
            estado="verde",
            prioridad="baja",
            detalle=(
                "Se detecta un enlace a la zona de acceso. Es normal y esperable que exista: lo "
                "importante es que el resto de checks de seguridad (cabeceras, cifrado) estén en verde."
            ),
            datos=datos,
        )

    return _resultado(
        estado="verde",
        prioridad="baja",
        detalle="No se detecta ninguna señal adicional de exposición del acceso privado en la home.",
        datos=datos,
    )


def _resultado(estado: str, prioridad: str, detalle: str, datos: dict | None = None) -> dict:
    """Mismo formato común que usa el resto de checks (ver ssl_check.py)."""
    return {
        "check": "area_privada",
        "estado": estado,
        "prioridad": prioridad,
        "detalle": detalle,
        "datos": datos or {},
    }
