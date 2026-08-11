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

GOOGLE_PAGESPEED_API_KEY = os.getenv("GOOGLE_PAGESPEED_API_KEY")

# Clave para la capa de IA (interpretación de hallazgos y soluciones).
# Ahora usa Claude (Anthropic) — antes era Google Gemini, pero su plan
# gratuito solo daba 20 peticiones/día. GOOGLE_GEMINI_API_KEY se deja
# aquí sin usar por si algún día hiciera falta volver atrás.
GOOGLE_GEMINI_API_KEY = os.getenv("GOOGLE_GEMINI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
