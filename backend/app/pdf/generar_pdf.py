"""
Generador del PDF descargable del informe, con la marca de Pipo.

Usa WeasyPrint (HTML+CSS → PDF) en vez de maquetar el documento a mano:
así se reaprovecha el mismo lenguaje visual que ya existe en la landing
y en informe.html, con mucho menos código que con una librería de bajo
nivel tipo ReportLab.

No usa las fuentes de marca (Fraunces/Nunito) a propósito: WeasyPrint
tendría que descargarlas de Google Fonts en cada generación, lo que
añade una dependencia de red y latencia a algo que debería ser rápido
y fiable. Se usan fuentes "serif"/"sans-serif" genéricas, siempre
disponibles, con los mismos colores y proporciones de la marca.
"""

import html
from datetime import datetime

COLOR_PRIORIDAD = {
    "baja": "#8A9A5B",
    "media": "#D9A441",
    "alta": "#B34733",
}
TEXTO_PRIORIDAD = {
    "baja": "Prioridad baja",
    "media": "Prioridad media",
    "alta": "Prioridad alta",
}

# Silueta de Pipo simplificada (sin animaciones ni clases: aquí solo
# hace falta la imagen estática), reutilizada de landing/index.html.
SVG_PIPO = """
<svg viewBox="0 0 240 260" width="64" height="64">
  <ellipse cx="120" cy="150" rx="82" ry="90" fill="#B08968"/>
  <ellipse cx="120" cy="162" rx="58" ry="66" fill="#E8D6BF"/>
  <path d="M54 82 Q44 40 78 60 Q70 84 54 82Z" fill="#6F4E37"/>
  <path d="M186 82 Q196 40 162 60 Q170 84 186 82Z" fill="#6F4E37"/>
  <path d="M70 92 Q92 80 116 92" stroke="#6F4E37" stroke-width="6" fill="none" stroke-linecap="round"/>
  <path d="M124 92 Q148 80 170 92" stroke="#6F4E37" stroke-width="6" fill="none" stroke-linecap="round"/>
  <circle cx="92" cy="120" r="30" fill="#fff"/>
  <circle cx="95" cy="122" r="15" fill="#3A2E24"/>
  <circle cx="100" cy="117" r="5" fill="#fff"/>
  <circle cx="148" cy="120" r="30" fill="#fff"/>
  <circle cx="145" cy="122" r="15" fill="#3A2E24"/>
  <circle cx="150" cy="117" r="5" fill="#fff"/>
  <path d="M120 132 L110 150 Q120 158 130 150Z" fill="#D9A441"/>
  <path d="M40 140 Q22 170 44 200 Q52 170 56 150Z" fill="#6F4E37"/>
  <path d="M200 140 Q218 170 196 200 Q188 170 184 150Z" fill="#6F4E37"/>
</svg>
""".strip()

CSS_BASE = """
@page {
  size: A4;
  margin: 22mm 18mm 24mm;
  @bottom-center {
    content: "Pipo — analizador web · página " counter(page) " de " counter(pages);
    font-family: Helvetica, Arial, sans-serif;
    font-size: 9px;
    color: #8a7a68;
  }
}
* { box-sizing: border-box; }
body {
  font-family: Georgia, "Times New Roman", serif;
  color: #3A2E24;
  line-height: 1.5;
  font-size: 12px;
}
.cabecera {
  display: flex;
  align-items: center;
  gap: 16px;
  border-bottom: 2px solid #C97B5A;
  padding-bottom: 16px;
  margin-bottom: 20px;
}
.cabecera .marca {
  font-family: Helvetica, Arial, sans-serif;
  font-weight: 700;
  font-size: 13px;
  letter-spacing: .08em;
  text-transform: uppercase;
  color: #C97B5A;
}
.cabecera h1 {
  font-size: 24px;
  margin: 2px 0 4px;
  color: #3A2E24;
}
.cabecera .fecha {
  font-family: Helvetica, Arial, sans-serif;
  font-size: 11px;
  color: #8a7a68;
}
.nota-global {
  margin-left: auto;
  text-align: center;
  flex-shrink: 0;
}
.nota-global .num {
  font-size: 40px;
  font-weight: 700;
  color: #D9A441;
  line-height: 1;
}
.nota-global .lbl {
  font-family: Helvetica, Arial, sans-serif;
  font-size: 10px;
  color: #8a7a68;
  text-transform: uppercase;
  letter-spacing: .05em;
}
.resumen {
  background: #F5EFE6;
  border-radius: 10px;
  padding: 14px 18px;
  margin-bottom: 22px;
  font-size: 12.5px;
}
h2.seccion {
  font-family: Helvetica, Arial, sans-serif;
  font-size: 13px;
  text-transform: uppercase;
  letter-spacing: .08em;
  color: #C97B5A;
  border-bottom: 1px solid #EBE1D2;
  padding-bottom: 6px;
  margin: 24px 0 14px;
}
.hallazgo, .solucion {
  break-inside: avoid;
  padding: 10px 0 10px 14px;
  border-left: 4px solid #ccc;
  margin-bottom: 12px;
}
.hallazgo h3, .solucion h3 {
  font-size: 14px;
  margin: 0 0 4px;
}
.etiqueta-prioridad {
  display: inline-block;
  font-family: Helvetica, Arial, sans-serif;
  font-size: 9.5px;
  font-weight: 700;
  color: #fff;
  padding: 2px 8px;
  border-radius: 999px;
  margin-bottom: 6px;
}
.hallazgo p, .solucion p { margin: 4px 0; font-size: 11.5px; }
.hallazgo .impacto { color: #6a5c4e; font-style: italic; }
.solucion ol { margin: 6px 0 6px 18px; padding: 0; font-size: 11.5px; }
.solucion li { margin-bottom: 3px; }
.solucion .meta {
  font-family: Helvetica, Arial, sans-serif;
  font-size: 10px;
  color: #8a7a68;
}
.pie-legal {
  margin-top: 28px;
  padding-top: 12px;
  border-top: 1px solid #EBE1D2;
  font-family: Helvetica, Arial, sans-serif;
  font-size: 9.5px;
  color: #8a7a68;
}
"""


