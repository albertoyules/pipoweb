"""
Check de caducidad del dominio (WHOIS).

Categoría: Salud del dominio (no es un check de seguridad estricto,
es un aviso de negocio). Naturaleza: 100% pasivo (verde). WHOIS es un
protocolo público por diseño (RFC 3912): cualquiera puede preguntar
"¿de quién es este dominio y cuándo caduca?" sin credenciales, es el
mismo dato que enseña cualquier buscador de WHOIS online.

Por qué importa: un dominio caducado dado de baja por descuido (no por
elección) se pierde — a veces para siempre, si alguien lo registra
antes de recuperarlo. Es uno de los sustos más tontos y evitables que
le puede pasar a un negocio pequeño.

Cómo se consulta: no hay un único servidor WHOIS ni un formato de
respuesta estándar — cada TLD tiene el suyo. Primero se pregunta a
whois.iana.org qué servidor es responsable del TLD del dominio, y
luego se le pregunta a ese servidor por el dominio en sí (mismo patrón
en dos pasos que usan la mayoría de clientes WHOIS).

Esto es más frágil que una consulta DNS normal: si no reconocemos el
formato de un TLD concreto, o el servidor no responde, se trata como
"no disponible" — nunca como un fallo del dominio en sí, porque la
limitación es nuestra, no suya.

CAMBIO DEL 14 AGO 2026 (aviso de un amigo de Alberto que hace esto mismo
en su estudio): antes "no disponible" se marcaba VERDE, con la idea de
"nunca acusar en falso". Pero eso miente por el otro lado — un punto
verde dice "comprobado, todo bien" cuando la verdad es "no lo sabemos",
y de paso SUMABA puntos a la nota que no le correspondían. La causa más
habitual de "no disponible" no es un fallo técnico nuestro: muchos
registros de dominios limitan o redactan estos datos por normativa de
protección de datos (el mismo espíritu del RGPD aplicado al WHOIS
público), así que a veces solo se puede saber con certeza consultando a
mano en la web del registrador. Ahora es un estado propio,
"sin_datos": ni verde ni rojo, no cuenta para la nota (ver
puntuacion.py) y se explica al cliente en vez de fingir que se comprobó.
"""

import re
import socket
from datetime import datetime, timezone

TIMEOUT_WHOIS = 5.0
SERVIDOR_IANA = "whois.iana.org"
DIAS_AVISO_CADUCIDAD = 30

PATRON_FECHA_CADUCIDAD = re.compile(
    r"(?:Registry Expiry Date|Registrar Registration Expiration Date|"
    r"Expiry Date|Expiration Date|expires|paid-till)\s*:\s*(.+)",
    re.IGNORECASE,
)

FORMATOS_FECHA = (
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
    "%d-%b-%Y",
    "%d/%m/%Y",
)


def _consultar_whois_crudo(servidor: str, consulta: str) -> str:
    with socket.create_connection((servidor, 43), timeout=TIMEOUT_WHOIS) as conexion:
        conexion.sendall((consulta + "\r\n").encode())
        trozos = []
        while True:
            trozo = conexion.recv(4096)
            if not trozo:
                break
            trozos.append(trozo)
    return b"".join(trozos).decode(errors="ignore")


def _servidor_whois_del_tld(dominio: str) -> str | None:
    """
    IANA no usa siempre el mismo nombre de campo para decir "el
    servidor autoritativo es este otro": los gTLD antiguos suelen usar
    "refer:", bastantes otros (como .org) usan "whois:". Se aceptan
    los dos.
    """
    tld = dominio.rsplit(".", 1)[-1]
    texto = _consultar_whois_crudo(SERVIDOR_IANA, tld)
    coincidencia = re.search(r"(?:refer|whois):\s*(\S+)", texto, re.IGNORECASE)
    return coincidencia.group(1) if coincidencia else None


def _extraer_fecha_caducidad(texto_whois: str) -> datetime | None:
    coincidencia = PATRON_FECHA_CADUCIDAD.search(texto_whois)
    if not coincidencia:
        return None
    texto_fecha = coincidencia.group(1).strip()
    for formato in FORMATOS_FECHA:
        try:
            fecha = datetime.strptime(texto_fecha, formato)
            return fecha if fecha.tzinfo else fecha.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def comprobar_whois(dominio: str) -> dict:
    """Función síncrona (sockets bloqueantes) — se manda a un hilo aparte desde scanner.py."""
    try:
        servidor_tld = _servidor_whois_del_tld(dominio)
        if not servidor_tld:
            return _resultado_no_disponible(dominio, "no se ha encontrado el servidor WHOIS de este dominio")

        texto_whois = _consultar_whois_crudo(servidor_tld, dominio)
    except (socket.timeout, socket.gaierror, OSError):
        return _resultado_no_disponible(dominio, "el servidor WHOIS no ha respondido a tiempo")

    fecha_caducidad = _extraer_fecha_caducidad(texto_whois)
    if fecha_caducidad is None:
        return _resultado_no_disponible(dominio, "no se ha reconocido el formato de fecha de este WHOIS")

    dias_restantes = (fecha_caducidad - datetime.now(timezone.utc)).days
    datos = {"caduca_el": fecha_caducidad.date().isoformat(), "dias_restantes": dias_restantes}

    if dias_restantes < 0:
        return _resultado(
            estado="rojo",
            prioridad="alta",
            detalle=f"El dominio parece haber caducado hace {abs(dias_restantes)} días. Si sigue siendo visible es porque puede estar en periodo de gracia — hay que renovarlo cuanto antes.",
            datos=datos,
        )

    if dias_restantes < DIAS_AVISO_CADUCIDAD:
        return _resultado(
            estado="ambar",
            prioridad="alta",
            detalle=f"El dominio caduca en {dias_restantes} días. Conviene renovarlo cuanto antes para no perderlo.",
            datos=datos,
        )

    return _resultado(
        estado="verde",
        prioridad="baja",
        detalle=f"El dominio está registrado y caduca en {dias_restantes} días.",
        datos=datos,
    )


def _resultado_no_disponible(dominio: str, motivo: str) -> dict:
    """
    No poder consultar el WHOIS de un TLD concreto no es un fallo del
    dominio, pero tampoco es una comprobación superada: es que no lo
    sabemos. Ni verde (fingiría que se comprobó y salió bien) ni rojo
    (acusaría sin motivo) — un estado propio que no suma ni resta en la
    nota, y que se lo dice al cliente tal cual.
    """
    return _resultado(
        estado="sin_datos",
        prioridad="info",
        detalle=(
            f"No hemos podido comprobar la fecha de caducidad de este dominio ({motivo}). "
            "Muchos registros limitan hoy este dato por normativa de protección de datos, así "
            "que a veces solo se puede consultar a mano en la web del registrador. No es ni "
            "bueno ni malo — no cuenta para tu nota."
        ),
        datos={"disponible": False},
    )


def _resultado(estado: str, prioridad: str, detalle: str, datos: dict | None = None) -> dict:
    """Mismo formato común que usa el resto de checks (ver ssl_check.py)."""
    return {
        "check": "whois",
        "estado": estado,
        "prioridad": prioridad,
        "detalle": detalle,
        "datos": datos or {},
    }
