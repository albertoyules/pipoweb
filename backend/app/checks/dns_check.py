"""
Check de registros DNS anti-suplantación: SPF, DKIM, DMARC.

Categoría: Reputación de dominio / email (ver PIPO_PLANNING.md, sección 2).
Naturaleza: 100% pasivo (verde). Los registros DNS son públicos por
diseño: cualquier persona, servidor de correo o resolver del mundo
puede consultarlos. No accedemos a ningún sistema del cliente, solo
preguntamos a la infraestructura DNS pública (la misma que usa
cualquier servidor de correo para decidir si confía en un email).

Qué comprobamos:
- SPF: qué servidores tienen permiso para enviar email en nombre del dominio.
- DMARC: qué hacer si un email falla la verificación (y su política).
- DKIM: firma criptográfica del email. A diferencia de SPF/DMARC, vive
  bajo un "selector" elegido por el proveedor de correo, que no se
  puede saber con certeza desde fuera. Probamos una lista corta de
  selectores habituales (misma técnica que usan herramientas como
  MXToolbox) y lo tratamos como informativo: no encontrar ninguno no
  demuestra que no exista DKIM, solo que no está en los selectores
  típicos.
"""

import dns.asyncresolver
import dns.exception

# Selectores DKIM más comunes entre proveedores de email habituales
# (Google Workspace, Microsoft 365, servicios de marketing...).
SELECTORES_DKIM_HABITUALES = [
    "google", "selector1", "selector2", "k1", "dkim", "default", "mail", "smtp",
]


async def _consultar_txt(nombre: str) -> list[str]:
    """
    Pide los registros TXT de un nombre DNS y devuelve su contenido
    como texto. Si el nombre no existe o no tiene TXT, devuelve una
    lista vacía en vez de fallar: es una respuesta válida ("no hay
    nada ahí"), no un error.
    """
    resolver = dns.asyncresolver.Resolver()
    resolver.timeout = 3.0
    resolver.lifetime = 3.0
    # Usamos un resolver público fijo (Cloudflare) en vez del que dé la
    # red local: evita depender de un router doméstico o corporativo
    # que puede ser lento, estar mal configurado, o directamente
    # rechazar ciertas consultas.
    resolver.nameservers = ["1.1.1.1", "1.0.0.1"]
    try:
        respuesta = await resolver.resolve(nombre, "TXT")
    except (
        dns.resolver.NXDOMAIN,
        dns.resolver.NoAnswer,
        dns.resolver.NoNameservers,
        dns.exception.Timeout,
    ):
        return []
    # Cada registro puede venir partido en varios trozos de texto;
    # los unimos para tener la cadena completa (p.ej. "v=spf1 ...").
    return ["".join(trozo.decode() for trozo in registro.strings) for registro in respuesta]


async def comprobar_dns(dominio: str) -> dict:
    """
    Consulta SPF, DMARC y DKIM (selectores habituales) del dominio.
    Devuelve el mismo formato que el resto de checks.
    """
    registros_dominio = await _consultar_txt(dominio)
    spf = next((r for r in registros_dominio if r.startswith("v=spf1")), None)

    registros_dmarc = await _consultar_txt(f"_dmarc.{dominio}")
    dmarc = next((r for r in registros_dmarc if r.startswith("v=DMARC1")), None)
    politica_dmarc = _extraer_politica_dmarc(dmarc) if dmarc else None

    dkim_encontrado = None
    for selector in SELECTORES_DKIM_HABITUALES:
        registros = await _consultar_txt(f"{selector}._domainkey.{dominio}")
        if registros:
            dkim_encontrado = selector
            break

    datos = {
        "spf": spf,
        "dmarc": dmarc,
        "dmarc_politica": politica_dmarc,
        "dkim_selector_encontrado": dkim_encontrado,
    }

    return _evaluar(spf, dmarc, politica_dmarc, dkim_encontrado, datos)


def _extraer_politica_dmarc(registro_dmarc: str) -> str | None:
    """De 'v=DMARC1; p=reject; ...' saca solo 'reject'."""
    for parte in registro_dmarc.split(";"):
        parte = parte.strip()
        if parte.startswith("p="):
            return parte.removeprefix("p=")
    return None


def _evaluar(spf, dmarc, politica_dmarc, dkim_encontrado, datos) -> dict:
    """
    Semáforo:
    - Ni SPF ni DMARC: rojo. El dominio no tiene ninguna protección
      frente a que alguien mande phishing en su nombre.
    - Falta uno de los dos, o DMARC en modo "none" (solo observa, no
      actúa): ámbar. Hay protección parcial.
    - Ambos presentes y DMARC en cuarentena/rechazo: verde.
    DKIM se añade solo como nota informativa en el detalle, nunca
    baja el semáforo por sí solo (ver docstring del módulo).
    """
    nota_dkim = (
        f" DKIM detectado con selector '{dkim_encontrado}'."
        if dkim_encontrado
        else " No se ha detectado DKIM en los selectores habituales (no concluyente)."
    )

    if not spf and not dmarc:
        return _resultado(
            estado="rojo",
            prioridad="alta",
            detalle="El dominio no tiene SPF ni DMARC: cualquiera podría enviar emails suplantando esta marca."
            + nota_dkim,
            datos=datos,
        )

    if not spf or not dmarc:
        faltante = "SPF" if not spf else "DMARC"
        return _resultado(
            estado="ambar",
            prioridad="media",
            detalle=f"Falta el registro {faltante}. La protección contra suplantación de email es incompleta."
            + nota_dkim,
            datos=datos,
        )

    if politica_dmarc == "none":
        return _resultado(
            estado="ambar",
            prioridad="media",
            detalle="DMARC está en modo \"solo observar\" (p=none): detecta la suplantación pero no la bloquea."
            + nota_dkim,
            datos=datos,
        )

    return _resultado(
        estado="verde",
        prioridad="baja",
        detalle=f"SPF y DMARC configurados correctamente (política DMARC: {politica_dmarc})." + nota_dkim,
        datos=datos,
    )


def _resultado(estado: str, prioridad: str, detalle: str, datos: dict | None = None) -> dict:
    """Mismo formato común que usa el resto de checks (ver ssl_check.py)."""
    return {
        "check": "dns",
        "estado": estado,
        "prioridad": prioridad,
        "detalle": detalle,
        "datos": datos or {},
    }