def _seguro(texto: str) -> str:
    """Escapa HTML para que ningún texto (dominio, texto de la IA) rompa el documento."""
    return html.escape(str(texto)) if texto else ""


def _bloque_hallazgos(hallazgos: list[dict]) -> str:
    piezas = ['<h2 class="seccion">Hallazgos</h2>']
    for hallazgo in hallazgos:
        prioridad = hallazgo.get("prioridad", "media")
        color = COLOR_PRIORIDAD.get(prioridad, "#D9A441")
        etiqueta = TEXTO_PRIORIDAD.get(prioridad, "Prioridad media")
        piezas.append(f"""
          <div class="hallazgo" style="border-left-color:{color}">
            <span class="etiqueta-prioridad" style="background:{color}">{etiqueta}</span>
            <h3>{_seguro(hallazgo.get('titulo', ''))}</h3>
            <p>{_seguro(hallazgo.get('explicacion_llana', ''))}</p>
            <p class="impacto">{_seguro(hallazgo.get('impacto_negocio', ''))}</p>
          </div>
        """)
    return "".join(piezas)


def _bloque_soluciones(soluciones: list[dict]) -> str:
    if not soluciones:
        return ""
    piezas = ['<h2 class="seccion">Cómo solucionarlo</h2>']
    for solucion in soluciones:
        pasos_html = "".join(f"<li>{_seguro(paso)}</li>" for paso in solucion.get("pasos", []))
        piezas.append(f"""
          <div class="solucion">
            <h3>{_seguro(solucion.get('problema', ''))}</h3>
            <ol>{pasos_html}</ol>
            <p class="meta">Quién lo hace normalmente: {_seguro(solucion.get('quien_lo_hace', ''))} ·
              Dificultad: {_seguro(solucion.get('dificultad', ''))}</p>
          </div>
        """)
    return "".join(piezas)


def generar_pdf_informe(escaneo: dict) -> bytes:
    """
    Construye el PDF de marca a partir de un escaneo ya guardado, con
    su informe interpretado (obligatorio) y sus soluciones (opcional,
    si ya se pidieron antes). No llama a la IA — solo compone HTML con
    lo que ya está guardado en la base de datos y lo convierte a PDF.
    """
    from weasyprint import HTML  # import perezoso: WeasyPrint es pesado de cargar

    informe = escaneo["informe"]
    dominio = _seguro(escaneo["dominio"])
    fecha = datetime.now().strftime("%d/%m/%Y")

    html_documento = f"""
    <html>
    <head><style>{CSS_BASE}</style></head>
    <body>
      <div class="cabecera">
        {SVG_PIPO}
        <div>
          <div class="marca">Informe Pipo</div>
          <h1>{dominio}</h1>
          <div class="fecha">Generado el {fecha}</div>
        </div>
        <div class="nota-global">
          <div class="num">{informe.get('puntuacion_global', '—')}</div>
          <div class="lbl">Nota global</div>
        </div>
      </div>

      <div class="resumen">{_seguro(informe.get('resumen_ejecutivo', ''))}</div>

      {_bloque_hallazgos(informe.get('hallazgos', []))}
      {_bloque_soluciones((escaneo.get('soluciones') or {}).get('soluciones', []))}

      <div class="pie-legal">
        Este informe lo genera Pipo de forma automática a partir de información pública de
        {dominio}, sin acceder a su servidor. No sustituye asesoría legal ni de un
        Delegado de Protección de Datos (DPO). © Pipo · piposcan.vercel.app
      </div>
    </body>
    </html>
    """

    return HTML(string=html_documento).write_pdf()
