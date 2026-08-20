"""
Check de certificado SSL/TLS.

Categoría: Seguridad básica (ver PIPO_PLANNING.md, sección 2).
Naturaleza: 100% pasivo (verde). Nos limitamos a hacer el mismo saludo
TLS que hace cualquier navegador al entrar en una web con HTTPS. El
certificado que leemos es información que el servidor enseña a
cualquiera que se conecte, por diseño del protocolo: no hay ninguna
medida de seguridad que estemos rodeando.

Qué comprobamos:
- Si el certificado sigue siendo válido (no caducado).
- Cuántos días le quedan antes de caducar.
- Qué versión de TLS se ha negociado (las viejas, TLS 1.0/1.1, ya se
  consideran inseguras y los navegadores avisan de ellas).
- Si http:// (sin cifrar) redirige de verdad a https://. Tener un
  buen certificado no sirve de mucho si alguien escribe el dominio sin
  "https://" y la web le sirve la versión sin cifrar en vez de mandarle
  directa a la segura.
"""

import socket
import ssl
from datetime import datetime, timezone

import requests

from app.checks.pagina import USER_AGENT_PIPO
from app.seguridad import variante_www

TIMEOUT_REDIRECCION = 5.0


def _verificar_redireccion_http_https(dominio: str) -> dict:
    """
    Pide http://dominio (sin cifrar) y mira a dónde se acaba llegando.
    Es una petición HTTP normal, la misma que haría un navegador si
    alguien escribe el dominio sin "https://" delante.

    Devuelve un diccionario con "ok" (True si termina en https, o si
    el puerto 80 ni siquiera responde — eso también es seguro, es que
    no hay ninguna puerta sin cifrar) y "detalle" para el caso malo.
    """
    try:
        respuesta = requests.get(
            f"http://{dominio}",
            timeout=TIMEOUT_REDIRECCION,
            allow_redirects=True,
            headers={"User-Agent": USER_AGENT_PIPO},
        )
    except requests.exceptions.RequestException:
        # No responde por HTTP: no hay ninguna puerta de entrada sin
        # cifrar, así que no hay nada que redirigir. Se cuenta como
        # correcto, no como un fallo del check.
        return {"ok": True, "url_final": None}

    # Un 403 al bot no dice nada sobre si el servidor redirige o no: se
    # queda en http:// porque nos ha echado, no porque sirva la web sin
    # cifrar. Sin esto, pascallegalabogados.es salía acusado de "no
    # redirige a https" cuando redirige perfectamente (16 ago 2026).
    if respuesta.status_code >= 400:
        return {"ok": True, "url_final": None}

    url_final = str(respuesta.url)
    if url_final.startswith("https://"):
        return {"ok": True, "url_final": url_final}

    return {
        "ok": False,
        "url_final": url_final,
        "detalle": "La versión sin cifrar (http://) de la web no redirige a https:// — sirve contenido real sin cifrar.",
    }

# Márgenes para decidir el semáforo. Fáciles de ajustar más adelante
# si vemos que asustamos de más o de menos a los clientes.
DIAS_AVISO_CADUCIDAD = 15  # por debajo de esto, ámbar
TLS_INSEGUROS = {"TLSv1", "TLSv1.1"}


def _parsear_fecha_certificado(texto_fecha: str) -> datetime:
    """
    El certificado da la fecha de caducidad en un formato de texto
    tipo 'Jun  1 12:00:00 2027 GMT'. Esta función la convierte en un
    objeto de fecha real con el que se puede calcular "cuántos días
    faltan".
    """
    fecha = datetime.strptime(texto_fecha, "%b %d %H:%M:%S %Y %Z")
    return fecha.replace(tzinfo=timezone.utc)


