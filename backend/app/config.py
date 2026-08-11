"""
Configuración centralizada: lee las variables de entorno (secretos,
claves de API...) una sola vez, para que el resto del código nunca
tenga que tocar archivos .env directamente.
"""

import os

from dotenv import load_dotenv

# Busca un archivo .env en la carpeta backend/ y carga sus variables
# como si fueran variables de entorno normales del sistema.
load_dotenv()

def _leer_clave(nombre: str) -> str | None:
    """
    Igual que os.getenv, pero quitando espacios y saltos de línea de
    los extremos. Un panel de variables de entorno (Railway y otros)
    puede colar un "\n" al final si se pega la clave de forma descuidada,
    y una cabecera HTTP con un salto de línea dentro es ilegal — httpx
    la rechaza con un "Connection error" que no da ninguna pista de que
    el problema es un simple espacio de más.
    """
    valor = os.getenv(nombre)
    return valor.strip() or None if valor else None


GOOGLE_PAGESPEED_API_KEY = _leer_clave("GOOGLE_PAGESPEED_API_KEY")

# Clave para la capa de IA (interpretación de hallazgos y soluciones).
# Ahora usa Claude (Anthropic) — antes era Google Gemini, pero su plan
# gratuito solo daba 20 peticiones/día. GOOGLE_GEMINI_API_KEY se deja
# aquí sin usar por si algún día hiciera falta volver atrás.
GOOGLE_GEMINI_API_KEY = _leer_clave("GOOGLE_GEMINI_API_KEY")
ANTHROPIC_API_KEY = _leer_clave("ANTHROPIC_API_KEY")

# Número de Bizum donde se cobra a mano el nivel de pago "soluciones +
# PDF" (ver CLAUDE.md, P2) — es un dato personal de Alberto, no una
# clave de API, pero se trata igual: fuera del código, en variables de
# entorno, para no dejarlo en claro en el repo (aunque sea privado).
TELEFONO_BIZUM = _leer_clave("TELEFONO_BIZUM")
