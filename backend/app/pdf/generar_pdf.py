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
    # "info": un check en sin_datos (p.ej. WHOIS sin respuesta) — no es
    # ni bien ni mal, así que ni verde ni rojo. Mismo gris cálido que
    # usa la landing para lo mismo (ver informe.html/index.html).
    "info": "#B6A894",
}
TEXTO_PRIORIDAD = {
    "baja": "Prioridad baja",
    "media": "Prioridad media",
    "alta": "Prioridad alta",
    "info": "Sin datos",
}
COLOR_ESTADO = {
    "verde": "#8A9A5B",
    "ambar": "#D9A441",
    "rojo": "#B34733",
}
# Nota: "sin_datos" no tiene entrada aquí a propósito — el estado de una
# FAMILIA (que es lo único que se colorea con este diccionario) nunca es
# "sin_datos", porque _peor_estado() en puntuacion.py ya lo excluye del
# cálculo. Solo los checks individuales pueden estar en sin_datos, y esos
# se colorean por prioridad (COLOR_PRIORIDAD["info"]), no por estado.

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
.preparado-para {
  font-family: Helvetica, Arial, sans-serif;
  font-size: 11px;
  color: #C97B5A;
  margin-top: 2px;
}
table.familias { width: 100%; border-collapse: collapse; margin-bottom: 6px; }
table.familias td { padding: 7px 4px; border-bottom: 1px solid #EBE1D2; font-size: 12px; }
table.familias td.punto { width: 16px; }
table.familias td.punto span {
  display: inline-block; width: 9px; height: 9px; border-radius: 50%;
}
table.familias td.nombre { font-weight: bold; }
table.familias td.detalle {
  font-family: Helvetica, Arial, sans-serif; font-size: 10.5px; color: #8a7a68;
}
table.familias td.nota { text-align: right; font-weight: bold; white-space: nowrap; }
.cierre {
  break-inside: avoid;
  margin-top: 24px;
  background: #F5EFE6;
  border-left: 4px solid #C97B5A;
  border-radius: 0 8px 8px 0;
  padding: 14px 16px;
  font-size: 11.5px;
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


def _bloque_familias(resumen: dict) -> str:
    """
    El desglose por familias (seguridad / cumplimiento / clientes) con
    su nota. Es lo que evita que el PDF sea un número suelto: enseña
    dónde está el problema, no solo que lo hay.
    """
    familias = resumen.get("familias") or []
    if not familias:
        return ""
    piezas = ['<h2 class="seccion">Resumen por áreas</h2><table class="familias">']
    for familia in familias:
        color = COLOR_ESTADO.get(familia["estado"], "#D9A441")
        rojos = familia["conteo"]["rojo"]
        # Los "sin_datos" (p.ej. WHOIS sin respuesta) no cuentan como
        # bien ni como mal, pero se mencionan aparte si los hay — si no,
        # el total de esta línea no cuadraría con el número de checks
        # reales de la familia, y parecería que a alguien se le olvidó
        # sumar uno.
        sin_datos = familia["conteo"].get("sin_datos", 0)
        texto_sin_datos = f" · {sin_datos} sin datos" if sin_datos else ""
        piezas.append(f"""
          <tr>
            <td class="punto"><span style="background:{color}"></span></td>
            <td class="nombre">{_seguro(familia['nombre'])}</td>
            <td class="detalle">{familia['conteo']['verde']} bien ·
              {familia['conteo']['ambar']} a mejorar ·
              {rojos} {'grave' if rojos == 1 else 'graves'}{texto_sin_datos}</td>
            <td class="nota">{familia['puntuacion']}/100</td>
          </tr>
        """)
    piezas.append("</table>")
    return "".join(piezas)


def generar_pdf_informe(escaneo: dict, marca: str | None = None) -> bytes:
    """
    Construye el PDF de marca a partir de un escaneo ya guardado y su
    informe interpretado. No llama a la IA — solo compone HTML con lo
    que ya está guardado en la base de datos y lo convierte a PDF.

    Lo que este PDF NO lleva, a propósito, es la sección de soluciones
    paso a paso. El diagnóstico se regala; el "cómo se arregla" es el
    servicio que se cobra (ver CLAUDE.md, P2). Si se entregaran los
    pasos aquí, el cliente se los pasa a su informático de siempre y la
    venta se pierde en ese reenvío.

    `marca` pone "Preparado para X" en la portada, para que un diseñador
    o una agencia pueda entregárselo a sus propios clientes.
    """
    from weasyprint import HTML  # import perezoso: WeasyPrint es pesado de cargar

    informe = escaneo["informe"]
    resumen = escaneo["resultado"].get("resumen", {})
    dominio = _seguro(escaneo["dominio"])
    fecha = datetime.now().strftime("%d/%m/%Y")
    linea_marca = f'<div class="preparado-para">Preparado para {_seguro(marca)}</div>' if marca else ""
    # La nota grande va del color del semáforo global, no de un ámbar
    # fijo: un 100 con todo en verde impreso en ámbar se lee como si
    # algo fallara y contradice a la tabla de áreas de más abajo.
    color_nota = COLOR_ESTADO.get(resumen.get("estado_global"), "#D9A441")

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
          {linea_marca}
        </div>
        <div class="nota-global">
          <div class="num" style="color: {color_nota}">{informe.get('puntuacion_global', '—')}</div>
          <div class="lbl">Nota global</div>
        </div>
      </div>

      <div class="resumen">{_seguro(informe.get('resumen_ejecutivo', ''))}</div>

      {_bloque_familias(resumen)}
      {_bloque_hallazgos(informe.get('hallazgos', []))}

      <div class="cierre">
        <strong>¿Prefieres que lo arreglemos nosotros?</strong>
        Este informe te dice qué falla y por qué importa. Si quieres que lo dejemos todo en
        verde sin que tengas que tocar nada, escríbenos a alberyules11@gmail.com indicando
        tu dominio y te pasamos presupuesto cerrado en menos de 24 horas.
      </div>

      <div class="pie-legal">
        Este informe lo genera Pipo de forma automática a partir de información pública de
        {dominio}, sin acceder a su servidor. No sustituye asesoría legal ni de un
        Delegado de Protección de Datos (DPO). © Pipo · pipoweb.com
      </div>
    </body>
    </html>
    """

    return HTML(string=html_documento).write_pdf()