def _comprobar_ssl_de_un_host(dominio: str, timeout: float = 5.0) -> dict:
    """
    Se conecta al dominio por HTTPS (puerto 443) y examina su
    certificado. Devuelve siempre el mismo formato: estado (semáforo),
    detalle (explicación en lenguaje llano) y datos crudos por si la
    capa de IA los quiere usar más adelante.
    """
    contexto = ssl.create_default_context()

    try:
        # Abrimos una conexión TCP normal...
        with socket.create_connection((dominio, 443), timeout=timeout) as conexion_tcp:
            # ...y sobre ella hacemos el handshake TLS, exactamente
            # como haría un navegador.
            with contexto.wrap_socket(conexion_tcp, server_hostname=dominio) as conexion_tls:
                certificado = conexion_tls.getpeercert()
                protocolo = conexion_tls.version()  # p.ej. "TLSv1.3"

    except socket.timeout:
        return _resultado(
            estado="sin_datos",
            prioridad="baja",
            detalle="El servidor no respondió a tiempo al intentar conectar por HTTPS.",
        )
    except ssl.SSLCertVerificationError as error:
        return _resultado(
            estado="rojo",
            prioridad="alta",
            detalle=f"El certificado no es válido o no es de confianza: {error.verify_message}.",
        )
    except (socket.gaierror, ConnectionRefusedError, OSError) as error:
        return _resultado(
            estado="sin_datos",
            prioridad="baja",
            detalle=f"No se ha podido conectar por HTTPS al dominio ({error}).",
        )

    fecha_caducidad = _parsear_fecha_certificado(certificado["notAfter"])
    dias_restantes = (fecha_caducidad - datetime.now(timezone.utc)).days
    emisor = dict(x[0] for x in certificado.get("issuer", []))
    redireccion = _verificar_redireccion_http_https(dominio)

    datos = {
        "protocolo_tls": protocolo,
        "emisor": emisor.get("organizationName", "desconocido"),
        "caduca_el": fecha_caducidad.date().isoformat(),
        "dias_restantes": dias_restantes,
        "http_redirige_a_https": redireccion["ok"],
    }

    # A partir de aquí, decidimos el semáforo. Los problemas del propio
    # certificado (caducado, a punto de caducar, TLS viejo) mandan
    # siempre sobre el aviso de redirección — si el certificado ya está
    # mal, ese es el problema principal a comunicar.
    if dias_restantes < 0:
        return _resultado(
            estado="rojo",
            prioridad="alta",
            detalle="El certificado SSL ha caducado. Los visitantes ven un aviso de seguridad al entrar.",
            datos=datos,
        )

    if dias_restantes < DIAS_AVISO_CADUCIDAD:
        return _resultado(
            estado="ambar",
            prioridad="media",
            detalle=f"El certificado caduca en {dias_restantes} días. Conviene renovarlo pronto.",
            datos=datos,
        )

    if protocolo in TLS_INSEGUROS:
        return _resultado(
            estado="ambar",
            prioridad="media",
            detalle=f"La web usa {protocolo}, una versión de TLS ya considerada insegura.",
            datos=datos,
        )

    if not redireccion["ok"]:
        return _resultado(
            estado="ambar",
            prioridad="media",
            detalle=f"Certificado válido, pero {redireccion['detalle'][0].lower()}{redireccion['detalle'][1:]}",
            datos=datos,
        )

    return _resultado(
        estado="verde",
        prioridad="baja",
        detalle=f"Certificado válido, emitido por {datos['emisor']}. Caduca en {dias_restantes} días.",
        datos=datos,
    )


def _resultado(estado: str, prioridad: str, detalle: str, datos: dict | None = None) -> dict:
    """Formato común para que todos los checks devuelvan la misma forma."""
    return {
        "check": "ssl",
        "estado": estado,
        "prioridad": prioridad,
        "detalle": detalle,
        "datos": datos or {},
    }


def comprobar_ssl(dominio: str, timeout: float = 5.0) -> dict:
    """
    El certificado del host pedido y, si ese host no responde, el de la
    otra forma de escribir la dirección.

    Por qué: obtener_pagina() aprendió el 16 ago 2026 a reintentar con la
    variante del "www" cuando solo una de las dos está bien configurada
    (el caso de mchomeinmobiliaria.com, que no sirve HTTPS en la raíz
    pero sí en www.). Este check no lo aprendió, así que sobre esa misma
    web los checks de contenido decían "bien" y este decía "no se ha
    podido conectar por HTTPS" en ROJO — y con peso 3 en una familia
    crítica, ese rojo solo ya pintaba el informe entero de rojo.

    Un certificado que no se ha podido mirar es "sin_datos", nunca rojo:
    un fallo de conexión nuestro no es una acusación contra su web. Los
    problemas reales del certificado (caducado, no fiable, TLS viejo) sí
    siguen siendo rojo, porque ahí sí hemos podido mirar.
    """
    resultado = _comprobar_ssl_de_un_host(dominio, timeout)
    if resultado["estado"] != "sin_datos":
        return resultado

    otra_forma = variante_www(dominio)
    if otra_forma == dominio:
        return resultado

    alternativa = _comprobar_ssl_de_un_host(otra_forma, timeout)
    if alternativa["estado"] != "sin_datos":
        alternativa["datos"]["host_analizado"] = otra_forma
        return alternativa

    # Ninguna de las dos formas da certificado. Queda una pregunta que sí
    # importa: ¿es que la web no responde (limitación nuestra, sin_datos)
    # o es que responde pero SOLO sin cifrar? Lo segundo es un problema
    # real y grave del negocio, y dejarlo en sin_datos sería el error
    # contrario al que se está arreglando: taparlo.
    if _sirve_solo_sin_cifrar(dominio) or _sirve_solo_sin_cifrar(otra_forma):
        return _resultado(
            estado="rojo",
            prioridad="alta",
            detalle=(
                "La web funciona pero solo por http://, sin cifrar: no tiene un certificado "
                "válido en https://. Los navegadores la marcan como \"No es seguro\" y todo lo "
                "que escriba un cliente viaja en abierto."
            ),
            datos={"https_disponible": False},
        )

    return resultado


def _sirve_solo_sin_cifrar(dominio: str) -> bool:
    """
    ¿Responde este host por http:// con una página de verdad? Se usa solo
    cuando ya sabemos que por https:// no hay nada, para distinguir "no
    tiene HTTPS" (culpa suya, rojo) de "no hemos podido conectar" (culpa
    nuestra, sin_datos).
    """
    try:
        respuesta = requests.get(
            f"http://{dominio}",
            timeout=TIMEOUT_REDIRECCION,
            allow_redirects=True,
            headers={"User-Agent": USER_AGENT_PIPO},
        )
    except requests.exceptions.RequestException:
        return False
    return respuesta.status_code < 400 and not str(respuesta.url).startswith("https://")
