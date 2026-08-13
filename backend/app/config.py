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

# Número de Bizum. YA NO SE USA en ningún sitio desde el 13 ago 2026: el
# producto de pago pasó a ser un servicio que se presupuesta antes de
# cobrar, así que no hay ningún pago que pedir por adelantado ni ninguna
# referencia que enseñar. Se deja leído aquí (sin usar) por si vuelve a
# hacer falta; es un dato personal, así que si se retoma, sigue fuera del
# código y solo en variables de entorno.
TELEFONO_BIZUM = _leer_clave("TELEFONO_BIZUM")

# Envío de emails (confirmación de pedido al cliente + aviso a Alberto)
# por Gmail SMTP con una "contraseña de aplicación" — ver
# app/notificaciones/enviar.py para el porqué de esta elección.
GMAIL_EMAIL = _leer_clave("GMAIL_EMAIL")
GMAIL_APP_PASSWORD = _leer_clave("GMAIL_APP_PASSWORD")

# Clave del panel privado de pedidos (landing/pedidos.html?clave=...) —
# quien la tenga puede ver los pedidos y marcarlos como pagados. Sin
# usuarios ni contraseñas de verdad a propósito: es un panel de uso
# personal para Alberto, no un producto multiusuario.
#
# Desde el 13 ago 2026 protege también los endpoints /check/* de
# depuración, que hasta entonces estaban abiertos a internet sin límite
# (ver app/main.py).
CLAVE_ADMIN = _leer_clave("CLAVE_ADMIN")

# ¿Se publica la documentación automática de la API (/docs y /redoc)?
# Apagada por defecto: enseña el mapa completo de la API, incluidos los
# endpoints de administración, y no aporta nada a un visitante. Se
# enciende poniendo PIPO_DOCS=1 en el .env local, que es donde sí
# resulta cómoda. Al ser "apagado por defecto", producción queda segura
# sin tener que acordarse de configurar nada en Railway.
MOSTRAR_DOCS = (os.getenv("PIPO_DOCS") or "").strip() == "1"
