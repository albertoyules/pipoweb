"""
La parte visual de los emails de Pipo.

Separado de mensajes.py igual que mensajes.py está separado de
enviar.py: aquí no hay ni una frase de contenido, solo el envoltorio de
marca. Así se puede cambiar el diseño sin releer los textos, y al revés.

POR QUÉ ESTÁ ESCRITO "A LA ANTIGUA" (tablas y estilos en línea)
---------------------------------------------------------------
Un email no es una página web. Outlook para Windows lo renderiza con el
motor de Word, y Gmail elimina las hojas de estilo del <head>. Nada de
esto funciona en un email y por eso no se usa aquí:

  - flexbox y grid          → Outlook los ignora y todo se apila mal
  - <style> en el <head>    → Gmail lo borra
  - fuentes web             → no se pueden cargar; se usan las del sistema
  - SVG                     → Gmail no lo pinta, hay que usar PNG

De ahí las tablas anidadas y los `style=` repetidos en cada etiqueta:
es feo de leer, pero es lo único que se ve igual en todos los clientes.

Las tipografías son Georgia y Helvetica en vez de Fraunces y Nunito por
el mismo motivo que en el PDF (ver app/pdf/generar_pdf.py): las de marca
son fuentes web y aquí no se pueden cargar, así que se usa la pareja
serif/sans del sistema que más se les parece.
"""

import html as _html

# Colores de marca (los mismos de la web y del PDF)
CREMA = "#F5EFE6"
CREMA_HONDA = "#EBE1D2"
MARRON = "#6F4E37"
TERRACOTA = "#C97B5A"
AMBAR = "#D9A441"
SALVIA = "#8A9A5B"
LADRILLO = "#B34733"
TINTA = "#3A2E24"
LINEA = "#E3D8C8"

# El búho, servido desde la propia web. Tiene que ser una URL pública y
# por HTTPS: Gmail descarga las imágenes a través de su propio proxy y
# no acepta ni SVG ni imágenes incrustadas en base64.
URL_LOGO = "https://www.pipoweb.com/favicon-192.png"
URL_WEB = "https://www.pipoweb.com"

SERIF = "Georgia,'Times New Roman',serif"
SANS = "Helvetica,Arial,sans-serif"


def esc(texto) -> str:
    """
    Escapa texto antes de meterlo en el HTML.

    No es opcional: por aquí pasan cosas que escribe el cliente (su
    mensaje libre, su teléfono) y textos sacados de la web analizada
    (títulos, cabeceras del servidor). Sin escapar, cualquiera de esos
    campos podría colar etiquetas en el email que Alberto abre.
    """
    return _html.escape(str(texto if texto is not None else ""))


def parrafo(texto_html: str, tenue: bool = False) -> str:
    """Un párrafo normal. `texto_html` ya viene escapado por quien llama."""
    color = "#6b5c4c" if tenue else TINTA
    return (
        f'<p style="margin:0 0 16px;font-family:{SANS};font-size:15px;'
        f'line-height:1.6;color:{color};overflow-wrap:break-word;">{texto_html}</p>'
    )


def nota_destacada(nota: int) -> str:
    """La nota del escaneo, en grande y con el color del semáforo."""
    color = SALVIA if nota >= 80 else (AMBAR if nota >= 60 else LADRILLO)
    return f"""
    <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:0 0 22px;">
      <tr>
        <td style="background:{CREMA};border:1px solid {LINEA};border-radius:12px;padding:16px 22px;">
          <span style="font-family:{SANS};font-size:12px;font-weight:bold;letter-spacing:1.2px;
                       text-transform:uppercase;color:#8a7a68;">Nota actual de tu web</span><br>
          <span style="font-family:{SERIF};font-size:34px;font-weight:bold;color:{color};">{nota}</span>
          <span style="font-family:{SERIF};font-size:18px;color:#8a7a68;">/100</span>
        </td>
      </tr>
    </table>"""


def lista(puntos: list[str]) -> str:
    """
    Lista de puntos con una marca de color. Se usan tablas y no <ul>
    porque Outlook aplica márgenes propios a las listas y descuadra
    la sangría.
    """
    if not puntos:
        return ""
    filas = "".join(
        f"""
      <tr>
        <td valign="top" style="padding:0 10px 10px 0;font-family:{SANS};
            font-size:15px;line-height:1.5;color:{TERRACOTA};">&bull;</td>
        <td valign="top" style="padding:0 0 10px;font-family:{SANS};
            font-size:15px;line-height:1.5;color:{TINTA};">{p}</td>
      </tr>"""
        for p in puntos
    )
    return (
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0" '
        f'style="margin:0 0 20px;width:100%;">{filas}</table>'
    )


