"""
Check de protecciones a nivel de dominio: CAA y DNSSEC.

Categoría: Seguridad básica (ver PIPO_PLANNING.md, sección 2).
Naturaleza: 100% pasivo (verde). Ambas son consultas DNS públicas por
diseño — la misma pregunta que hace cualquier autoridad certificadora
o resolver del mundo.

Qué comprobamos:
- CAA (Certification Authority Authorization): qué entidades
  certificadoras tienen permiso para emitir certificados SSL para
  este dominio. Sin él, cualquier CA del mundo podría llegar a emitir
  un certificado para el dominio si consigue superar sus propias
  comprobaciones — CAA es una capa de control adicional, no
  imprescindible pero recomendada.
- DNSSEC: firma criptográfica de las respuestas DNS, para que nadie
  pueda falsificarlas (por ejemplo, para redirigir el tráfico a un
  servidor falso). Se comprueba pidiendo la respuesta con la flag EDNS
  "DO" (DNSSEC OK) y mirando si el servidor devuelve un registro RRSIG
  junto a la respuesta normal — RRSIG es la firma en sí, así que su
  sola presencia confirma que la zona está firmada. No validamos la
  cadena de confianza completa hasta la raíz (eso exigiría
  reimplementar criptografía DNSSEC nosotros mismos); es la misma
  profundidad de comprobación "pasiva" que el resto de checks de Pipo.
"""

import dns.asyncresolver
import dns.exception
import dns.flags
import dns.rdatatype


async def _consultar_caa(dominio: str) -> list[str]:
    resolver = dns.asyncresolver.Resolver()
    resolver.timeout = 3.0
    resolver.lifetime = 3.0
    resolver.nameservers = ["1.1.1.1", "1.0.0.1"]
    try:
        respuesta = await resolver.resolve(dominio, "CAA")
    except (
        dns.resolver.NXDOMAIN,
        dns.resolver.NoAnswer,
        dns.resolver.NoNameservers,
        dns.exception.Timeout,
    ):
        return []
    return [str(registro) for registro in respuesta]


async def _dnssec_activo(dominio: str) -> bool:
    resolver = dns.asyncresolver.Resolver()
    resolver.timeout = 3.0
    resolver.lifetime = 3.0
    resolver.nameservers = ["1.1.1.1", "1.0.0.1"]
    # Pide EDNS con la flag DO ("DNSSEC OK"): sin ella, el servidor ni
    # se molesta en devolver las firmas RRSIG aunque la zona esté firmada.
    resolver.use_edns(0, dns.flags.DO, 4096)
    try:
        respuesta = await resolver.resolve(dominio, "SOA")
    except (
        dns.resolver.NXDOMAIN,
        dns.resolver.NoAnswer,
        dns.resolver.NoNameservers,
        dns.exception.Timeout,
    ):
        return False
    return any(
        registro.rdtype == dns.rdatatype.RRSIG for registro in respuesta.response.answer
    )


async def comprobar_dominio(dominio: str) -> dict:
    """
    CAA + DNSSEC del dominio. Ninguno de los dos es imprescindible por
    sí solo (por eso el peor caso es ámbar, no rojo): son capas
    adicionales de protección del sistema de nombres, no fallos de
    seguridad activos como un certificado caducado.
    """
    caa = await _consultar_caa(dominio)
    dnssec = await _dnssec_activo(dominio)

    datos = {"registros_caa": caa, "dnssec_activo": dnssec}

    if caa and dnssec:
        return _resultado(
            estado="verde",
            prioridad="baja",
            detalle="El dominio tiene CAA (controla qué entidades pueden emitir certificados) y DNSSEC (firma las respuestas DNS) activos.",
            datos=datos,
        )

    faltan = []
    if not caa:
        faltan.append("CAA")
    if not dnssec:
        faltan.append("DNSSEC")

    return _resultado(
        estado="ambar",
        prioridad="media",
        detalle=f"Faltan protecciones adicionales a nivel de dominio: {' y '.join(faltan)}. No es un fallo grave, pero refuerzan la confianza en el dominio.",
        datos=datos,
    )


def _resultado(estado: str, prioridad: str, detalle: str, datos: dict | None = None) -> dict:
    """Mismo formato común que usa el resto de checks (ver ssl_check.py)."""
    return {
        "check": "dominio",
        "estado": estado,
        "prioridad": prioridad,
        "detalle": detalle,
        "datos": datos or {},
    }
