"""
Contenido de los dos emails de una solicitud de arreglo (ver CLAUDE.md,
P2): uno al cliente, confirmando que ha llegado y con su diagnóstico;
otro a Alberto, con el caso para poder contestarle.

Separado de enviar.py a propósito: enviar.py solo sabe mandar un email
genérico (asunto + cuerpo), y no tiene que saber nada de solicitudes,
precios ni checks — igual que app/ia/cliente.py no sabe de hallazgos.

Antes estos dos emails eran de un pedido de 19€ con instrucciones de
Bizum. El 13 ago 2026 el producto de pago pasó a ser el arreglo en sí,
que es un servicio: no se cobra por adelantado, primero se habla.
"""

from app.puntuacion import calcular_puntuacion


def _checks_a_mejorar(checks: list[dict]) -> str:
    """
    Lista en texto plano de los checks que no están en verde, usando el
    campo "detalle" que ya escribe cada check — no hace falta duplicar
    esas frases aquí, ya están pensadas para leerse en cristiano.
    """
    problematicos = [check for check in checks if check["estado"] != "verde"]
    if not problematicos:
        return "Ahora mismo no hay ningún punto en rojo o ámbar — buena señal."
    return "\n".join(f"- {check['detalle']}" for check in problematicos)


def mensaje_solicitud_cliente(
    dominio: str,
    checks: list[dict],
    referencia: str,
    precio_estimado: int,
) -> tuple[str, str]:
    """Devuelve (asunto, cuerpo) del email de confirmación al cliente."""
    nota = calcular_puntuacion(checks)
    asunto = f"Pipo — hemos recibido tu solicitud para {dominio}"
    cuerpo = f"""Hola,

Nos has pedido que arreglemos lo que Pipo ha encontrado en {dominio}. Ya lo tenemos.

Nota actual de tu web: {nota}/100

Esto es lo que hay que tocar:

{_checks_a_mejorar(checks)}

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
    return asunto, cuerpo


def mensaje_solicitud_alberto(
    dominio: str,
    email_cliente: str,
    telefono_cliente: str | None,
    mensaje_cliente: str | None,
    referencia: str,
    precio_estimado: int,
    id_escaneo: int,
) -> tuple[str, str]:
    """Devuelve (asunto, cuerpo) del aviso interno para Alberto."""
    asunto = f"Nueva solicitud de arreglo: {dominio} (~{precio_estimado}€)"
    cuerpo = f"""Solicitud nueva de arreglo.

Dominio: {dominio}
Email: {email_cliente}
Teléfono: {telefono_cliente or "no facilitado"}
Referencia: {referencia}
Precio orientativo calculado: {precio_estimado}€
Escaneo nº {id_escaneo}

Lo que ha escrito el cliente:
{mensaje_cliente or "(no ha escrito nada)"}

Siguiente paso: abre el panel de solicitudes, saca las soluciones paso a paso de ese
escaneo, y contéstale con el presupuesto cerrado.
"""
    return asunto, cuerpo
