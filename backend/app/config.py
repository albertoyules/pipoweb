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
# Hoy usa Google Gemini; si en el futuro se cambia a otro proveedor,
# este es el único sitio que habría que tocar.
GOOGLE_GEMINI_API_KEY = os.getenv("GOOGLE_GEMINI_API_KEY")
