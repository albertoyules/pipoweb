"""
Piezas de seguridad compartidas: quién nos está pidiendo algo, y qué
dominios aceptamos analizar.

Las dos cosas viven aquí y no en main.py porque las usan varios
endpoints y porque son las que sostienen dos promesas del proyecto:
que Pipo no se pueda usar como arma de reconocimiento masivo, y que
solo mire webs públicas de verdad.
"""

import asyncio
import ipaddress
import re
import socket

from fastapi import Request

# --------------------------------------------------------------------
# 1. Quién nos pide las cosas (clave del rate limiting)
# --------------------------------------------------------------------

def ip_cliente(request: Request) -> str:
    """
    La IP real del visitante, para que el límite de peticiones sea por
    persona y no por servidor.

    Por qué no vale el get_remote_address de slowapi: ese lee la IP de
    quien abre la conexión TCP con uvicorn. En local eso es el visitante
    y funciona; en Railway (y en cualquier hosting con proxy delante)
    eso es el proxy, no el visitante. Se comprobó el 13 ago 2026 con
    curl real contra producción: 7 escaneos seguidos, los 7 aceptados,
    mientras el mismo código en local cortaba al sexto. El límite
    existía sobre el papel y no se aplicaba nunca.

    X-Forwarded-For es una lista, "cliente, proxy1, proxy2": el primero
    es el visitante original. En general es una cabecera que cualquiera
    puede escribir a mano, así que nunca sirve para autorizar nada — para
    repartir cubos de rate limiting sí, que es lo que hace todo el mundo.

    Comprobado en producción tras desplegar (13 ago 2026): **Railway
    reescribe esta cabecera con la IP real de quien conecta**, no la
    respeta si viene puesta desde fuera. Se vio mandando siete peticiones
    con X-Forwarded-For inventadas y distintas: el límite saltó igual a
    la sexta, señal de que todas cayeron en el mismo cubo (el de la IP de
    verdad). O sea que aquí no se puede esquivar el límite falsificando
    la cabecera. Si algún día se cambia de hosting, esto hay que volver a
    comprobarlo: con un proxy que la respete, sí se podría.
    """
    reenviada = request.headers.get("x-forwarded-for")
    if reenviada:
        primera = reenviada.split(",")[0].strip()
        if primera:
            return primera
    return request.client.host if request.client else "desconocido"


# --------------------------------------------------------------------
# 2. Qué dominios aceptamos analizar
# --------------------------------------------------------------------

class DominioNoValido(ValueError):
    """El texto recibido no es un dominio público que podamos analizar."""


# Un nombre de dominio: etiquetas separadas por puntos, y una extensión
# final de solo letras (así "1.2.3.4" no cuela como si fuera un dominio).
PATRON_DOMINIO = re.compile(
    r"^(?=.{4,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$"
)

# Nombres que apuntan a la propia máquina o a la red interna del
# hosting. Aunque el patrón de arriba ya los rechaza casi todos, se
# listan explícitamente para que quede claro que es a propósito.
NOMBRES_PROHIBIDOS = {"localhost", "localhost.localdomain", "ip6-localhost"}
SUFIJOS_PROHIBIDOS = (".local", ".internal", ".localdomain", ".home.arpa")


