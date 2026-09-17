"""
Relevancia de cada check según el tipo de sitio detectado.

Esto NO toca la nota (ver puntuacion.py, decisión #1 de CLAUDE.md: la
nota es una fórmula fija, nunca depende del tipo de negocio ni la
calcula la IA). Es una capa de contexto aparte: "esto te importa más o
menos por ser el tipo de web que eres", pensada para que el informe
pueda decir, por ejemplo, que las cabeceras de seguridad le importan
más a un sitio con panel de acceso que a una landing sin login.

Determinista a propósito, igual que la nota — no se le pide a la IA
que decida esto, por el mismo motivo: sería fácil que un modelo
"quitara importancia" a un fallo real para sonar más amable, o al
revés. La tabla vive aquí, en código, para que sea predecible y se
pueda razonar sobre ella sin llamar a nadie.

REGLA para no confundirla con PESOS: un check nunca sube de relevancia
solo porque proteja a cualquier visitante por igual (eso ya lo decide
el peso fijo en puntuacion.py). Sube o baja aquí solo cuando el propio
tipo de sitio cambia lo que hay en juego — un CDN sin verificar es más
grave si por ahí pasan datos de pago que si la web es una landing sin
formularios.
"""

NIVELES = ("alta", "normal", "baja")


def _tiene_datos_sensibles(senales: dict) -> bool:
    """Checkout o login: en los dos hay datos personales/de pago en juego."""
    return bool(senales.get("tiene_checkout") or senales.get("tiene_login"))


# Cada función recibe las señales del perfil (perfil_sitio.py) y
# devuelve "alta", "normal" o "baja". Los checks que no aparecen aquí
# se quedan siempre en "normal": su importancia no depende del tipo de
# sitio (p.ej. whois, dominio, dns, archivos_expuestos, experiencia).
_REGLAS: dict[str, callable] = {
    "mixed_content": lambda s: "alta" if _tiene_datos_sensibles(s) else "normal",
    "headers": lambda s: "alta" if s.get("tiene_login") else "normal",
    "ssl": lambda s: "alta" if s.get("tiene_checkout") else "normal",
    "tecnologia": lambda s: "alta" if _tiene_datos_sensibles(s) else "normal",
    "accesibilidad": lambda s: "alta" if (s.get("es_blog") or s.get("tiene_checkout")) else "normal",
    "rendimiento": lambda s: "alta" if s.get("tiene_checkout") else "normal",
    "privacidad": lambda s: "alta" if _tiene_datos_sensibles(s) else "normal",
    # Un panel de acceso sin tienda ni blog detrás no necesita salir en
    # Google: no hay nada que un visitante anónimo deba encontrar ahí.
    "seo": lambda s: "baja" if (s.get("tiene_login") and not s.get("tiene_checkout") and not s.get("es_blog")) else "normal",
}


def relevancia_de(check_id: str, perfil_sitio: dict | None) -> str:
    """
    "alta", "normal" o "baja" para ese check, según el perfil del
    sitio. Sin perfil (escaneos guardados antes de que existiera, o
    webs que no se dejaron descargar), todo es "normal": no hay
    señales de las que partir, así que no se prioriza nada.
    """
    if not perfil_sitio or not perfil_sitio.get("senales"):
        return "normal"

    regla = _REGLAS.get(check_id)
    if regla is None:
        return "normal"

    return regla(perfil_sitio["senales"])


def anotar_relevancia(checks: list[dict], perfil_sitio: dict | None) -> list[dict]:
    """
    Devuelve los mismos checks con una clave "relevancia" añadida a
    cada uno. No muta la lista original: el informe y el PDF pueden
    seguir usando el resultado crudo del escaneo sin este añadido si
    alguna vez hace falta.
    """
    return [{**check, "relevancia": relevancia_de(check["check"], perfil_sitio)} for check in checks]
