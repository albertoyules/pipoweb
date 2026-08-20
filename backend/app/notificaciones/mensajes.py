"""
Contenido de los dos emails de una solicitud de arreglo (ver CLAUDE.md,
P2): uno al cliente, confirmando que ha llegado y con su diagnóstico;
otro a Alberto, con el caso para poder contestarle.

Separado de enviar.py a propósito: enviar.py solo sabe mandar un email
genérico (asunto + cuerpo + html opcional), y no tiene que saber nada
de solicitudes, precios ni checks — igual que app/ia/cliente.py no sabe
de hallazgos.

Cada mensaje se escribe DOS VECES, en texto plano y en HTML (ver
plantilla.py). No es redundancia accidental: el texto plano sigue
siendo el contenido real (es lo que ven quienes no cargan HTML, y es lo
que hay que poder leer de un vistazo en los logs), y el HTML es el
mismo contenido con la vestimenta de marca. Si se cambia una frase, hay
que cambiarla en los dos sitios.

Antes estos dos emails eran de un pedido de 19€ con instrucciones de
Bizum. El 13 ago 2026 el producto de pago pasó a ser el arreglo en sí,
que es un servicio: no se cobra por adelantado, primero se habla.
"""

from app.notificaciones import plantilla as p
from app.puntuacion import calcular_puntuacion


def _checks_a_mejorar(checks: list[dict]) -> list[str]:
    """
    Detalle de cada check que no está en verde, usando el campo
    "detalle" que ya escribe cada check — no hace falta duplicar esas
    frases aquí, ya están pensadas para leerse en cristiano.
    """
    # "sin_datos" fuera: bajo el titular "Esto es lo que hay que tocar"
    # aparecía "No hemos podido comprobar la caducidad de este dominio...
    # No es ni bueno ni malo", que se contradice solo en la misma frase —
    # y es el primer email que recibe alguien que acaba de pedir precio.
    return [check["detalle"] for check in checks if check["estado"] not in ("verde", "sin_datos")]


def mensaje_solicitud_cliente(
    dominio: str,
    checks: list[dict],
    referencia: str,
    precio_estimado: int,
) -> tuple[str, str, str]:
    """Devuelve (asunto, cuerpo_texto, cuerpo_html) para el cliente."""
    nota = calcular_puntuacion(checks)
    pendientes = _checks_a_mejorar(checks)
    asunto = f"Pipo — hemos recibido tu solicitud para {dominio}"

    lista_texto = (
        "\n".join(f"- {d}" for d in pendientes)
        if pendientes
        else "Ahora mismo no hay ningún punto en rojo o ámbar — buena señal."
    )
    cuerpo = f"""Hola,

Nos has pedido que arreglemos lo que Pipo ha encontrado en {dominio}. Ya lo tenemos.

Nota actual de tu web: {nota}/100

Esto es lo que hay que tocar:

{lista_texto}

Precio orientativo para dejarlo todo en verde: {precio_estimado}€. Es una estimación
automática a partir de lo que hemos visto desde fuera; el precio cerrado te lo confirmamos
al responderte, ya sin sorpresas.

Te escribimos normalmente en menos de 24 horas para ver contigo cómo entramos a hacerlo
(en algunos casos hace falta acceso a tu gestor de la web o a tu hosting; en otros no).

No hay que pagar nada por adelantado ni te hemos cobrado nada.

Referencia de tu solicitud: {referencia}

Un saludo,
Pipo (Alberto)
"""

    contenido_html = "".join([
        p.parrafo(f"Nos has pedido que arreglemos lo que Pipo ha encontrado en "
                  f"<strong>{p.esc(dominio)}</strong>. Ya lo tenemos."),
        p.nota_destacada(nota),
        p.parrafo("Esto es lo que hay que tocar:") if pendientes else p.parrafo(p.esc(lista_texto), tenue=True),
        p.lista([p.esc(d) for d in pendientes]),
        p.parrafo(
            f"Precio orientativo para dejarlo todo en verde: "
            f"<strong>{precio_estimado}€</strong>. Es una estimación automática a partir "
            f"de lo que hemos visto desde fuera; el precio cerrado te lo confirmamos al "
            f"responderte, ya sin sorpresas."
        ),
        p.parrafo(
            "Te escribimos normalmente en menos de 24 horas para ver contigo cómo entramos "
            "a hacerlo (en algunos casos hace falta acceso a tu gestor de la web o a tu "
            "hosting; en otros no)."
        ),
        p.parrafo("No hay que pagar nada por adelantado ni te hemos cobrado nada.", tenue=True),
        p.parrafo(f"Referencia de tu solicitud: <strong>{p.esc(referencia)}</strong>", tenue=True),
    ])
    html = p.envolver(
        titulo=f"Hemos recibido tu solicitud para {dominio}",
        contenido=contenido_html,
        preheader=f"Nota actual: {nota}/100 · Precio orientativo {precio_estimado}€ · "
                  f"Te contestamos en menos de 24 horas",
        firma="Un saludo,<br>Pipo (Alberto)",
    )

    return asunto, cuerpo, html


def mensaje_solicitud_alberto(
    dominio: str,
    email_cliente: str,
    telefono_cliente: str | None,
    mensaje_cliente: str | None,
    referencia: str,
    precio_estimado: int,
    id_escaneo: int,
) -> tuple[str, str, str]:
    """Devuelve (asunto, cuerpo_texto, cuerpo_html) para el aviso interno."""
    asunto = f"Nueva solicitud de arreglo: {dominio} (~{precio_estimado}€)"
    texto_mensaje = mensaje_cliente or "(no ha escrito nada)"

    cuerpo = f"""Solicitud nueva de arreglo.

Dominio: {dominio}
Email: {email_cliente}
Teléfono: {telefono_cliente or "no facilitado"}
Referencia: {referencia}
Precio orientativo calculado: {precio_estimado}€
Escaneo nº {id_escaneo}

Lo que ha escrito el cliente:
{texto_mensaje}

Siguiente paso: abre el panel de solicitudes, saca las soluciones paso a paso de ese
escaneo, y contéstale con el presupuesto cerrado.
"""

    contenido_html = "".join([
        p.ficha([
            ("Dominio", f"<strong>{p.esc(dominio)}</strong>"),
            ("Email", f'<a href="mailto:{p.esc(email_cliente)}" style="color:{p.TERRACOTA};">{p.esc(email_cliente)}</a>'),
            ("Teléfono", p.esc(telefono_cliente) if telefono_cliente else "no facilitado"),
            ("Referencia", p.esc(referencia)),
            ("Precio orientativo", f"{precio_estimado}€"),
            ("Escaneo", f"nº {id_escaneo}"),
        ]),
        p.parrafo("Lo que ha escrito el cliente:"),
        p.parrafo(p.esc(texto_mensaje), tenue=(mensaje_cliente is None)),
        p.parrafo(
            "Siguiente paso: abre el panel de solicitudes, saca las soluciones paso a paso "
            "de ese escaneo, y contéstale con el presupuesto cerrado.",
            tenue=True,
        ),
    ])
    html = p.envolver(
        titulo="Nueva solicitud de arreglo",
        contenido=contenido_html,
        preheader=f"{dominio} · ~{precio_estimado}€ · {email_cliente}",
    )

    return asunto, cuerpo, html