def normalizar_dominio(texto: str) -> str:
    """
    Convierte lo que escriba el usuario en un dominio limpio, o lanza
    DominioNoValido. Acepta "https://www.ejemplo.com/contacto?x=1" y
    devuelve "www.ejemplo.com".

    No comprueba todavía a qué IP resuelve — eso es el paso siguiente
    (resolver_es_publico), que sí toca la red y por eso va aparte.
    """
    if not texto:
        raise DominioNoValido("Escribe el dominio de la web que quieres revisar.")

    limpio = texto.strip().lower()
    limpio = re.sub(r"^[a-z][a-z0-9+.-]*://", "", limpio)  # quita http://, https://...
    limpio = limpio.split("/")[0].split("?")[0].split("#")[0]
    limpio = limpio.split("@")[-1]  # por si pegan un email o un "usuario@host"

    # Un puerto explícito se rechaza en vez de ignorarse: pedir el
    # puerto 8080 o 22 de una máquina ya no es "mirar la web como
    # cualquier visitante", que es toda la base legal de Pipo.
    if ":" in limpio:
        raise DominioNoValido("Escribe solo el dominio, sin puerto (por ejemplo: tunegocio.es).")

    limpio = limpio.rstrip(".")

    if limpio in NOMBRES_PROHIBIDOS or limpio.endswith(SUFIJOS_PROHIBIDOS):
        raise DominioNoValido("Pipo solo analiza webs públicas de internet.")

    try:  # dominios con eñes o acentos (ejemplo: pequeñanegocio.es)
        limpio = limpio.encode("idna").decode("ascii")
    except UnicodeError as error:
        raise DominioNoValido("Ese dominio tiene caracteres que no se reconocen.") from error

    if not PATRON_DOMINIO.match(limpio):
        raise DominioNoValido("Eso no parece un dominio válido. Prueba con algo como tunegocio.es.")

    return limpio


def dominio_raiz(dominio: str) -> str:
    """
    Quita el "www." del principio, si lo hay.

    Hace falta porque hay registros del DNS que, por definición, viven
    en el dominio raíz y nunca en el subdominio "www": SPF y DMARC (que
    mira dns_check), CAA y DNSSEC (dominio_check) y el propio WHOIS,
    que solo se puede consultar de un dominio registrado, no de un
    subdominio cualquiera.

    Descubierto el 16 ago 2026 haciendo el estudio de negocios de
    Churriana/Alhaurín: escanear "www.mchomeinmobiliaria.com" daba dns
    en ROJO por "no tiene SPF ni DMARC", cuando el dominio los tiene
    los dos bien puestos (DMARC incluso en p=quarantine). Pipo estaba
    preguntando donde no podía haber respuesta y tratando el silencio
    como una acusación.

    Solo se quita el "www" de delante. Cualquier otro subdominio
    (tienda.ejemplo.com) se deja tal cual: ahí el usuario sí está
    pidiendo expresamente ese subdominio.
    """
    return dominio[4:] if dominio.startswith("www.") else dominio


def variante_www(dominio: str) -> str:
    """
    La otra forma de escribir la misma dirección: si viene con "www."
    lo quita, y si viene sin él lo pone.

    Se usa para reintentar la descarga de la home cuando la forma
    pedida no responde (ver obtener_pagina). Es muy común que solo una
    de las dos esté bien configurada, y hasta el 16 ago 2026 eso hacía
    que Pipo diera por muerta una web que funciona perfectamente con
    la otra forma.
    """
    raiz = dominio_raiz(dominio)
    return raiz if dominio.startswith("www.") else f"www.{raiz}"


def _es_ip_publica(ip: str) -> bool:
    """True solo si la IP es de internet abierto, no de una red interna."""
    direccion = ipaddress.ip_address(ip)
    return not (
        direccion.is_private
        or direccion.is_loopback
        or direccion.is_link_local
        or direccion.is_reserved
        or direccion.is_multicast
        or direccion.is_unspecified
    )


async def comprobar_dominio_publico(dominio: str) -> None:
    """
    Comprueba que el dominio resuelve a una IP de internet público, y
    no a la red interna del servidor donde corre Pipo.

    Por qué hace falta si ya validamos el texto: cualquiera puede
    registrar un dominio normal y hacerlo apuntar a 127.0.0.1 o a
    169.254.169.254 (la dirección donde los hostings guardan sus datos
    internos). Sin esta comprobación, Pipo haría esas peticiones desde
    dentro del servidor y devolvería lo que encontrase. Es el patrón que
    se conoce como SSRF, y la defensa estándar es exactamente esto:
    resolver primero, y solo seguir si la IP es pública.
    """
    try:
        direcciones = await asyncio.to_thread(socket.getaddrinfo, dominio, None)
    except socket.gaierror as error:
        raise DominioNoValido(
            "Ese dominio no existe o no se puede resolver. Comprueba que está bien escrito."
        ) from error

    ips = {info[4][0] for info in direcciones}
    if not any(_es_ip_publica(ip) for ip in ips):
        raise DominioNoValido("Pipo solo analiza webs publicadas en internet.")
