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

    python3 presentacion/construir.py
"""
import base64, pathlib

AQUI = pathlib.Path(__file__).parent
FUENTES = AQUI.parent / "landing" / "fonts"

html = (AQUI / "presentacion.plantilla.html").read_text()
for marca, archivo in [("__FRAUNCES__", "fraunces-latin.woff2"),
                       ("__NUNITO__",   "nunito-latin.woff2")]:
    if marca not in html:
        raise SystemExit(f"Falta el marcador {marca} en la plantilla")
    html = html.replace(marca, base64.b64encode((FUENTES / archivo).read_bytes()).decode())

destino = AQUI / "presentacion.html"
destino.write_text(html)
print(f"{destino.name} generado ({len(html)/1024:.0f} KB)")