def ficha(pares: list[tuple[str, str]]) -> str:
    """
    Tabla de etiqueta/valor, para el aviso interno a Alberto.

    Sin white-space:nowrap en la etiqueta: con esa regla, una etiqueta
    como "Precio orientativo" no puede partirse en dos líneas, así que
    en un móvil estrecho la tabla entera se veía obligada a ensancharse
    más que la pantalla para dejarle sitio — el email se desbordaba en
    horizontal (visto en pruebas: 320px de pantalla, tabla de 387px).
    Con la etiqueta pudiendo partirse, la tabla vuelve a caber.
    """
    filas = "".join(
        f"""
      <tr>
        <td valign="top" width="130" style="padding:7px 14px 7px 0;font-family:{SANS};font-size:13px;
            color:#8a7a68;border-bottom:1px solid {LINEA};">{k}</td>
        <td valign="top" style="padding:7px 0;font-family:{SANS};font-size:14px;
            color:{TINTA};border-bottom:1px solid {LINEA};word-break:break-word;">{v}</td>
      </tr>"""
        for k, v in pares
    )
    return (
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0" '
        f'style="margin:0 0 22px;width:100%;">{filas}</table>'
    )


def boton(texto: str, url: str) -> str:
    """Botón de llamada a la acción, hecho con una tabla para que Outlook lo respete."""
    return f"""
    <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:6px 0 22px;">
      <tr>
        <td style="background:{TERRACOTA};border-radius:999px;">
          <a href="{url}" style="display:inline-block;padding:13px 28px;font-family:{SANS};
             font-size:15px;font-weight:bold;color:#ffffff;text-decoration:none;">{texto}</a>
        </td>
      </tr>
    </table>"""


def envolver(titulo: str, contenido: str, preheader: str, firma: str = "") -> str:
    """
    Mete el contenido dentro del envoltorio de marca: cabecera con el
    búho, tarjeta blanca y pie.

    `preheader` es el texto que las bandejas de entrada enseñan detrás
    del asunto. Va oculto dentro del email; si no se pone, Gmail rellena
    ese hueco con lo primero que encuentre en el HTML, que suele ser
    basura como "Ver esta imagen".
    """
    firma_html = (
        f'<p style="margin:26px 0 0;font-family:{SANS};font-size:15px;'
        f'line-height:1.6;color:{TINTA};">{firma}</p>'
        if firma
        else ""
    )

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(titulo)}</title>
</head>
<body style="margin:0;padding:0;background:{CREMA_HONDA};">

<div style="display:none;max-height:0;overflow:hidden;opacity:0;">{esc(preheader)}</div>

<!-- El padding va en la CELDA (<td>), no en la <table>. Puesto
     directamente en la tabla, con width:100%, se sumaba por fuera del
     100% en algunos motores y el email se desbordaba en horizontal en
     móvil (visto en pruebas: pantalla de 320px, email de 328px). En una
     celda, el padding siempre se descuenta del ancho disponible. -->
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%"
       style="background:{CREMA_HONDA};">
  <tr>
    <td align="center" style="padding:28px 12px;">

      <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="600"
             style="width:100%;max-width:600px;">

        <tr>
          <td align="center" style="padding:0 0 20px;">
            <img src="{URL_LOGO}" width="52" height="52" alt="Pipo"
                 style="display:block;border:0;width:52px;height:52px;">
            <div style="font-family:{SERIF};font-size:21px;font-weight:bold;
                        color:{MARRON};padding-top:8px;">Pipo</div>
          </td>
        </tr>

        <tr>
          <td style="background:#ffffff;border:1px solid {LINEA};border-radius:18px;
                     padding:34px 32px;word-break:break-word;overflow-wrap:break-word;">
            <!-- El título lleva el dominio del cliente (p.ej. "negociodemalaga.es"), una
                 palabra larga y sin espacios que puede partirse. Sin overflow-wrap, el
                 navegador prefiere desbordar el email antes que partir la palabra —
                 encontrado en pruebas con un dominio real de 19 caracteres a 320px de
                 pantalla, no con la palabra corta de prueba. -->
            <h1 style="margin:0 0 20px;font-family:{SERIF};font-size:23px;line-height:1.3;
                       font-weight:bold;color:{MARRON};overflow-wrap:break-word;
                       word-break:break-word;">{esc(titulo)}</h1>
            {contenido}
            {firma_html}
          </td>
        </tr>

        <tr>
          <td align="center" style="padding:20px 12px 0;font-family:{SANS};
                                    font-size:12px;line-height:1.6;color:#8a7a68;">
            <a href="{URL_WEB}" style="color:{MARRON};text-decoration:none;
               font-weight:bold;">pipoweb.com</a><br>
            Revisamos webs desde fuera, sin tocar tus sistemas.
          </td>
        </tr>

      </table>

    </td>
  </tr>
</table>

</body>
</html>"""
