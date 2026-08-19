"""
Mete las fuentes de marca dentro de la presentación.

La presentación se comparte como un único archivo suelto (un artifact,
un adjunto, un USB), así que no puede depender de la carpeta
landing/fonts/. Y la política de seguridad de los artifacts bloquea
cualquier CDN, así que tampoco se pueden pedir a Google.

La solución es incrustar los dos woff2 en base64 dentro del HTML. Se
edita SIEMPRE presentacion.plantilla.html (que lleva los marcadores
__FRAUNCES__ / __NUNITO__) y se ejecuta esto para generar el archivo
final, que pesa ~176 KB con todo dentro.

    python3 presentacion/construir.py                 # el deck nocturno 16:9
    python3 presentacion/construir.py cuadrada        # el cuadrado 1080x1080

El argumento es el prefijo del archivo: `cuadrada` lee
cuadrada.plantilla.html y escribe cuadrada.html.
"""
import base64, pathlib, sys

AQUI = pathlib.Path(__file__).parent
FUENTES = AQUI.parent / "landing" / "fonts"

nombre = sys.argv[1] if len(sys.argv) > 1 else "presentacion"
html = (AQUI / f"{nombre}.plantilla.html").read_text()
for marca, archivo in [("__FRAUNCES__", "fraunces-latin.woff2"),
                       ("__NUNITO__",   "nunito-latin.woff2")]:
    if marca not in html:
        raise SystemExit(f"Falta el marcador {marca} en la plantilla")
    html = html.replace(marca, base64.b64encode((FUENTES / archivo).read_bytes()).decode())

destino = AQUI / f"{nombre}.html"
destino.write_text(html)
print(f"{destino.name} generado ({len(html)/1024:.0f} KB)")
